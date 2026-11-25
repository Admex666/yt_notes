import os
import datetime
from typing import Optional
import streamlit as st
from dotenv import load_dotenv

from src.config import (
    NOTION_DATABASE_ID,
    MODEL_METADATA,
    DEFAULT_MODEL,
    PLAN_INFO_URL,
    DEFAULT_PLAYLIST_URL,
)
from src.services import youtube_service, notion_service, ai_service, substack_service

load_dotenv()

st.set_page_config(
    page_title="Zettelkasten Note Maker (YouTube & Substack)",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Egyedi CSS stílusok (beleértve a Substack Swipe kártyát)
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #555;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .badge-saved {
        background-color: #d4edda;
        color: #155724;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-new {
        background-color: #cce5ff;
        color: #004085;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-bookmarked {
        background-color: #fff3cd;
        color: #856404;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .swipe-card {
        background-color: #ffffff;
        border: 1px solid #e0e4e8;
        border-radius: 14px;
        padding: 24px 28px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05);
        margin-bottom: 16px;
    }
    .swipe-meta {
        color: #6c757d;
        font-size: 0.9rem;
        margin-bottom: 8px;
    }
    .swipe-excerpt {
        background-color: #f8f9fa;
        border-left: 4px solid #ff6719;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        font-size: 0.98rem;
        line-height: 1.6;
        color: #212529;
        margin-top: 12px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE INICIALIZÁLÁSA ---
if "videos" not in st.session_state:
    st.session_state.videos = []
if "existing_urls" not in st.session_state:
    st.session_state.existing_urls = set()
if "database_tags" not in st.session_state:
    st.session_state.database_tags = []
if "selected_video_idx" not in st.session_state:
    st.session_state.selected_video_idx = 0
if "transcripts" not in st.session_state:
    st.session_state.transcripts = {}
if "narratives" not in st.session_state:
    st.session_state.narratives = {}
if "notes" not in st.session_state:
    st.session_state.notes = {}
if "note_titles" not in st.session_state:
    st.session_state.note_titles = {}
if "note_tags" not in st.session_state:
    st.session_state.note_tags = {}

# Substack specifikus session state
if "substack_state" not in st.session_state:
    st.session_state.substack_state = substack_service.load_state()
if "substack_articles" not in st.session_state:
    st.session_state.substack_articles = []
if "substack_swipe_idx" not in st.session_state:
    st.session_state.substack_swipe_idx = 0
if "substack_deep_dive_id" not in st.session_state:
    st.session_state.substack_deep_dive_id = None

# Token- és kvótastatisztika session state
if "token_stats" not in st.session_state:
    st.session_state.token_stats = {
        "total_calls": 0,
        "prompt_tokens": 0,
        "candidate_tokens": 0,
        "total_tokens": 0,
        "last_call": None
    }


def record_token_usage(usage: dict, task_name: str):
    """Rögzíti az elvégzett API hívás token adatait."""
    if not usage:
        return
    p_tok = usage.get("prompt_tokens", 0)
    c_tok = usage.get("candidate_tokens", 0)
    t_tok = usage.get("total_tokens", 0)

    st.session_state.token_stats["total_calls"] += 1
    st.session_state.token_stats["prompt_tokens"] += p_tok
    st.session_state.token_stats["candidate_tokens"] += c_tok
    st.session_state.token_stats["total_tokens"] += t_tok
    st.session_state.token_stats["last_call"] = {
        "task": task_name,
        "prompt_tokens": p_tok,
        "candidate_tokens": c_tok,
        "total_tokens": t_tok,
        "model": usage.get("model", ""),
        "time": datetime.datetime.now().strftime("%H:%M:%S")
    }


def render_zettelkasten_workflow(
    item_id: str,
    item_title: str,
    item_url: str,
    source_text: Optional[str],
    model_choice: str,
    current_meta: dict,
    lang_choice: str,
    notion_db_id: str,
    is_youtube: bool = True
):
    """
    Közös kétlépcsős Zettelkasten munkafolyamat (Narratívák -> Végső jegyzet -> Notion mentés)
    mind YouTube videókhoz, mind Substack cikkekhez.
    """
    st.markdown("### 1. Lépés: Narratívák azonosítása")

    btn_label = "💡 Narratívák generálása az AI-val"
    btn_type = "primary" if not st.session_state.narratives.get(item_id) else "secondary"

    col_act1, _ = st.columns([1, 1])
    with col_act1:
        if st.button(btn_label, type=btn_type, key=f"btn_narr_{item_id}", use_container_width=True):
            if is_youtube and not source_text:
                with st.spinner("1/2: Leirat letöltése..."):
                    t_text, _, err = youtube_service.get_video_transcript(item_id)
                    if err or not t_text:
                        st.error(f"Hiba a leirat lekérésekor: {err}")
                        st.stop()
                    source_text = t_text
                    st.session_state.transcripts[item_id] = t_text

            if not source_text:
                st.error("Nincs elérhető szöveg a feldolgozáshoz.")
                st.stop()

            with st.spinner(f"Narratívák feltárása {current_meta['display_name']} modellel..."):
                narratives, usage, err = ai_service.generate_narratives(
                    item_title, item_url, source_text, model=model_choice
                )
                if err:
                    st.error(err)
                else:
                    record_token_usage(usage, "Narratívák generálása")
                    st.session_state.narratives[item_id] = narratives
                    st.rerun()

    if source_text:
        label_prefix = "📜 Videó leirata" if is_youtube else "📜 Teljes cikk szövege"
        with st.expander(f"{label_prefix} (kb. {len(source_text.split())} szó)"):
            st.text_area("Nyers szöveg", source_text, height=220, disabled=True, key=f"raw_{item_id}")

    current_narratives = st.session_state.narratives.get(item_id)
    if current_narratives:
        st.markdown("#### 🔍 Azonosított narratívák és összehasonlítás:")
        st.markdown(current_narratives)
        st.divider()

        st.markdown("### 2. Lépés: Válaszd ki a kívánt narratívát és fókuszt")

        col_opt1, col_opt2 = st.columns([1, 1])
        with col_opt1:
            choice_type = st.selectbox(
                "Választási mód",
                options=["Egyszerű opció (pl. 1, 2, 3)", "Kombináció (pl. 1 + 3)", "Mindegyik / Átfogó", "Egyedi instrukció"],
                key=f"choice_type_{item_id}"
            )
            if choice_type == "Egyszerű opció (pl. 1, 2, 3)":
                selected_narrative_input = st.radio(
                    "Válaszd ki az elsődleges narratívát:",
                    ["1", "2", "3", "4"],
                    horizontal=True,
                    key=f"radio_narr_{item_id}"
                )
            elif choice_type == "Kombináció (pl. 1 + 3)":
                selected_narrative_input = st.text_input("Kombináció megadása:", value="1 + 2", key=f"comb_{item_id}")
            elif choice_type == "Mindegyik / Átfogó":
                selected_narrative_input = "Mindegyik / Comprehensive synthesis"
            else:
                selected_narrative_input = st.text_input("Egyedi narratíva leírás:", value="", key=f"cust_{item_id}")

        with col_opt2:
            user_comments = st.text_area(
                "Saját megjegyzések, kérdések vagy egyedi fókusz (opcionális):",
                placeholder="Pl. 'Fókuszáljunk a praktikus frameworkökre és a döntéshozatali modellekre...'",
                height=100,
                key=f"comm_{item_id}"
            )

        st.markdown("### 3. Lépés: Végső Zettelkasten jegyzet generálása")

        if st.button("✍️ Jegyzet elkészítése a kiválasztott narratívával", type="primary", key=f"btn_final_{item_id}", use_container_width=True):
            with st.spinner("Zettelkasten jegyzet generálása folyamatban..."):
                note_content, parsed_title, suggested_tags, usage, err = ai_service.generate_final_note(
                    title=item_title,
                    url=item_url,
                    transcript=source_text,
                    narratives_text=current_narratives,
                    selected_narratives=selected_narrative_input,
                    user_comments=user_comments,
                    available_tags=st.session_state.database_tags,
                    language=lang_choice,
                    model=model_choice
                )
                if err:
                    st.error(err)
                else:
                    record_token_usage(usage, "Végső jegyzet generálása")
                    st.session_state.notes[item_id] = note_content
                    st.session_state.note_titles[item_id] = parsed_title
                    st.session_state.note_tags[item_id] = [t for t in suggested_tags if t in st.session_state.database_tags]
                    st.rerun()

    current_note = st.session_state.notes.get(item_id)
    if current_note:
        st.divider()
        st.markdown("### 4. Lépés: Jegyzet áttekintése és mentése a Notionbe")

        col_edit1, col_edit2 = st.columns([2, 1])
        with col_edit1:
            edit_title = st.text_input(
                "Jegyzet címe (Notion Name):",
                value=st.session_state.note_titles.get(item_id, item_title),
                key=f"edit_title_{item_id}"
            )
        with col_edit2:
            default_tags = st.session_state.note_tags.get(item_id, [])
            all_tags = list(st.session_state.database_tags)
            for dt in default_tags:
                if dt not in all_tags:
                    all_tags.append(dt)

            selected_tags = st.multiselect(
                "Címkék (Tags):",
                options=all_tags,
                default=default_tags,
                key=f"tags_{item_id}"
            )

        with st.expander("📄 Teljes jegyzet előnézete (kattints a lenyitáshoz)", expanded=True):
            st.markdown(current_note)

        if st.button("🚀 Mentés a Notion 'Zettelkasten Notes [PT]' adatbázisba", type="primary", key=f"save_notion_{item_id}", use_container_width=True):
            with st.spinner("Mentés a Notionbe..."):
                success, msg, page_url = notion_service.create_zettelkasten_note(
                    database_id=notion_db_id,
                    title=edit_title,
                    video_url=item_url,
                    tags=selected_tags,
                    markdown_content=current_note
                )
                if success:
                    st.success("🎉 Sikeresen elmentve a Notionbe!")
                    if page_url:
                        st.markdown(f"👉 **[Kattints ide a jegyzet megnyitásához a Notionben]({page_url})**")
                    st.session_state.existing_urls.add(item_url)
                else:
                    st.error(f"Hiba a mentés során: {msg}")


# --- OLDALSÁV (Módválasztó, Beállítások és Token statisztika) ---
with st.sidebar:
    st.markdown("### 🧭 Forrás / Mód")
    app_mode = st.radio(
        "Válassz modult:",
        options=["🎥 YouTube Jegyzetelő", "📰 Substack Swipe"],
        index=0,
        label_visibility="collapsed"
    )
    st.divider()

    # Mód-specifikus forrásbeállítások közvetlenül felül a gyors elérésért
    if app_mode == "🎥 YouTube Jegyzetelő":
        st.markdown("### 📋 YouTube Forrás")
        playlist_url = st.text_input(
            "YouTube Playlist vagy Videó URL",
            value=DEFAULT_PLAYLIST_URL,
            placeholder="https://www.youtube.com/playlist?list=..."
        )

        if st.button("📥 Videók betöltése", type="primary", use_container_width=True):
            if not playlist_url:
                st.error("Kérlek adj meg egy érvényes YouTube linket!")
            else:
                with st.spinner("Videók adatainak lekérése..."):
                    v_list = youtube_service.get_playlist_videos(playlist_url)
                    if v_list:
                        st.session_state.videos = v_list
                        st.session_state.selected_video_idx = 0
                        st.success(f"Betöltve {len(v_list)} videó!")
                    else:
                        st.error("Nem sikerült videókat találni ezen a linken.")
    else:
        st.markdown("### 📰 Követett Substack Írók")
        sub_state = st.session_state.substack_state

        new_feed_input = st.text_input(
            "Új Substack hozzáadása",
            placeholder="pl. pragmaticengineer vagy https://...",
            help="Megadhatsz Substack nevet (pl. lennysnewsletter), teljes URL-t vagy @szerzo linket."
        )
        if st.button("➕ Író felvétele", use_container_width=True):
            norm = substack_service.normalize_substack_feed_url(new_feed_input)
            if not norm:
                st.warning("Adj meg egy érvényes Substack nevet vagy URL-t!")
            elif norm in sub_state["feeds"]:
                st.info("Ez a csatorna már szerepel a listádban.")
            else:
                with st.spinner("Csatorna ellenőrzése..."):
                    test_arts, pub_name, err = substack_service.fetch_feed_articles(norm, max_items=3)
                    if err:
                        st.error(err)
                    else:
                        sub_state["feeds"].append(norm)
                        substack_service.save_state(sub_state)
                        st.success(f"Hozzáadva: {pub_name or norm} ({len(test_arts)} ingyenes cikk észlelve)")
                        st.rerun()

        if sub_state["feeds"]:
            with st.expander(f"📚 Követett csatornák ({len(sub_state['feeds'])})", expanded=False):
                for idx_f, f_url in enumerate(list(sub_state["feeds"])):
                    c_f1, c_f2 = st.columns([4, 1])
                    short_label = f_url.replace("https://", "").replace("http://", "").replace("/feed", "")
                    c_f1.caption(short_label)
                    if c_f2.button("🗑️", key=f"del_feed_{idx_f}", help="Eltávolítás"):
                        sub_state["feeds"].remove(f_url)
                        substack_service.save_state(sub_state)
                        st.rerun()

        max_per_writer = st.slider("Legfrissebb cikkek / író", min_value=3, max_value=20, value=8)
        preview_chars = st.slider("Előnézet hossza (karakter)", min_value=200, max_value=2000, value=650, step=50)

        if st.button("🔄 Cikkek lekérése / Frissítés", type="primary", use_container_width=True):
            if not sub_state["feeds"]:
                st.warning("Előbb vegyél fel legalább egy Substack írót fent!")
            else:
                with st.spinner("Ingyenes Substack cikkek letöltése..."):
                    arts, errs = substack_service.fetch_all_followed_articles(
                        sub_state["feeds"], max_per_feed=max_per_writer
                    )
                    st.session_state.substack_articles = arts
                    st.session_state.substack_swipe_idx = 0
                    st.session_state.substack_deep_dive_id = None
                    if errs:
                        for e in errs:
                            st.warning(e)
                    st.success(f"Betöltve {len(arts)} ingyenes cikk!")

    st.divider()
    st.header("⚙️ Általános Beállítások")

    notion_db_id = st.text_input("Notion Adatbázis ID", value=NOTION_DATABASE_ID)

    if st.button("🔄 Notion szinkronizálása", use_container_width=True):
        with st.spinner("Notion adatok lekérdezése..."):
            st.session_state.existing_urls = notion_service.get_existing_video_urls(notion_db_id)
            st.session_state.database_tags = notion_service.get_database_tags(notion_db_id)
            st.success(f"Szinkronizálva! ({len(st.session_state.existing_urls)} mentett elem)")

    if not st.session_state.database_tags and notion_db_id:
        st.session_state.existing_urls = notion_service.get_existing_video_urls(notion_db_id)
        st.session_state.database_tags = notion_service.get_database_tags(notion_db_id)

    st.caption(f"📁 **Notion:** {len(st.session_state.existing_urls)} korábbi jegyzet észlelve")

    model_options = list(MODEL_METADATA.keys())
    model_choice = st.selectbox(
        "Gemini AI Modell",
        options=model_options,
        index=0,
        format_func=lambda m: MODEL_METADATA[m]["display_name"]
    )
    current_meta = MODEL_METADATA[model_choice]

    lang_choice = st.selectbox(
        "Jegyzet / Összefoglaló nyelve",
        options=["Az eredeti nyelven", "Hungarian", "English"],
        index=0
    )

    st.divider()

    # --- TOKEN & KVÓTA STATISZTIKA ---
    st.markdown("### 📊 Token- és Kvótahasználat")

    stats = st.session_state.token_stats
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric(label="Összes token", value=f"{stats['total_tokens']:,}")
    with col_m2:
        st.metric(label="AI hívások", value=f"{stats['total_calls']} db")

    if stats["last_call"]:
        last = stats["last_call"]
        with st.expander(f"🕒 Utolsó hívás ({last['task']} - {last['time']})", expanded=False):
            st.write(f"• **Prompt tokenek:** {last['prompt_tokens']:,}")
            st.write(f"• **Válasz tokenek:** {last['candidate_tokens']:,}")
            st.write(f"• **Összesen:** {last['total_tokens']:,}")
            st.write(f"• **Modell:** {last['model']}")

    rpd_limit = current_meta.get("rpd", 1500)
    calls_today = stats["total_calls"]
    progress_val = min(1.0, calls_today / rpd_limit) if rpd_limit else 0.0

    st.write(f"**Napi kvótakeret (RPD):** {calls_today} / {rpd_limit:,} kérés")
    st.progress(progress_val)

    st.caption(
        f"**Csomag:** Ingyenes Free Tier\n\n"
        f"• **Sebességhatár (RPM):** {current_meta.get('rpm', 15)} kérés/perc\n\n"
        f"• **Tokenlimit (TPM):** {current_meta.get('tpm', 1000000):,} token/perc"
    )
    st.markdown(f"[🔗 Google AI Studio Részletes Kvóta & Kreditek]({PLAN_INFO_URL})")


# =====================================================================
# 1. NÉZET: YOUTUBE JEGYZETELŐ
# =====================================================================
if app_mode == "🎥 YouTube Jegyzetelő":
    st.markdown('<div class="main-header">🧠 YouTube Zettelkasten Note Maker</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Alakítsd a YouTube videók leiratait mély, strukturált Notion Zettelkasten jegyzetekké a saját narratíváid szerint.</div>', unsafe_allow_html=True)

    if not st.session_state.videos:
        st.info("👈 Kezdésként másold be a YouTube Playlist (vagy egyedi videó) linkjét a bal oldalsávba, majd kattints a **Videók betöltése** gombra!")
        st.stop()

    videos = st.session_state.videos
    saved_urls = st.session_state.existing_urls

    video_options = []
    for idx, v in enumerate(videos):
        status_icon = "✅ [Mentve]" if v["url"] in saved_urls else "🆕 [Új]"
        video_options.append(f"{idx + 1}. {status_icon} {v['title']}")

    selected_option = st.selectbox(
        "Válassz videót a feldolgozáshoz:",
        options=range(len(video_options)),
        format_func=lambda i: video_options[i],
        index=st.session_state.selected_video_idx
    )
    st.session_state.selected_video_idx = selected_option
    current_video = videos[selected_option]
    v_id = current_video["id"]
    v_url = current_video["url"]
    v_title = current_video["title"]

    col_v1, col_v2 = st.columns([1, 3])
    with col_v1:
        if current_video.get("thumbnail"):
            st.image(current_video["thumbnail"], use_container_width=True)
    with col_v2:
        st.subheader(v_title)
        if v_url in saved_urls:
            st.markdown('<span class="badge-saved">✅ Már szerepel a Notion adatbázisban</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge-new">🆕 Még nincs elmentve a Notionben</span>', unsafe_allow_html=True)
        st.markdown(f"🔗 [Megnyitás a YouTube-on]({v_url})")
        if current_video.get("uploader"):
            st.caption(f"Feltöltő: {current_video['uploader']}")

    st.divider()

    render_zettelkasten_workflow(
        item_id=v_id,
        item_title=v_title,
        item_url=v_url,
        source_text=st.session_state.transcripts.get(v_id),
        model_choice=model_choice,
        current_meta=current_meta,
        lang_choice=lang_choice,
        notion_db_id=notion_db_id,
        is_youtube=True
    )

# =====================================================================
# 2. NÉZET: SUBSTACK SWIPE & ZETTELKASTEN
# =====================================================================
else:
    st.markdown('<div class="main-header">📰 Substack Swipe & Zettelkasten</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Böngészd át gyorsan a követett Substack írók ingyenes cikkeit: '
        'cím + első X karakter azonnali előnézet (0 token), kérésre gyors AI összefoglaló, vagy mély Zettelkasten jegyzet.</div>',
        unsafe_allow_html=True
    )

    sub_state = st.session_state.substack_state
    all_articles = st.session_state.substack_articles
    saved_urls = st.session_state.existing_urls

    if not sub_state["feeds"]:
        st.info("👈 Vegyél fel legalább egy Substack írót a bal oldalsávban (pl. `lennysnewsletter` vagy `pragmaticengineer`), majd kattints a **Cikkek lekérése** gombra!")
        st.stop()

    if not all_articles:
        st.info("👈 Kattints a bal oldalsávban a **🔄 Cikkek lekérése / Frissítés** gombra a legújabb ingyenes cikkek betöltéséhez!")
        st.stop()

    # Szűrési sáv (Új / Mentett könyvjelzők / Összes)
    col_flt1, col_flt2, col_flt3 = st.columns([2, 2, 1])
    with col_flt1:
        filter_mode = st.radio(
            "Nézet szűrő:",
            options=["🔥 Swipe Várólista", "🔖 Félretett (Könyvjelzők)", "📚 Összes cikk"],
            index=0,
            horizontal=True
        )
    with col_flt2:
        pubs = ["Összes író"] + sorted(list({a["publication"] for a in all_articles}))
        selected_pub = st.selectbox("Szűrés író / csatorna szerint:", options=pubs)
    with col_flt3:
        if sub_state["dismissed_urls"]:
            if st.button(f"♻️ Elvetettek visszaállítása ({len(sub_state['dismissed_urls'])})"):
                sub_state["dismissed_urls"] = []
                substack_service.save_state(sub_state)
                st.rerun()

    dismissed_set = set(sub_state.get("dismissed_urls", []))
    bookmarked_set = set(sub_state.get("bookmarked_urls", []))

    filtered_articles = []
    for art in all_articles:
        if selected_pub != "Összes író" and art["publication"] != selected_pub:
            continue
        if filter_mode == "🔥 Swipe Várólista":
            if art["url"] in dismissed_set or art["url"] in saved_urls:
                continue
        elif filter_mode == "🔖 Félretett (Könyvjelzők)":
            if art["url"] not in bookmarked_set:
                continue
        filtered_articles.append(art)

    if not filtered_articles:
        st.success("🎉 Nincs több cikk ebben a nézetben! Válts szűrőt vagy frissítsd a csatornákat.")
        st.stop()

    # Biztosítjuk, hogy a swipe index határon belül maradjon
    if st.session_state.substack_swipe_idx >= len(filtered_articles):
        st.session_state.substack_swipe_idx = 0
    if st.session_state.substack_swipe_idx < 0:
        st.session_state.substack_swipe_idx = len(filtered_articles) - 1

    curr_idx = st.session_state.substack_swipe_idx
    art = filtered_articles[curr_idx]
    art_id = art["url"]

    # Gyors ugrás legördülővel, ha böngészni szeretne a listában is
    with st.expander(f"📋 Gyorslista ({curr_idx + 1} / {len(filtered_articles)} cikk ebben a nézetben)", expanded=False):
        jump_idx = st.selectbox(
            "Ugrás egy konkrét cikkre:",
            options=range(len(filtered_articles)),
            format_func=lambda i: f"{i + 1}. [{filtered_articles[i]['publication']}] {filtered_articles[i]['title']} ({filtered_articles[i]['published_date']})",
            index=curr_idx
        )
        if jump_idx != curr_idx:
            st.session_state.substack_swipe_idx = jump_idx
            st.session_state.substack_deep_dive_id = None
            st.rerun()

    # --- SWIPE KÁRTYA MEGJELENÍTÉSE ---
    excerpt_raw = art["content"][:preview_chars].strip()
    if len(art["content"]) > preview_chars:
        excerpt_raw += "..."
    # HTML-biztos sortörések az idéző dobozban
    excerpt_html = excerpt_raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n\n", "<br><br>").replace("\n", " ")

    badges_html = ""
    if art["url"] in saved_urls:
        badges_html += '<span class="badge-saved">✅ Notionben mentve</span> '
    else:
        badges_html += '<span class="badge-new">🆕 Új cikk</span> '
    if art["url"] in bookmarked_set:
        badges_html += '<span class="badge-bookmarked">🔖 Félretéve</span> '

    st.markdown(f"**Kártya: {curr_idx + 1} / {len(filtered_articles)}**")

    card_cols = st.columns([3, 1]) if art.get("thumbnail") else [1]
    with card_cols[0]:
        subtitle_block = f"<p style='color:#495057; font-style:italic; margin-top:4px;'>{art['subtitle']}</p>" if art.get("subtitle") else ""
        st.markdown(
            f"""
            <div class="swipe-card">
                <div class="swipe-meta">
                    ✍️ <strong>{art['author']}</strong> ({art['publication']}) &nbsp;•&nbsp;
                    📅 {art['published_date']} &nbsp;•&nbsp;
                    ⏱️ ~{art['reading_time_min']} perc ({art['word_count']:,} szó)
                </div>
                <div style="margin-bottom:8px;">{badges_html}</div>
                <h2 style="margin-top:4px; margin-bottom:6px;">{art['title']}</h2>
                {subtitle_block}
                <div class="swipe-excerpt">
                    <strong>📖 Első {preview_chars} karakter:</strong><br>
                    {excerpt_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(f"🔗 [Eredeti cikk megnyitása Substacken]({art['url']})")

    if art.get("thumbnail") and len(card_cols) > 1:
        with card_cols[1]:
            st.image(art["thumbnail"], use_container_width=True)

    # --- KVÓTATAKARÉKOS GYORS AI ÖSSZEFOGLALÓ (CSAK KÉRÉSRE, CACHE-ELVE) ---
    cached_summary = sub_state["summaries"].get(art_id)
    if cached_summary:
        st.info(f"**⚡ AI Gyors-összefoglaló (gyorsítótárazva):**\n\n{cached_summary}")

    # --- SWIPE VEZÉRLŐ GOMBOK ---
    b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns([1, 1.3, 1.5, 1.6, 1])

    with b_col1:
        if st.button("⬅️ Előző", use_container_width=True):
            st.session_state.substack_swipe_idx = (curr_idx - 1) % len(filtered_articles)
            st.session_state.substack_deep_dive_id = None
            st.rerun()

    with b_col2:
        if st.button("❌ Skip (Elvetés)", use_container_width=True, help="Nem érdekel – leveszi a várólistáról"):
            if art_id not in sub_state["dismissed_urls"]:
                sub_state["dismissed_urls"].append(art_id)
                substack_service.save_state(sub_state)
            st.session_state.substack_deep_dive_id = None
            st.rerun()

    with b_col3:
        is_bm = art_id in bookmarked_set
        bm_label = "🔖 Félretéve (Kivesz)" if is_bm else "🔖 Félreteszem"
        if st.button(bm_label, use_container_width=True):
            if is_bm:
                sub_state["bookmarked_urls"].remove(art_id)
            else:
                sub_state["bookmarked_urls"].append(art_id)
                st.session_state.substack_swipe_idx = (curr_idx + 1) % len(filtered_articles)
            substack_service.save_state(sub_state)
            st.rerun()

    with b_col4:
        sum_label = "🔄 AI Összefoglaló újra" if cached_summary else "⚡ Gyors AI Összefoglaló"
        if st.button(sum_label, use_container_width=True, help="Rövid, 10 másodperces AI összefoglaló csak erre a cikkre"):
            with st.spinner("Gyors összefoglaló készítése..."):
                s_text, usage, err = ai_service.generate_swipe_summary(
                    title=art["title"],
                    author=art["author"],
                    publication=art["publication"],
                    url=art["url"],
                    content=art["content"],
                    language=lang_choice,
                    model=model_choice
                )
                if err:
                    st.error(err)
                else:
                    record_token_usage(usage, "Substack gyors-összefoglaló")
                    sub_state["summaries"][art_id] = s_text
                    substack_service.save_state(sub_state)
                    st.rerun()

    with b_col5:
        if st.button("Következő ➡️", use_container_width=True):
            st.session_state.substack_swipe_idx = (curr_idx + 1) % len(filtered_articles)
            st.session_state.substack_deep_dive_id = None
            st.rerun()

    # Mélyfeldolgozás gomb (lenyitja a Zettelkasten munkafolyamatot erre a cikkre)
    deep_active = (st.session_state.substack_deep_dive_id == art_id) or (art_id in st.session_state.narratives)
    if not deep_active:
        if st.button("🧠 Tetszik! Mély Zettelkasten jegyzet készítése ebből a cikkből 👇", type="primary", use_container_width=True):
            st.session_state.substack_deep_dive_id = art_id
            st.rerun()
    else:
        st.divider()
        st.subheader("🧠 Zettelkasten Mélyfeldolgozás")
        render_zettelkasten_workflow(
            item_id=art_id,
            item_title=art["title"],
            item_url=art["url"],
            source_text=art["content"],
            model_choice=model_choice,
            current_meta=current_meta,
            lang_choice=lang_choice,
            notion_db_id=notion_db_id,
            is_youtube=False
        )
