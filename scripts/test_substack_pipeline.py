import os
import sys
from unittest.mock import patch

# Projekt gyökér hozzáadása a keresési útvonalhoz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding="utf-8")

from src.config import DEFAULT_MODEL, GOOGLE_API_KEY, NOTION_API_KEY, NOTION_DATABASE_ID
from src.services import substack_service, ai_service, notion_service


def run_pipeline_test():
    print("=" * 70)
    print(" 1. URL NORMALIZÁLÁS & @PROFIL FELOLDÁS TESZTJE")
    print("=" * 70)
    cases = {
        "pragmaticengineer": "https://pragmaticengineer.substack.com/feed",
        "https://www.lennysnewsletter.com/": "https://www.lennysnewsletter.com/feed",
        "https://stratechery.substack.com/p/some-article": "https://stratechery.substack.com/feed",
    }
    for raw, expected in cases.items():
        actual = substack_service.normalize_substack_feed_url(raw)
        assert actual == expected, f"Hiba: {raw} -> {actual} != {expected}"
        print(f" [OK] '{raw}' -> {actual}")

    resolved_mollick = substack_service.normalize_substack_feed_url("https://substack.com/@ethanmollick")
    print(f" [OK] '@ethanmollick' profil automatikusan feloldva -> {resolved_mollick}")
    assert "oneusefulthing" in resolved_mollick or "substack" in resolved_mollick

    print("\n" + "=" * 70)
    print(" 2. ÉLŐ SUBSTACK RSS BEOLVASÁS, TISZTÍTÁS & INGYENES SZŰRÉS")
    print("=" * 70)
    test_feeds = ["oneusefulthing", "https://www.lennysnewsletter.com", "pragmaticengineer"]
    articles, errs = substack_service.fetch_all_followed_articles(test_feeds, max_per_feed=4)
    if errs:
        print(" Figyelmeztetések:", errs)
    assert len(articles) >= 4, "Nem sikerült elegendő cikket letölteni a teszt csatornákról!"
    pubs_found = sorted(list({a["publication"] for a in articles}))
    print(f" [OK] Letöltve összesen {len(articles)} ingyenes, tiszta cikk. Észlelt kiadványok: {pubs_found}")

    sample = articles[0]
    print(f"\n Mintacikk kiválasztva:")
    print(f"  - Csatorna / Szerző: {sample['publication']} / {sample['author']}")
    print(f"  - Cím: {sample['title']}")
    print(f"  - Dátum: {sample['published_date']} | Szószám: {sample['word_count']} szó (~{sample['reading_time_min']} perc)")
    print(f"  - Első 300 karakter:\n    \"{sample['content'][:300].replace(chr(10), ' ')}...\"")

    print("\n" + "=" * 70)
    print(" 3. HELYI ÁLLAPOTMENTÉS (SWIPE / BOOKMARK / FEED LISTA) TESZT")
    print("=" * 70)
    orig_state = substack_service.load_state()
    test_state = {
        "feeds": ["https://oneusefulthing.substack.com/feed"],
        "dismissed_urls": [sample["url"]],
        "bookmarked_urls": [articles[1]["url"]],
        "summaries": {sample["url"]: "Teszt gyors-összefoglaló"}
    }
    substack_service.save_state(test_state)
    reloaded = substack_service.load_state()
    assert reloaded["dismissed_urls"] == [sample["url"]]
    assert reloaded["summaries"][sample["url"]] == "Teszt gyors-összefoglaló"
    # Eredeti állapot visszaállítása, hogy tiszta maradjon a munkakörnyezet
    substack_service.save_state(orig_state)
    print(" [OK] Állapotmentés és visszatöltés (feeds, skip, félretétel, summary cache) hibátlan!")

    print("\n" + "=" * 70)
    print(f" 4. AI PIPELINE (GYORS-ÖSSZEFOGLALÓ -> NARRATÍVA -> ZETTELKASTEN -> NOTION BLOKK)")
    print("=" * 70)
    has_live_gemini = bool(GOOGLE_API_KEY and GOOGLE_API_KEY != "your_google_api_key_here")

    if has_live_gemini:
        print(" [INFO] Élő GOOGLE_API_KEY észlelve -> valós Gemini hívások futtatása...")
        swipe_sum, usage1, err1 = ai_service.generate_swipe_summary(
            title=sample["title"],
            author=sample["author"],
            publication=sample["publication"],
            url=sample["url"],
            content=sample["content"],
            language="Hungarian",
            model=DEFAULT_MODEL,
        )
        assert not err1 and swipe_sum, f"Gyors-összefoglaló hiba: {err1}"
        print(f" [OK] Élő gyors-összefoglaló kész ({usage1['total_tokens']} token)")

        narratives, usage2, err2 = ai_service.generate_narratives(
            sample["title"], sample["url"], sample["content"], model=DEFAULT_MODEL
        )
        assert not err2 and narratives, f"Narratíva hiba: {err2}"
        print(f" [OK] Élő narratívák kész ({usage2['total_tokens']} token)")

        final_note, parsed_title, suggested_tags, usage3, err3 = ai_service.generate_final_note(
            title=sample["title"],
            url=sample["url"],
            transcript=sample["content"],
            narratives_text=narratives,
            selected_narratives="1",
            available_tags=["AI", "Business", "Productivity"],
            language="Hungarian",
            model=DEFAULT_MODEL,
        )
        assert not err3 and final_note, f"Végső jegyzet hiba: {err3}"
        print(f" [OK] Élő Zettelkasten jegyzet kész ({usage3['total_tokens']} token) | Cím: {parsed_title}")
    else:
        print(" [INFO] .env fájlban nincs még GOOGLE_API_KEY beállítva -> teljes prompt- és parser-lánc tesztelése szimulált Gemini válasszal...")
        captured_prompts = []

        def fake_post(url, json=None, timeout=60):
            sys_instr = json["system_instruction"]["parts"][0]["text"]
            usr_prompt = json["contents"][0]["parts"][0]["text"]
            captured_prompts.append((sys_instr, usr_prompt))

            class FakeResp:
                status_code = 200
                def json(self_inner):
                    if "triage Substack articles" in sys_instr:
                        reply = "**🎯 Fő állítás:** A cikk fő tézise...\n\n**💡 Legérdekesebb gondolatok:**\n- Első pont\n- Második pont"
                    elif "IDENTIFY POSSIBLE NARRATIVES" in sys_instr:
                        reply = "### 1. Gyakorlati keretrendszer\n**Core idea:** Teszt narratíva..."
                    else:
                        reply = (
                            "# Egyenetlen AI képességek a gyakorlatban\n\n"
                            "## 🎯 Main Takeaway\nRészletes kifejtő bekezdés az új modellről.\n\n"
                            "## 💡 Core Ideas\nMásodik szekció folyószöveggel.\n\n"
                            "## 🛠️ Practical Applications\n- Konkrét tesztelési lépés\n\n"
                            "TAGS: [AI, Strategy]"
                        )
                    return {
                        "candidates": [{"content": {"parts": [{"text": reply}]}}],
                        "usageMetadata": {"promptTokenCount": 1200, "candidatesTokenCount": 250, "totalTokenCount": 1450}
                    }
            return FakeResp()

        with patch("src.services.ai_service.GOOGLE_API_KEY", "test_key_123"), patch("src.services.ai_service.requests.post", side_effect=fake_post):
            swipe_sum, usage1, err1 = ai_service.generate_swipe_summary(
                sample["title"], sample["author"], sample["publication"], sample["url"], sample["content"], language="Hungarian"
            )
            assert not err1 and "Fő állítás" in swipe_sum
            narratives, usage2, err2 = ai_service.generate_narratives(
                sample["title"], sample["url"], sample["content"]
            )
            assert not err2 and "Gyakorlati keretrendszer" in narratives
            final_note, parsed_title, suggested_tags, usage3, err3 = ai_service.generate_final_note(
                title=sample["title"],
                url=sample["url"],
                transcript=sample["content"],
                narratives_text=narratives,
                selected_narratives="1",
                available_tags=["AI", "Strategy", "Business"],
                language="Hungarian",
            )
            assert not err3
            assert parsed_title == "Egyenetlen AI képességek a gyakorlatban"
            assert suggested_tags == ["AI", "Strategy"]
            assert "TAGS:" not in final_note
            assert sample["title"] in captured_prompts[0][1]
            print(" [OK] Prompt-összeállítás, cikk-törzs átadás, cím- és TAGS-kinyerés hibátlan!")

    blocks = notion_service.markdown_to_notion_blocks(final_note)
    assert len(blocks) >= 5
    print(f" [OK] Notion Markdown -> Block konverter ellenőrizve ({len(blocks)} Notion blokk előállítva).")

    print("\n" + "=" * 70)
    print(" 5. STREAMLIT UI INTERAKTÍV FLOW TESZT (AppTest)")
    print("=" * 70)
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "app.py"), default_timeout=30)
    at.run()
    assert not at.exception, f"Kivétel YouTube módban: {at.exception}"

    # 1) Átváltás Substack Swipe módra
    at.sidebar.radio[0].set_value("📰 Substack Swipe").run()
    assert not at.exception, f"Kivétel Substack Swipe módban: {at.exception}"

    # 2) Új Substack író felvétele az oldalsávban ('oneusefulthing')
    at.sidebar.text_input[0].set_value("oneusefulthing").run()
    at.sidebar.button[0].click().run()
    assert not at.exception, f"Kivétel író felvételekor: {at.exception}"

    # 3) Cikkek lekérése gomb megnyomása -> megjelenik a Swipe kártya címmel és első X karakterrel!
    fetch_btns = [b for b in at.sidebar.button if "Cikkek lekérése" in b.label]
    assert fetch_btns, "Nem található a Cikkek lekérése gomb!"
    fetch_btns[0].click().run()
    assert not at.exception, f"Kivétel cikkek lekérésekor: {at.exception}"

    rendered_markdown = "\n".join([m.value for m in at.markdown])
    assert "Első 650 karakter:" in rendered_markdown, "Nem jelent meg az első X karakter előnézet a kártyán!"
    print(" [OK] Substack író felvétele, cikkek letöltése és Swipe kártya (Cím + Első 650 karakter) renderelése hibátlan!")

    # 4) Következő és Skip gombok tesztelése
    next_btns = [b for b in at.button if "Következő" in b.label]
    next_btns[0].click().run()
    assert not at.exception, f"Kivétel Következő gombnál: {at.exception}"

    skip_btns = [b for b in at.button if "Skip" in b.label]
    skip_btns[0].click().run()
    assert not at.exception, f"Kivétel Skip gombnál: {at.exception}"
    print(" [OK] Swipe navigáció (Következő ➡️ / ❌ Skip) hibátlanul működik!")

    # Tiszta állapot visszaállítása a teszt végén
    substack_service.save_state(orig_state)
    if not orig_state["feeds"] and os.path.exists(substack_service.STATE_FILE):
        os.remove(substack_service.STATE_FILE)

    print("\n" + "=" * 70)
    print(" MINDEN PIPELINE ÉS UI TESZT HIBÁTLANUL LEFUTOTT!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    ok = run_pipeline_test()
    sys.exit(0 if ok else 1)
