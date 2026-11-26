import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
STATE_FILE = os.path.join(DATA_DIR, "substack_state.json")

DEFAULT_SUBSTACK_FEEDS: List[str] = [
    "https://fussballcoach.substack.com/feed",
    "https://alex11marin11.substack.com/feed",
    "https://bookbase.substack.com/feed",
    "https://pogatsa.substack.com/feed",
    "https://cannonstats.substack.com/feed",
    "https://datadealsfc.substack.com/feed",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def _resolve_substack_profile_to_feed(username: str) -> Optional[str]:
    """
    Ha a felhasználó @username profilt adott meg (pl. substack.com/@ethanmollick),
    feloldja a szerző elsődleges Substack publikációjának (custom domain vagy subdomain) RSS feedjét.
    """
    clean_user = username.strip().lstrip("@").split("/")[0]
    if not clean_user:
        return None
    try:
        api_url = f"https://substack.com/api/v1/user/{clean_user}/public_profile"
        res = requests.get(api_url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for pu in data.get("publicationUsers", []):
                pub = pu.get("publication") or {}
                custom_domain = pub.get("custom_domain")
                subdomain = pub.get("subdomain")
                if custom_domain:
                    return f"https://{custom_domain}/feed"
                if subdomain:
                    return f"https://{subdomain}.substack.com/feed"
    except Exception:
        pass
    return f"https://{clean_user}.substack.com/feed"


def normalize_substack_feed_url(raw_input: str) -> Optional[str]:
    """
    Átalakítja a felhasználó által megadott Substack linket vagy nevet szabványos RSS feed URL-lé.
    Példák:
      - 'oneusefulthing' -> 'https://oneusefulthing.substack.com/feed'
      - 'https://www.lennysnewsletter.com/' -> 'https://www.lennysnewsletter.com/feed'
      - 'https://substack.com/@ethanmollick' -> feloldja a szerző publikációjának /feed címét
    """
    if not raw_input:
        return None
    s = raw_input.strip()
    if not s:
        return None

    # Ha @handle formátumot adott meg
    if s.startswith("@") and "/" not in s:
        return _resolve_substack_profile_to_feed(s[1:])

    # Ha csak egy szót / azonosítót adott meg pont nélkül (pl. "oneusefulthing" vagy "pragmaticengineer")
    if "." not in s and "/" not in s:
        slug = s.lower()
        return f"https://{slug}.substack.com/feed"

    if not s.startswith(("http://", "https://")):
        s = "https://" + s

    parsed = urlparse(s)
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")

    if not netloc:
        return None

    # Ha substack.com/@username formátumú profil linket adtak meg:
    if netloc in ("substack.com", "www.substack.com") and path.startswith("/@"):
        username = path[2:].split("/")[0]
        if username:
            return _resolve_substack_profile_to_feed(username)

    # Ha egy konkrét poszt linkjét adta meg (pl. .../p/cikk-cime), vágjuk le a gyökérig
    if "/p/" in path:
        path = path.split("/p/")[0]

    # Ha már /feed vagy .xml végződésű, megtartjuk
    if path.endswith("/feed") or path.endswith(".xml") or path.endswith("/rss"):
        return f"{parsed.scheme}://{netloc}{path}"

    return f"{parsed.scheme}://{netloc}{path}/feed"


def load_state() -> Dict:
    """Betölti a követett Substack feedeket, elswipe-olt cikkeket és gyorsítótárazott rövid összefoglalókat."""
    default_data = {
        "feeds": list(DEFAULT_SUBSTACK_FEEDS),
        "dismissed_urls": [],
        "bookmarked_urls": [],
        "summaries": {}
    }
    if not os.path.exists(STATE_FILE):
        return default_data
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in default_data.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return default_data


def save_state(state: Dict) -> None:
    """Elmenti a Substack állapotot a data/substack_state.json fájlba."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def clean_html_to_text(html_content: str) -> Tuple[str, Optional[str]]:
    """
    Megtisztítja a Substack cikk HTML törzsét jól olvasható szöveggé,
    és kinyeri az első értelmes borítóképet (ha van).
    """
    if not html_content:
        return "", None

    soup = BeautifulSoup(html_content, "html.parser")

    # Első kép kinyerése borítóképnek (kihagyva az 1x1-es tracking pixeleket / ikonokat)
    cover_img = None
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        width = img.get("width")
        if src.startswith("http") and "substackcdn.com/image/fetch" in src or src.startswith("http"):
            if width and str(width).isdigit() and int(width) < 80:
                continue
            cover_img = src
            break

    # Substack gombok, feliratkozó widgetek és script/style elemek eltávolítása
    for tag in soup.find_all(["script", "style", "button", "svg", "form", "iframe"]):
        tag.decompose()
    for div in soup.find_all("div", class_=re.compile(r"subscription-widget|button-wrapper|captioned-button-wrap")):
        div.decompose()

    # Bekezdések és címsorok strukturált megtartása
    blocks = []
    for elem in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote"]):
        txt = elem.get_text(" ", strip=True)
        if not txt:
            continue
        if elem.name in ("h1", "h2", "h3", "h4"):
            blocks.append(f"\n## {txt}\n")
        elif elem.name == "li":
            blocks.append(f"- {txt}")
        elif elem.name == "blockquote":
            blocks.append(f"> {txt}")
        else:
            blocks.append(txt)

    if blocks:
        clean_text = "\n\n".join(blocks)
    else:
        clean_text = soup.get_text("\n\n", strip=True)

    # Felesleges üres sorok tömörítése
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()
    return clean_text, cover_img


def _parse_pub_date(date_str: str) -> Tuple[str, float]:
    """Visszaadja az olvasható dátumot (YYYY-MM-DD) és a rendezéshez használt timestampet."""
    if not date_str:
        return "", 0.0
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d"), dt.timestamp()
    except Exception:
        return date_str[:16], 0.0


def _is_paywalled_or_truncated(raw_html: str, clean_text: str) -> bool:
    """Észleli, ha a cikk fizetős fal (paywall) mögött van és csak rövid előnézet érhető el."""
    lower_html = (raw_html or "").lower()
    paywall_markers = [
        "this post is for paid subscribers",
        "subscribe to continue reading",
        "become a paying subscriber",
        "paid subscribers only",
    ]
    if any(m in lower_html for m in paywall_markers):
        return True
    # Ha gyanúsan rövid (< 120 szó) és "read more" van a végén
    if len(clean_text.split()) < 80 and "read more" in clean_text.lower()[-150:]:
        return True
    return False


def fetch_feed_articles(feed_url: str, max_items: int = 10, include_paywalled: bool = False) -> Tuple[List[Dict], Optional[str], Optional[str]]:
    """
    Lekéri egyetlen Substack RSS feed cikkeit.
    Visszatérési érték: (articles_list, publication_title, error_message)
    """
    norm_url = normalize_substack_feed_url(feed_url)
    if not norm_url:
        return [], None, f"Érvénytelen Substack URL: {feed_url}"

    try:
        res = requests.get(norm_url, headers=HEADERS, timeout=15)
        if res.status_code != 200:
            return [], None, f"Nem sikerült elérni a feedet ({norm_url}) - HTTP {res.status_code}"
        content_type = (res.headers.get("Content-Type") or "").lower()
        # Ha a Substack átirányított egy @felhasznalo profiloldalra (HTML), próbáljuk feloldani a valódi publikációt
        if "text/html" in content_type and "substack.com/@" in res.url:
            handle = res.url.split("substack.com/@")[-1].split("/")[0].split("?")[0]
            resolved = _resolve_substack_profile_to_feed(handle)
            if resolved and resolved != norm_url:
                res = requests.get(resolved, headers=HEADERS, timeout=15)
                norm_url = resolved
                content_type = (res.headers.get("Content-Type") or "").lower()
        if "text/html" in content_type and not res.text.lstrip().startswith("<?xml") and "<rss" not in res.text[:500]:
            return [], None, f" Nem található aktív Substack RSS feed ezen a címen ({norm_url}). Ellenőrizd a publikáció pontos URL-jét!"
        xml_bytes = res.content
    except Exception as e:
        return [], None, f"Hálózati hiba ({norm_url}): {str(e)}"

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        return [], None, f"Érvénytelen RSS/XML formátum ({norm_url}): {str(e)}"

    ns = {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "media": "http://search.yahoo.com/mrss/",
    }

    channel = root.find("channel")
    if channel is None:
        return [], None, f"Nem található RSS csatorna ezen a címen: {norm_url}"

    pub_title = (channel.findtext("title") or norm_url).strip()
    articles: List[Dict] = []

    items = channel.findall("item")
    for item in items[:max_items * 2]:
        if len(articles) >= max_items:
            break

        title = (item.findtext("title") or "Névtelen cikk").strip()
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or link).strip()
        description_html = item.findtext("description") or ""
        content_encoded = item.findtext("content:encoded", default="", namespaces=ns)
        author = (
            item.findtext("dc:creator", default="", namespaces=ns).strip()
            or pub_title
        )
        pub_date_raw = item.findtext("pubDate") or ""
        pub_date_str, pub_ts = _parse_pub_date(pub_date_raw)

        # Borítókép: enclosure vagy media:content vagy HTML-ből
        enclosure = item.find("enclosure")
        enclosure_img = None
        if enclosure is not None and (enclosure.attrib.get("type", "").startswith("image") or enclosure.attrib.get("url", "").endswith((".jpg", ".jpeg", ".png", ".webp"))):
            enclosure_img = enclosure.attrib.get("url")

        raw_body = content_encoded if content_encoded else description_html
        clean_text, html_img = clean_html_to_text(raw_body)
        subtitle_text, _ = clean_html_to_text(description_html)

        # Csak ingyenes cikkek szűrése (felhasználói igény szerint)
        is_paywalled = _is_paywalled_or_truncated(raw_body, clean_text)
        if is_paywalled and not include_paywalled:
            continue

        # Ha szinte üres (pl. csak egy rövid podcast/videó beágyazás szöveg nélkül), kihagyjuk vagy jelezzük
        word_count = len(clean_text.split())
        if word_count < 40:
            continue

        reading_time_min = max(1, round(word_count / 220))

        articles.append({
            "id": guid or link,
            "title": title,
            "subtitle": subtitle_text[:280] if subtitle_text and subtitle_text != clean_text[:280] else "",
            "url": link,
            "publication": pub_title,
            "author": author,
            "published_date": pub_date_str,
            "published_ts": pub_ts,
            "thumbnail": enclosure_img or html_img or "",
            "content": clean_text,
            "word_count": word_count,
            "reading_time_min": reading_time_min,
            "feed_url": norm_url,
        })

    return articles, pub_title, None


def fetch_all_followed_articles(feed_urls: List[str], max_per_feed: int = 8) -> Tuple[List[Dict], List[str]]:
    """
    Lekéri az összes követett Substack író legfrissebb ingyenes cikkeit,
    időrendben (legújabb elöl) rendezve, duplikációk nélkül.
    """
    all_articles: List[Dict] = []
    seen_urls: Set[str] = set()
    errors: List[str] = []

    for f_url in feed_urls:
        items, _, err = fetch_feed_articles(f_url, max_items=max_per_feed, include_paywalled=False)
        if err:
            errors.append(err)
            continue
        for art in items:
            if art["url"] not in seen_urls:
                seen_urls.add(art["url"])
                all_articles.append(art)

    all_articles.sort(key=lambda x: x.get("published_ts", 0.0), reverse=True)
    return all_articles, errors
