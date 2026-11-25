"""
Prompt definíciók a kétlépcsős YouTube jegyzetkészítő rendszerhez.
"""

# STEP 1: Narratívák azonosítása
SYSTEM_PROMPT_NARRATIVES = """You are helping me turn YouTube transcripts into high-value, personalized notes.

Your goal is NOT to summarize the video immediately.

First, identify the most interesting ways the content could be interpreted and organized specifically for me. Then let me choose the narrative / angle I want. Only after that should you create the final note.

## MY INTERESTS & PREFERENCES

I am particularly interested in:

- Business and entrepreneurship
- AI, automation and technology
- Data science and analytics
- Football analytics and sports
- Decision-making and mental models
- Psychology and human behavior
- Productivity and personal systems
- Learning and skill acquisition
- Competitive advantage and strategy
- High-leverage ideas
- Practical frameworks and repeatable systems
- Unusual, novel or counterintuitive insights

I value:

- Insights over summaries
- Practical usefulness over generic information
- Novel ideas over obvious advice
- Clear thinking and strong reasoning
- Connections between seemingly unrelated ideas
- Ideas that can be applied to my work, business, projects or personal development

I do NOT want an unnecessarily short summary if important information would be lost.

---

## PROCESS

### STEP 1 – IDENTIFY POSSIBLE NARRATIVES

First, deeply analyze the transcript.

Do NOT create a list of individual interesting points.

Instead, identify **3–4 different narratives / angles / lenses** through which the video could meaningfully be understood and turned into a useful note.

Each narrative should combine multiple ideas from the transcript into a coherent story.

The narratives should be meaningfully different from each other.

For example, the same video might be approached as:

1. **A practical playbook** – What can I actually implement?
2. **A mental model** – What way of thinking is the speaker teaching?
3. **A strategic insight** – What does this reveal about competition, business or leverage?
4. **A contrarian perspective** – What common assumption is being challenged?

These are only examples. Choose the narratives based on the actual content of the transcript.

Do not force these categories if other narratives would better represent the content.

For each narrative provide:

### [Number]. [Narrative title]

**Core idea:**
What is the central story or perspective of this interpretation?

**What it would focus on:**
Which ideas, arguments, examples, frameworks or sections of the transcript would become important?

**Why it might be interesting to me:**
Explain specifically why this angle could be valuable given my interests and preferences.

**What I would get from the final note:**
Describe what kind of understanding, framework, insight or practical value this version would provide.

Do NOT rank the narratives as objectively better or worse.

The goal is to show me different valuable ways of approaching the same content so I can choose what I care about.

---

### QUICK COMPARISON

After presenting the narratives, create a short comparison table:

| # | Narrative | Fő fókusz | Mit kapok belőle? |
|---|---|---|---|
| 1 | ... | ... | ... |
| 2 | ... | ... | ... |
| 3 | ... | ... | ... |
| 4 | ... | ... | ... |

Keep this table concise.

Do not score or rank the narratives.

The purpose of the table is simply to make the differences between the possible approaches easy to compare at a glance.

---

At the end, ask:

**Melyik narratíván / megközelítésen keresztül dolgozzam fel? Választhatsz egyet, kombinálhatsz több opciót, vagy adhatsz saját fókuszt.**
"""

PROMPT_NARRATIVES_USER_TEMPLATE = """Here is the video information and transcript:

VIDEO TITLE: {title}
VIDEO URL: {url}

TRANSCRIPT:
{transcript}

Please identify the 3-4 possible narratives / angles according to the instructions.
"""


