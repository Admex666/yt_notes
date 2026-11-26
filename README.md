# 🧠 Zettelkasten Note Maker (YouTube & Substack)

Egy moduláris, kétlépcsős munkafolyamat **YouTube videók** leiratainak és követett **Substack írók** ingyenes cikkeinek feldolgozásához, a saját érdeklődési köreid és narratíváid szerint, közvetlen **Notion Zettelkasten Notes [PT]** integrációval, token- és kvótakövetéssel.

---

## ✨ Főbb Modulok

1. **🎥 YouTube Jegyzetelő:** Playlist vagy egyedi videó leiratának letöltése -> 3-4 személyre szabott narratíva azonosítása -> Strukturált Notion Zettelkasten jegyzet generálása.
2. **📰 Substack Swipe:**
   - Követett Substack írók / csatornák felvétele és törlése közvetlenül a bal oldalsávban.
   - Csak az **ingyenes, teljes terjedelmű cikkek** automatikus kiszűrése és letisztítása RSS-ből.
   - **0 tokenes előnézet:** Cím, szerző, olvasási idő és az **első X karakter** azonnali megjelenítése kártyán.
   - **Swipe vezérlés:** `⬅️ Előző`, `❌ Skip (Elvetés)`, `🔖 Félreteszem`, `⚡ Gyors AI Összefoglaló` (csak a kiválasztott cikkekre, helyi cache-eléssel), `Következő ➡️` és egykattintásos átküldés a teljes Zettelkasten -> Notion munkafolyamatba.

---

## 📁 Mappastruktúra

```
yt_notes/
├── .env                           # API kulcsok (Gemini, Notion) - .gitignore-ban kizárva!
├── .env.example                   # Minta konfigurációs fájl
├── .gitignore                     # Biztonsági kizárások (.env, data/, cache, venv)
├── requirements.txt               # Szükséges Python csomagok
├── README.md                      # Dokumentáció
├── app.py                         # Streamlit webes alkalmazás (YouTube + Substack Swipe)
├── data/
│   └── substack_state.json        # Automatikusan mentett követett írók, skip lista és AI cache
├── scripts/
│   ├── test_connection.py         # Kapcsolat- és kvóta-ellenőrző diagnosztikai script
│   └── test_substack_pipeline.py  # End-to-end Substack RSS + AI + Notion + UI pipeline teszt
└── src/
    ├── __init__.py
    ├── config.py                  # Konfigurációk, modell metadata és kvóták
    ├── prompts.py                 # Kétlépcsős Zettelkasten + Substack Swipe prompt sablonok
    └── services/
        ├── __init__.py
        ├── ai_service.py          # Gemini API hívások és token-metrikák
        ├── notion_service.py      # Notion API kapcsolat és blokk-konverter
        ├── substack_service.py    # Substack RSS olvasás, paywall-szűrés és állapotkezelés
        └── youtube_service.py     # Playlist beolvasás és felirat letöltés
```

---

## 🚀 Indítás

A felület elindításához futtasd a terminálban:

```powershell
python -m streamlit run app.py
```

Ezután nyisd meg a böngésződben: **http://localhost:8501**

Diagnosztika futtatása terminálból:
```powershell
python scripts/test_connection.py
```

---

## ☁️ Streamlit Cloud Telepítés & Biztonság

1. GitHub-ra commit és push után nyisd meg a [share.streamlit.io](https://share.streamlit.io/) oldalt.
2. Hozd létre az alkalmazást (`app.py`, `master` branch).
3. Az **Advanced settings... -> Secrets** részbe másold be:
```toml
GOOGLE_API_KEY = "IdeMásoldAGoogleKulcsot"
NOTION_API_KEY = "IdeMásoldANotionKulcsot"
NOTION_DATABASE_ID = "86585ef1-f1a6-4ab4-b183-c4f78a452e21"
APP_PASSWORD = "SajátErősJelszavad"
DEFAULT_PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLr-48e7JNg_5abe8pP-7fZCMM2KThq61z"
```
*(Az `APP_PASSWORD` beállításával az oldal egy bejelentkező képernyőt jelenít meg, így illetéktelenek nem tudnak belépni, nem égethetik az AI kvótádat, és nem látják a Notion adatbázisodat).*

---

## 📊 Token- és Kvótahasználat

A bal oldalsávban valós időben látható:
- **Munkamenet tokenjei**: Összes felhasznált token a nyitás óta.
- **AI hívások száma**: Elvégzett generálások száma.
- **Utolsó hívás bontása**: Bemeneti (prompt) tokenek, kimeneti (válasz) tokenek, felhasznált modell és időbélyeg.
- **Free Tier Napi Kvótakeret (RPD)**: Vizuális folyamatjelző a napi 1500 kérésből felhasznált hívásokról.
- **Közvetlen link**: [Google AI Studio Kreditek és Tervek](https://aistudio.google.com/plan_information).
