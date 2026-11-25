import re
import time
from typing import Dict, Tuple, List, Optional
import requests
from src.config import GOOGLE_API_KEY
from src.prompts import (
    SYSTEM_PROMPT_NARRATIVES,
    PROMPT_NARRATIVES_USER_TEMPLATE,
    SYSTEM_PROMPT_FINAL_NOTE,
    PROMPT_FINAL_NOTE_USER_TEMPLATE,
    SYSTEM_PROMPT_SWIPE_SUMMARY,
    PROMPT_SWIPE_SUMMARY_USER_TEMPLATE
)

def _call_gemini(system_prompt: str, user_prompt: str, model: str = "gemini-3.5-flash-lite") -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
    """Segédfüggvény a Gemini API hívásához részletes tokenhasználattal."""
    if not GOOGLE_API_KEY:
        return None, None, "Hiányzik a GOOGLE_API_KEY a környezeti változókból vagy a .env fájlból."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_API_KEY}"
    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "parts": [{"text": user_prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192
        }
    }

    last_error = None
    for attempt in range(3):
        try:
            res = requests.post(url, json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    raw_usage = data.get("usageMetadata", {})

                    usage = {
                        "prompt_tokens": raw_usage.get("promptTokenCount", 0),
                        "candidate_tokens": raw_usage.get("candidatesTokenCount", 0),
                        "total_tokens": raw_usage.get("totalTokenCount", 0),
                        "service_tier": raw_usage.get("serviceTier", "standard"),
                        "model": model
                    }
                    return text, usage, None
                return None, None, "A modell nem adott vissza szöveges választ."
            elif res.status_code == 503 and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            elif res.status_code == 429:
                return None, None, "Google AI Studio kvótakorlát (429: Resource Exhausted). Kérlek várj pár másodpercet a következő kérés előtt."
            else:
                return None, None, f"Google API hiba (HTTP {res.status_code}): {res.text[:300]}"
        except Exception as e:
            last_error = f"Hálózati hiba a Gemini API hívása közben: {str(e)}"
            if attempt < 2:
                time.sleep(2)
                continue
    return None, None, last_error or "Ismeretlen hiba a Gemini API hívása közben."

def generate_swipe_summary(
    title: str,
    author: str,
    publication: str,
    url: str,
    content: str,
    language: str = "Hungarian",
    model: str = "gemini-3.5-flash-lite"
) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
    """
    Gyors, kvótatakarékos előszűrő összefoglaló egyetlen Substack cikkhez (Swipe kártyán).
    """
    if language in ["A videó eredeti nyelve", "Az eredeti nyelven", "The original language of the video"]:
        lang_instruction = "the original language of the article (e.g. English if English, Hungarian if Hungarian)"
    else:
        lang_instruction = language

    system_prompt = SYSTEM_PROMPT_SWIPE_SUMMARY.format(language=lang_instruction)
    # Biztonsági levágás nagyon hosszú cikkeknél, bár Flash Lite 1M tokent bír, gyors-összefoglalóhoz elég az első ~25000 karakter
    trimmed_content = content[:25000] if len(content) > 25000 else content
    user_prompt = PROMPT_SWIPE_SUMMARY_USER_TEMPLATE.format(
        title=title,
        author=author,
        publication=publication,
        url=url,
        content=trimmed_content
    )
    return _call_gemini(system_prompt, user_prompt, model=model)

def generate_narratives(title: str, url: str, transcript: str, model: str = "gemini-3.5-flash-lite") -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
    """
    1. Lépés: Narratívák azonosítása a videó leiratából.
    """
    user_prompt = PROMPT_NARRATIVES_USER_TEMPLATE.format(
        title=title,
        url=url,
        transcript=transcript
    )
    return _call_gemini(SYSTEM_PROMPT_NARRATIVES, user_prompt, model=model)

def generate_final_note(
    title: str,
    url: str,
    transcript: str,
    narratives_text: str,
    selected_narratives: str,
    user_comments: str = "",
    available_tags: Optional[List[str]] = None,
    language: str = "Hungarian",
    model: str = "gemini-3.5-flash-lite"
) -> Tuple[Optional[str], Optional[str], List[str], Optional[Dict], Optional[str]]:
    """
    2. Lépés: A kiválasztott narratíva / narratívák alapján elkészíti a végső Zettelkasten jegyzetet.
    Visszatérés: (markdown_note, parsed_title, suggested_tags, usage, error)
    """
    tags_str = ", ".join(available_tags) if available_tags else "Productivity, Learning, Business, AI, Psychology"
    
    if language in ["A videó eredeti nyelve", "Az eredeti nyelven", "The original language of the video"]:
        lang_instruction = "The original language of the source text/transcript (e.g. if in English, write the entire note in English; if Hungarian, write in Hungarian)"
    else:
        lang_instruction = language

    system_prompt = SYSTEM_PROMPT_FINAL_NOTE.format(language=lang_instruction)
    user_prompt = PROMPT_FINAL_NOTE_USER_TEMPLATE.format(
        title=title,
        url=url,
        selected_narratives=selected_narratives,
        user_comments=user_comments if user_comments else "None (Kövesd a kiválasztott narratívát)",
        narratives_text=narratives_text,
        transcript=transcript,
        available_tags=tags_str
    )

    text, usage, error = _call_gemini(system_prompt, user_prompt, model=model)
    if error or not text:
        return None, None, [], usage, error

    parsed_title = title
    suggested_tags = []

    lines = text.strip().splitlines()
    for line in lines:
        if line.startswith("# "):
            parsed_title = line[2:].strip()
            break

    tag_match = re.search(r'TAGS:\s*\[(.*?)\]', text, re.IGNORECASE)
    if tag_match:
        tag_items = tag_match.group(1).split(",")
        suggested_tags = [t.strip().strip("'\"") for t in tag_items if t.strip()]
        text = re.sub(r'\n*TAGS:\s*\[.*?\]', '', text, flags=re.IGNORECASE).strip()

    return text, parsed_title, suggested_tags, usage, None
