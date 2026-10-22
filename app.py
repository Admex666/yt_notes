import os
import datetime
import streamlit as st
from dotenv import load_dotenv

from src.config import (
    NOTION_DATABASE_ID,
    MODEL_METADATA,
    DEFAULT_MODEL,
    PLAN_INFO_URL,
    DEFAULT_PLAYLIST_URL,
    DEFAULT_LANGUAGE
)
from src.services import youtube_service, notion_service, ai_service

load_dotenv()

st.set_page_config(
    page_title="YouTube Zettelkasten Note Maker",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Egyedi CSS stílusok
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
    .token-box {
        background-color: #f1f3f5;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 12px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Session state inicializálása
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

# --- OLDALSÁV (Beállítások és Token statisztika) ---
with st.sidebar:
    st.header("⚙️ Beállítások")

    # Notion konfiguráció
    default_db = NOTION_DATABASE_ID
    notion_db_id = st.text_input("Notion Adatbázis ID", value=default_db)
    
    if st.button("🔄 Notion szinkronizálása", width="stretch"):
        with st.spinner("Notion adatok lekérdezése..."):
            st.session_state.existing_urls = notion_service.get_existing_video_urls(notion_db_id)
            st.session_state.database_tags = notion_service.get_database_tags(notion_db_id)
            st.success(f"Szinkronizálva! ({len(st.session_state.existing_urls)} mentett videó)")

    if not st.session_state.database_tags and notion_db_id:
        st.session_state.existing_urls = notion_service.get_existing_video_urls(notion_db_id)
        st.session_state.database_tags = notion_service.get_database_tags(notion_db_id)

    st.caption(f"📁 **Notion:** {len(st.session_state.existing_urls)} korábbi jegyzet észlelve")
    st.divider()

    # Modell választó
    model_options = list(MODEL_METADATA.keys())
    model_choice = st.selectbox(
        "Gemini AI Modell",
        options=model_options,
        index=0,
        format_func=lambda m: MODEL_METADATA[m]["display_name"]
    )
    current_meta = MODEL_METADATA[model_choice]

    lang_choice = st.selectbox(
        "Jegyzet nyelve",
        options=["A videó eredeti nyelve", "Hungarian", "English"],
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

    # Utolsó hívás részletei
    if stats["last_call"]:
        last = stats["last_call"]
        with st.expander(f"🕒 Utolsó hívás ({last['task']} - {last['time']})", expanded=False):
            st.write(f"• **Prompt tokenek:** {last['prompt_tokens']:,}")
            st.write(f"• **Válasz tokenek:** {last['candidate_tokens']:,}")
            st.write(f"• **Összesen:** {last['total_tokens']:,}")
            st.write(f"• **Modell:** {last['model']}")

    # Google Free Tier limitek és kvóták
    rpd_limit = current_meta.get("rpd", 1500)
    calls_today = stats["total_calls"]
    progress_val = min(1.0, calls_today / rpd_limit) if rpd_limit else 0.0

    st.write(f"**Napi kvótakeret (RPD):** {calls_today} / {rpd_limit:,} kérés")
    st.progress(progress_val)

    st.caption(
        f"**Csomag:** Ingyenes Free Tier\n\n"
        f"• **Sebességhatár (RPM):** {current_meta.get('rpm', 15)} kérés/perc\n\n"
        f"• **Tokenlimit (TPM):** {current_meta.get('tpm', 1000000):,} token/perc\n\n"
        f"*(A Google nem küld vissza fennmaradó keret fejlécet, de a hívásokat és kvótákat követi.)*"
    )
    st.markdown(f"[🔗 Google AI Studio Részletes Kvóta & Kreditek]({PLAN_INFO_URL})")

    st.divider()

    # Playlist beolvasás
    st.markdown("### 📋 YouTube Forrás")
    playlist_url = st.text_input(
        "YouTube Playlist vagy Videó URL",
        value=DEFAULT_PLAYLIST_URL,
        placeholder="https://www.youtube.com/playlist?list=..."
    )

    if st.button("📥 Videók betöltése", type="primary", width="stretch"):
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

# --- FŐ KÉPERNYŐ ---
st.markdown('<div class="main-header">🧠 YouTube Zettelkasten Note Maker</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Alakítsd a YouTube videók leiratait mély, strukturált Notion Zettelkasten jegyzetekké a saját narratíváid szerint.</div>', unsafe_allow_html=True)

if not st.session_state.videos:
    st.info("👈 Kezdésként másold be a YouTube Playlist (vagy egyedi videó) linkjét a bal oldalsávba, majd kattints a **Videók betöltése** gombra!")
    st.stop()

# Videó választó
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

# Videó kártya
col_v1, col_v2 = st.columns([1, 3])
with col_v1:
    if current_video.get("thumbnail"):
        st.image(current_video["thumbnail"], width="stretch")
with col_v2:
    st.subheader(v_title)
    is_saved = v_url in saved_urls
    if is_saved:
        st.markdown('<span class="badge-saved">✅ Már szerepel a Notion adatbázisban</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-new">🆕 Még nincs elmentve a Notionben</span>', unsafe_allow_html=True)
    st.markdown(f"🔗 [Megnyitás a YouTube-on]({v_url})")
    if current_video.get("uploader"):
        st.caption(f"Feltöltő: {current_video['uploader']}")

st.divider()

# --- 1. LÉPÉS: LEIRAT ÉS NARRATÍVÁK ---
st.markdown("### 1. Lépés: Narratívák azonosítása")

transcript_text = st.session_state.transcripts.get(v_id)

col_act1, col_act2 = st.columns([1, 1])
with col_act1:
    if st.button("💡 Narratívák generálása az AI-val", type="primary" if not st.session_state.narratives.get(v_id) else "secondary", width="stretch"):
        with st.spinner("1/2: Leirat letöltése..."):
            if not transcript_text:
                t_text, lang, err = youtube_service.get_video_transcript(v_id)
                if err or not t_text:
                    st.error(f"Hiba a leirat lekérésekor: {err}")
                    st.stop()
                transcript_text = t_text
                st.session_state.transcripts[v_id] = t_text
        
        with st.spinner(f"2/2: Narratívák feltárása {current_meta['display_name']} modellel..."):
            narratives, usage, err = ai_service.generate_narratives(
                v_title, v_url, transcript_text, model=model_choice
            )
            if err:
                st.error(err)
            else:
                record_token_usage(usage, "Narratívák generálása")
                st.session_state.narratives[v_id] = narratives
                st.rerun()

# Leirat megtekintése expanderben
if transcript_text:
    with st.expander(f"📜 Videó leirata (kb. {len(transcript_text.split())} szó)"):
        st.text_area("Nyers szöveg", transcript_text, height=200, disabled=True)

# Narratívák megjelenítése
current_narratives = st.session_state.narratives.get(v_id)
if current_narratives:
    st.markdown("#### 🔍 Azonosított narratívák és összehasonlítás:")
    st.markdown(current_narratives)
    st.divider()

    # --- 2. LÉPÉS: NARRATÍVA VÁLASZTÁS & SZEMÉLYRE SZABÁS ---
    st.markdown("### 2. Lépés: Válaszd ki a kívánt narratívát és fókuszt")
    
    col_opt1, col_opt2 = st.columns([1, 1])
    with col_opt1:
        choice_type = st.selectbox(
            "Választási mód",
            options=["Egyszerű opció (pl. 1, 2, 3)", "Kombináció (pl. 1 + 3)", "Mindegyik / Átfogó", "Egyedi instrukció"]
        )
        if choice_type == "Egyszerű opció (pl. 1, 2, 3)":
            selected_narrative_input = st.radio("Válaszd ki az elsődleges narratívát:", ["1", "2", "3", "4"], horizontal=True)
        elif choice_type == "Kombináció (pl. 1 + 3)":
            selected_narrative_input = st.text_input("Kombináció megadása:", value="1 + 2")
        elif choice_type == "Mindegyik / Átfogó":
            selected_narrative_input = "Mindegyik / Comprehensive synthesis"
        else:
            selected_narrative_input = st.text_input("Egyedi narratíva leírás:", value="")

    with col_opt2:
        user_comments = st.text_area(
            "Saját megjegyzések, kérdések vagy egyedi fókusz (opcionális):",
            placeholder="Pl. 'Fókuszáljunk a praktikus frameworkökre és a döntéshozatali modellekre...'",
            height=100
        )

    # --- 3. LÉPÉS: JEGYZET GENERÁLÁSA ---
    st.markdown("### 3. Lépés: Végső Zettelkasten jegyzet generálása")
    
    if st.button("✍️ Jegyzet elkészítése a kiválasztott narratívával", type="primary", width="stretch"):
        with st.spinner("Zettelkasten jegyzet generálása folyamatban..."):
            note_content, parsed_title, suggested_tags, usage, err = ai_service.generate_final_note(
                title=v_title,
                url=v_url,
                transcript=transcript_text,
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
                st.session_state.notes[v_id] = note_content
                st.session_state.note_titles[v_id] = parsed_title
                st.session_state.note_tags[v_id] = [t for t in suggested_tags if t in st.session_state.database_tags]
                st.rerun()

# --- 4. LÉPÉS: ELŐNÉZET ÉS NOTION MENTÉS ---
current_note = st.session_state.notes.get(v_id)
if current_note:
    st.divider()
    st.markdown("### 4. Lépés: Jegyzet áttekintése és mentése a Notionbe")

    col_edit1, col_edit2 = st.columns([2, 1])
    with col_edit1:
        edit_title = st.text_input(
            "Jegyzet címe (Notion Name):",
            value=st.session_state.note_titles.get(v_id, v_title)
        )
    with col_edit2:
        default_tags = st.session_state.note_tags.get(v_id, [])
        all_tags = list(st.session_state.database_tags)
        for dt in default_tags:
            if dt not in all_tags:
                all_tags.append(dt)

        selected_tags = st.multiselect(
            "Címkék (Tags):",
            options=all_tags,
            default=default_tags
        )

    # Jegyzet előnézete
    with st.expander("📄 Teljes jegyzet előnézete (kattints a lenyitáshoz)", expanded=True):
        st.markdown(current_note)

    # Mentés gomb
    if st.button("🚀 Mentés a Notion 'Zettelkasten Notes [PT]' adatbázisba", type="primary", width="stretch"):
        with st.spinner("Mentés a Notionbe..."):
            success, msg, page_url = notion_service.create_zettelkasten_note(
                database_id=notion_db_id,
                title=edit_title,
                video_url=v_url,
                tags=selected_tags,
                markdown_content=current_note
            )
            if success:
                st.success("🎉 Sikeresen elmentve a Notionbe!")
                if page_url:
                    st.markdown(f"👉 **[Kattints ide a jegyzet megnyitásához a Notionben]({page_url})**")
                st.session_state.existing_urls.add(v_url)
            else:
                st.error(f"Hiba a mentés során: {msg}")
