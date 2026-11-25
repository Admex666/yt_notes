import re
from typing import List, Dict, Optional, Tuple

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

def extract_video_id(url_or_id: str) -> Optional[str]:
    """Kinyeri a 11 karakteres YouTube videó ID-t URL-ből vagy szövegből."""
    if not url_or_id:
        return None
    url_or_id = url_or_id.strip()
    if len(url_or_id) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return None

def get_playlist_videos(playlist_url: str) -> List[Dict]:
    """
    Lekéri a megadott YouTube playlist összes videójának alapadatait.
    Gyors és nem tölt le videófájlokat.
    """
    if yt_dlp is None:
        print("Hiányzik a yt-dlp csomag (pip install yt-dlp).")
        return []
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'quiet': True,
        'skip_download': True,
        'ignoreerrors': True,
    }
    videos = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(playlist_url, download=False)
        except Exception as e:
            print(f"Hiba a playlist betöltésekor: {e}")
            return []

        if not info:
            return []
        
        # Ha egyetlen videó URL-t adott meg a felhasználó playlist helyett:
        if 'entries' not in info:
            v_id = info.get('id')
            return [{
                'id': v_id,
                'title': info.get('title', 'Névtelen videó'),
                'url': info.get('webpage_url') or f"https://www.youtube.com/watch?v={v_id}",
                'duration': info.get('duration'),
                'uploader': info.get('uploader', ''),
                'thumbnail': info.get('thumbnail') or f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg" if v_id else ""
            }]

        for entry in info.get('entries', []):
            if not entry:
                continue
            video_id = entry.get('id')
            title = entry.get('title', 'Névtelen videó')
            url = entry.get('url') or f"https://www.youtube.com/watch?v={video_id}"
            if not url.startswith('http'):
                url = f"https://www.youtube.com/watch?v={video_id}"
            
            thumbnails = entry.get('thumbnails', [])
            thumb = entry.get('thumbnail')
            if not thumb and thumbnails:
                thumb = thumbnails[-1].get('url')
            if not thumb and video_id:
                thumb = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

            videos.append({
                'id': video_id,
                'title': title,
                'url': url,
                'duration': entry.get('duration'),
                'uploader': entry.get('uploader', ''),
                'thumbnail': thumb
            })

    return videos

def get_video_transcript(video_id: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Letölti a videó leiratát (transcript).
    Visszatérési érték: (transcript_text, language_code, error_message)
    Először youtube-transcript-api-val próbálkozik, prioritás: hu, en, majd bármely elérhető.
    """
    clean_id = extract_video_id(video_id)
    if not clean_id:
        return None, None, "Érvénytelen videó ID vagy URL."

    try:
        if YouTubeTranscriptApi is None:
            raise ImportError("youtube-transcript-api nincs telepítve")
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(clean_id)
        
        # 1. Próbálunk magyar vagy angol feliratot keresni
        chosen_transcript = None
        for lang_code in ['hu', 'en']:
            try:
                chosen_transcript = transcript_list.find_transcript([lang_code])
                break
            except Exception:
                continue

        # 2. Ha nincs hu vagy en, vegyük az első elérhető feliratot
        if not chosen_transcript:
            for t in transcript_list:
                chosen_transcript = t
                break

        if chosen_transcript:
            snippets = chosen_transcript.fetch()
            text_lines = []
            for item in snippets:
                text = getattr(item, 'text', None) or (item.get('text') if isinstance(item, dict) else str(item))
                if text:
                    text_lines.append(text.replace('\n', ' '))
            
            full_text = " ".join(text_lines)
            return full_text, chosen_transcript.language_code, None

    except Exception:
        pass

    # Ha a youtube-transcript-api nem talált feliratot, próbáljuk yt-dlp-vel
    try:
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['hu', 'en', 'all'],
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={clean_id}", download=False)
            subs = info.get('subtitles', {}) or info.get('automatic_captions', {})
            if subs:
                for lang in subs.keys():
                    return None, lang, f"Automatikus felirat észlelve ({lang}), de a felirat letöltése védett."
    except Exception:
        pass

    return None, None, "Ehhez a videóhoz nem található letölthető felirat/leirat (a videó nem tartalmaz feliratot)."