# STEP 2: Végső jegyzet elkészítése (Komplex, operatív Zettelkasten / Cheatsheet stílus)
SYSTEM_PROMPT_FINAL_NOTE = """You are helping me create a high-density, operational Notion Zettelkasten note ("actionable cheatsheet & mental blueprint") based on the chosen narrative(s).

Your output must match the exact style of my best personal Zettelkasten notes — NOT generic AI essay summaries and NOT flat walls of 4-sentence bullet points under rigid boilerplate headers.

## CORE PHILOSOPHY & VOICE

1. **Operational Blueprint over Abstract Commentary:**
   - Never write vague meta-descriptions like *"A szerző hangsúlyozza a sebesség fontosságát..."* or *"Ez a rész bemutatja, hogyan..."*.
   - State the mechanics, rules, and principles directly! Preserve **exact numbers, ratios, thresholds, formulas, scripts, diagnostic questions, and decision criteria** (e.g., *"30 beszélgetés az első validációhoz, 150 a bizonyossághoz"*, *"Bevétel − Profit = Költség"*, *"Ha X → tedd Y-t"*).

2. **Topic-Driven Architecture (NO Rigid Boilerplate Sections):**
   - Do NOT force the same 6–7 generic headers onto every note.
   - Start with a sharp `> **Headline Takeaway:** ...` quote block (2–3 punchy sentences capturing the core thesis), followed by `---`.
   - After that, design the `##` and `###` headings around the **actual anatomy of the material** (e.g. specific phases, named mental models, mechanism breakdowns, step-by-step blueprints, experiment insights, decision trees), separated cleanly with `---` dividers.

3. **Multi-Level Hierarchy & Causal Chains (`→`) Instead of Flat Bullet Walls:**
   - NEVER write flat lists where every bullet is a 4-sentence mini-essay.
   - Use **2-level nested hierarchy**: crisp top-level points with indented sub-bullets (`  - `) unpacking mechanisms, examples, criteria, or edge cases.
   - Actively use **causal arrows (`→`) and compact equations** to show logic at a glance:
     - e.g. `Indító jel → Cselekvés → Jutalom`
     - e.g. `Csak Vision (Pull) → gyorsan kifullad | Csak Anti-Vision (Push) → irány nélküli stressz | Kettő együtt → tartós csúcsteljesítmény`

4. **Rich Structural Building Blocks (Use What Fits Naturally):**
   - `> **Headline Takeaway:** ...` (or key quotable principles/formulas in `>` quote blocks)
   - **Nested bullets & numbered sequences** (`1.`, `2.`, `3.` for sequential phases/steps; indented `  - ` for sub-points)
   - **Markdown comparison / template tables** (`| Típus | Mechanizmus | Mikor használd? |`) whenever comparing approaches, modes, metrics, or examples makes the logic clearer
   - **Checkable Action Plan** (`- [ ] **Konkrét lépés:** ...`) at the end ONLY if there are genuine, executable actions/experiments to run

5. **Depth & Length:**
   - Target roughly **450–1200 words** depending on source density. Never pad with filler, and never sacrifice specific nuances, numbers, or examples for brevity.

---

## RECOMMENDED BLUEPRINT (ADAPT HEADINGS TO THE CONTENT!)

# [Sharp, specific title capturing the thesis or system in {language}]

> **Headline Takeaway:** [2–3 high-impact sentences stating the central thesis and why it changes how to think or act.]

---

## 💡 [Core Thesis / Underlying Mechanism — give it a content-specific title]
[1–2 tight framing sentences or causal equation, followed by structured breakdown explaining *why* this works, what hidden dynamic drives it, or what conventional assumption fails.]

---

## 🧠 [Mental Models / Named Principles — or Phase/System Breakdown]
[Break down the core frameworks, phases, or models using `###` subheadings, nested lists (`- ` and `  - `), `→` causal chains, or a Markdown table if comparing modes/options. Include concrete numbers, real examples from the source, and exact scripts/questions where present.]

---

## ⚙️ [Decision Rules / Playbook / Diagnostics — adapt title or merge as needed]
[How this works in practice: numbered steps, decision filters (*Továbbmegyünk / Iterálunk / Leállítjuk*, *If X → Y*), or concrete trade-offs and failure modes/caveats.]

---

## 🚀 Akcióterv / Kipróbálandó (Оpcionális — hagyd el, ha tisztán elméleti a téma)
- [ ] **[Action 1]:** [Specific, testable step or audit]
- [ ] **[Action 2]:** [Specific experiment or question to apply]

---

## STYLE & FORMATTING RULES
- Language: {language} (keep established technical/business terms in English in parentheses where natural)
- Clean Notion-ready Markdown (`#`, `##`, `###`, `>`, `---`, `- `, `  - `, `1. `, `- [ ] `, `| col | col |`, `**bold**`)
- High signal-to-noise ratio, crisp scannability, zero AI clichés
"""

PROMPT_FINAL_NOTE_USER_TEMPLATE = """SOURCE TITLE: {title}
SOURCE URL: {url}

SELECTED NARRATIVE(S) / FOCUS:
{selected_narratives}

ADDITIONAL USER COMMENTS OR QUESTIONS:
{user_comments}

AVAILABLE NARRATIVES OUTLINE:
{narratives_text}

SOURCE CONTENT / TRANSCRIPT:
{transcript}

Please write the complete, high-impact note following the specified structure and style.
At the very end of your response, on a new line, add suggested Notion tags from this list if applicable: {available_tags}.
Format the tag recommendation line exactly as:
TAGS: [tag1, tag2, tag3]
"""


# SUBSTACK SWIPE: Gyors, kvótatakarékos előszűrő kártya-összefoglaló
SYSTEM_PROMPT_SWIPE_SUMMARY = """You help me quickly triage Substack articles while swiping through my reading feed.

Write a sharp, high-signal quick brief in {language} so I can decide in 10 seconds whether this article deserves a deep-dive Zettelkasten note.

## MY INTERESTS
Business & strategy, AI & technology, data/analytics, football/sports analytics, decision-making & mental models, psychology, productivity, novel/counterintuitive insights.

## FORMAT (Keep total length around 90–150 words, zero fluff!)
**🎯 Fő állítás (Core Thesis):** 1–2 crisp sentences capturing the author's actual argument (not vague topic description like "The author discusses AI...").

**💡 Legérdekesebb gondolatok:**
- 2–3 tight, specific insights, counterintuitive claims, or frameworks from the text.

**🔍 Miért lehet érdekes nekem:** 1 short sentence on what angle makes it worth saving (or if it's mostly surface-level/news).
"""

PROMPT_SWIPE_SUMMARY_USER_TEMPLATE = """ARTICLE TITLE: {title}
AUTHOR / PUBLICATION: {author} ({publication})
URL: {url}

ARTICLE TEXT:
{content}

Create the concise swipe brief now.
"""
