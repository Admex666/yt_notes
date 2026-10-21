import re
from typing import List, Dict, Set, Optional, Tuple
import requests
from src.config import NOTION_API_KEY, NOTION_VERSION

def _get_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }

def get_database_tags(database_id: str) -> List[str]:
    """Lekéri a Notion adatbázis létező címkéit (Tags multi-select)."""
    headers = _get_headers()
    url = f"https://api.notion.com/v1/databases/{database_id}"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            props = res.json().get("properties", {})
            tags_prop = props.get("Tags", {})
            options = tags_prop.get("multi_select", {}).get("options", [])
            return [opt.get("name") for opt in options if opt.get("name")]
    except Exception as e:
        print(f"Hiba a címkék lekérésekor: {e}")
    return []

def get_existing_video_urls(database_id: str) -> Set[str]:
    """
    Lekérdezi az adatbázisban már rögzített YouTube videók URL-jeit.
    Kezeli az oldalazást (pagination).
    """
    headers = _get_headers()
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    existing_urls = set()
    has_more = True
    start_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code != 200:
                break
            data = res.json()
            for page in data.get("results", []):
                props = page.get("properties", {})
                url_prop = props.get("URL", {})
                v_url = url_prop.get("url")
                if v_url:
                    existing_urls.add(v_url.strip())
            
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
        except Exception as e:
            print(f"Hiba a létező URL-ek lekérdezésekor: {e}")
            break

    return existing_urls

def markdown_to_notion_blocks(markdown_text: str) -> List[Dict]:
    """
    Átalakítja a Markdown szöveget tiszta Notion blokkokká.
    Kezeli a címeket (#, ##, ###), felsorolásokat, idézeteket, elválasztókat és bekezdéseket.
    """
    lines = markdown_text.splitlines()
    blocks = []

    def _truncate_text(text: str) -> str:
        return text[:1950] if len(text) > 1950 else text

    def _rich_text(content: str) -> List[Dict]:
        return [{"type": "text", "text": {"content": _truncate_text(content)}}]

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        
        # Üres sorok átugrása
        if not line:
            i += 1
            continue

        # Elválasztó vonal (---)
        if line.strip() in ["---", "***", "___"]:
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            i += 1
            continue

        # Címsorok
        if line.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": _rich_text(line[2:].strip())}
            })
            i += 1
            continue

        if line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": _rich_text(line[3:].strip())}
            })
            i += 1
            continue

        if line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": _rich_text(line[4:].strip())}
            })
            i += 1
            continue

        # Idézet vagy Callout
        if line.startswith("> "):
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": _rich_text(line[2:].strip())}
            })
            i += 1
            continue

        # Felsorolás (Bullet)
        if line.lstrip().startswith(("- ", "* ", "• ")):
            clean_line = re.sub(r'^\s*[-*•]\s+', '', line)
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _rich_text(clean_line)}
            })
            i += 1
            continue

        # Számozott lista
        match_num = re.match(r'^\s*\d+[\.\)]\s+(.*)', line)
        if match_num:
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": _rich_text(match_num.group(1))}
            })
            i += 1
            continue

        # Normál bekezdés (együtt tartva az összetartozó sorokat)
        para_lines = [line]
        while i + 1 < len(lines):
            next_line = lines[i + 1].rstrip()
            if not next_line or next_line.startswith(("#", "-", "*", ">", "---", "•")) or re.match(r'^\s*\d+[\.\)]\s+', next_line):
                break
            para_lines.append(next_line)
            i += 1

        full_para = " ".join(para_lines).strip()
        if full_para:
            for chunk_start in range(0, len(full_para), 1900):
                chunk = full_para[chunk_start:chunk_start + 1900]
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": _rich_text(chunk)}
                })
        i += 1

    return blocks

def create_zettelkasten_note(
    database_id: str,
    title: str,
    video_url: str,
    tags: List[str],
    markdown_content: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Létrehozza a jegyzetet a Notion 'Zettelkasten Notes [PT]' adatbázisban.
    Visszatérés: (siker, üzenet, notion_page_url)
    """
    headers = _get_headers()
    blocks = markdown_to_notion_blocks(markdown_content)

    initial_blocks = blocks[:100]
    remaining_blocks = blocks[100:]

    properties = {
        "Name": {
            "title": [{"type": "text", "text": {"content": title[:200]}}]
        },
        "URL": {
            "url": video_url
        }
    }

    if tags:
        properties["Tags"] = {
            "multi_select": [{"name": t} for t in tags]
        }

    payload = {
        "parent": {"database_id": database_id},
        "properties": properties,
        "children": initial_blocks
    }

    create_url = "https://api.notion.com/v1/pages"
    try:
        res = requests.post(create_url, headers=headers, json=payload, timeout=20)
        if res.status_code != 200:
            return False, f"Notion hiba (HTTP {res.status_code}): {res.text}", None

        page_data = res.json()
        page_id = page_data.get("id")
        page_url = page_data.get("url")

        if remaining_blocks and page_id:
            append_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            for b_idx in range(0, len(remaining_blocks), 100):
                batch = remaining_blocks[b_idx:b_idx + 100]
                batch_res = requests.patch(append_url, headers=headers, json={"children": batch}, timeout=20)
                if batch_res.status_code != 200:
                    print(f"Figyelmeztetés: néhány blokk hozzáfűzése sikertelen volt: {batch_res.text}")

        return True, "Sikeresen mentve a Notion adatbázisba!", page_url

    except Exception as e:
        return False, f"Hálózati hiba a Notion mentés során: {str(e)}", None
