# 🧠 YouTube Zettelkasten Note Maker

Egy moduláris, kétlépcsős munkafolyamat YouTube videók leiratainak feldolgozásához, a saját érdeklődési köreid és narratíváid szerint, közvetlen **Notion Zettelkasten Notes [PT]** integrációval, token- és kvótakövetéssel.

---

## 📁 Mappastruktúra

```
yt_notes/
├── .env                       # API kulcsok (Gemini, Notion) - .gitignore-ban kizárva!
├── .env.example               # Minta konfigurációs fájl
├── .gitignore                 # Biztonsági kizárások (.env, cache, venv)
├── requirements.txt           # Szükséges Python csomagok
├── README.md                  # Dokumentáció
├── app.py                     # Streamlit webes alkalmazás (belépési pont)
├── scripts/
│   └── test_connection.py    # Kapcsolat- és kvóta-ellenőrző diagnosztikai script
└── src/
    ├── __init__.py
    ├── config.py              # Konfigurációk, modell metadata és kvóták
    ├── prompts.py             # A kétlépcsős Two-Shot prompt sablonok
    └── services/
        ├── __init__.py
        ├── ai_service.py      # Gemini API hívások és token-metrikák
        ├── notion_service.py  # Notion API kapcsolat és blokk-konverter
        └── youtube_service.py # Playlist beolvasás és felirat letöltés
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

## 📊 Token- és Kvótahasználat

A bal oldalsávban valós időben látható:
- **Munkamenet tokenjei**: Összes felhasznált token a nyitás óta.
- **AI hívások száma**: Elvégzett generálások száma.
- **Utolsó hívás bontása**: Bemeneti (prompt) tokenek, kimeneti (válasz) tokenek, felhasznált modell és időbélyeg.
- **Free Tier Napi Kvótakeret (RPD)**: Vizuális folyamatjelző a napi 1500 kérésből felhasznált hívásokról.
- **Közvetlen link**: [Google AI Studio Kreditek és Tervek](https://aistudio.google.com/plan_information).
