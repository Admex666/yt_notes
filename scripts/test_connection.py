import os
import sys

# Projekt gyökér hozzáadása a keresési útvonalhoz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from src.config import GOOGLE_API_KEY, NOTION_API_KEY, NOTION_DATABASE_ID, DEFAULT_MODEL, MODEL_METADATA, PLAN_INFO_URL
from src.services.notion_service import get_database_tags, get_existing_video_urls

def test_gemini():
    print("=" * 60)
    print(" 1. GOOGLE AI STUDIO / GEMINI ELLENŐRZÉSE")
    print("=" * 60)
    if not GOOGLE_API_KEY:
        print("[HIBA] GOOGLE_API_KEY nincs beállítva a .env-ben!")
        return False

    masked = GOOGLE_API_KEY[:6] + "..." + GOOGLE_API_KEY[-4:]
    print(f"Kulcs: {masked}")
    
    meta = MODEL_METADATA.get(DEFAULT_MODEL, {})
    print(f"Modell: {meta.get('display_name', DEFAULT_MODEL)}")
    print(f"Napi limit (RPD): {meta.get('rpd', 'N/A')} kérés / nap")
    print(f"Percenkénti limit (RPM): {meta.get('rpm', 'N/A')} kérés / perc")
    print(f"Token / perc (TPM): {meta.get('tpm', 'N/A'):,} token / perc")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{DEFAULT_MODEL}:generateContent?key={GOOGLE_API_KEY}"
    payload = {"contents": [{"parts": [{"text": "Hello, respond with 'OK' only."}]}]}
    try:
        res = requests.post(url, json=payload, timeout=15)
        if res.status_code == 200:
            usage = res.json().get("usageMetadata", {})
            print("[SIKER] Gemini kapcsolat hibátlan!")
            print(f"Teszt hívás tokenjei: {usage.get('totalTokenCount', 0)} token (Prompt: {usage.get('promptTokenCount', 0)}, Válasz: {usage.get('candidatesTokenCount', 0)})")
            return True
        else:
            print(f"[HIBA] HTTP {res.status_code}: {res.text}")
            return False
    except Exception as e:
        print(f"[HIBA] Kapcsolódási hiba: {e}")
        return False

def test_notion():
    print("\n" + "=" * 60)
    print(" 2. NOTION ADATBÁZIS ELLENŐRZÉSE")
    print("=" * 60)
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        print("[HIBA] NOTION_API_KEY vagy NOTION_DATABASE_ID hiányzik!")
        return False

    print(f"Adatbázis ID: {NOTION_DATABASE_ID}")
    try:
        tags = get_database_tags(NOTION_DATABASE_ID)
        print(f"[SIKER] Notion kapcsolat aktív! Elérhető címkék száma: {len(tags)}")
        urls = get_existing_video_urls(NOTION_DATABASE_ID)
        print(f"[SIKER] Korábban mentett videók száma az adatbázisban: {len(urls)}")
        return True
    except Exception as e:
        print(f"[HIBA] Notion kapcsolódási hiba: {e}")
        return False

if __name__ == "__main__":
    ok_g = test_gemini()
    ok_n = test_notion()
    print("\n" + "=" * 60)
    if ok_g and ok_n:
        print(" Minden rendszer készen áll a futtatásra!")
    else:
        print(" Valamelyik szolgáltatásnál hiba történt, kérlek ellenőrizd a beállításokat.")
    print("=" * 60)
