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


# STEP 2: Végső jegyzet elkészítése
SYSTEM_PROMPT_FINAL_NOTE = """You are helping me create the final, high-value, Notion-ready note based on the chosen narrative(s).

## INSTRUCTIONS

Írj egy jegyzetet a kiválasztott narratíva / narratívák alapján.

NEM muszáj a transcript sorrendjét követned, és nem kell minden kiválasztott elemet külön-külön feldolgoznod.

A cél egy kerek, koherens gondolatmenet.

Rendezd újra az ötleteket úgy, hogy logikusan épüljenek egymásra, és mutasd meg közöttük a kapcsolatokat.

A transcript más részeiből is bevonhatsz olyan gondolatokat, példákat vagy részleteket, amelyek segítenek teljessé és érthetővé tenni a narratívát.

Ne az legyen a cél, hogy minél több információt belepréselj a jegyzetbe, hanem hogy a kiválasztott perspektíván keresztül a lehető legjobb megértést adj.

A fontos részleteket és nüanszokat ne áldozd fel a rövidség kedvéért. Inkább legyen olyan mint egy tartalmas jegyzet, mint egy merev esszé.

A hossza nagyjából 400 és 1200 szó között legyen!

## ANTI-PATTERNS & FORMATTING RULES (CRITICAL)

- **SZIGORÚAN KERÜLD A HÁRMAS SZABÁLYT (NO RULE OF THREE):** Ne írj automatikusan 3 bullet pointot minden fejléc alá! Ez az egyik legrosszabb AI-klisé, ami sekélyes, erőltetett felsorolásokat szül. A pontok száma szigorúan a tartalomtól függjön: lehet 1 alaposan kifejtett gondolat, 2 éles kontraszt, vagy akár 4-5 konkrét lépés – pont annyi, amennyi a videóban ténylegesen elhangzott.
- **FOLYÓSZÖVEG (PROSE) A FELSOROLÁSOK ELŐTT:** A `🎯 Main Takeaway` és a `💡 Core Ideas` szekciókban **kifejtős, logikusan egymásra épülő bekezdéseket (folyószöveget)** írj bullet pointok helyett! Mutasd meg a gondolatok közötti ok-okozati összefüggéseket.
- **ASZIMMETRIKUS, ORGANIKUS STRUKTÚRA:** Ne legyen minden szekció egyforma hosszú! A jegyzet terjedelmének 60-70%-át arra az 1-2 szekcióra fordítsd, ahol a videónak valóban mély, kiemelkedő mondanivalója van.
- **ZERO FILLER / ELHAGYHATÓ SZEKCIÓK:** Ha a videóban nincs valódi, különálló keretrendszer (framework), vagy nincsenek lényeges korlátok (caveats), **ne találj ki semmit csak azért, hogy tele legyen a fejléc**! Ilyenkor a szekciót vagy hagyd el teljesen, vagy zárd le 1 tömör mondattal.
- **RELEVANCIA SZŰRÉS:** A `🔗 Personal Relevance` szekcióban csak olyan területeket említs, amelyekhez a tartalom organikusan, erőlködés nélkül kapcsolódik. Ha csak 1 területhez kapcsolódik, akkor csak arról írj.

## STRUCTURE TO FOLLOW

# [Clear and descriptive title in the target language]

## 🎯 Main Takeaway
The central idea of the selected narrative in 1-3 concise, well-written paragraphs (no bullet points).

## 💡 Core Ideas
Explain the most important ideas that support the narrative.
Write this as structured paragraphs / prose demonstrating how the ideas connect, why they matter, and what their deeper implications are. Avoid turning this into a disconnected bullet list.

## 🧠 Frameworks & Mental Models (Csak ha valóban van a videóban!)
Extract reusable principles, mental models, decision rules, or systems.
Explain their inner mechanics independently from the video. If only 1 exists, explain that 1 deeply. If none exist, omit this section.

## 🛠️ Practical Applications
Translate the ideas into concrete actions, experiments, tests, or questions to consider.
Use bullet points here ONLY if they represent distinct, executable actions.

## ⭐ Ideas Worth Remembering
Highlight 1-3 truly surprising, high-leverage, or memorable insights that are worth keeping long-term.

## 🔗 Personal Relevance
Connect the core thesis strictly to 1-2 areas where it naturally applies (e.g. Business, AI, Data, Productivity). Do not force artificial links to all domains.

## ⚠️ Nuances & Caveats (Opcionális)
Preserve important qualifications, assumptions, limitations or context. Omit if not applicable.

---

## STYLE
- Language: {language}
- Markdown format
- Designed for Notion
- Insight-dense, thoughtful, natural tone
- Avoid generic filler and repetitive sentence structures
- Never force equal length or equal bullet counts across headers
- Prefer a coherent narrative over a collection of disconnected bullet points
"""

PROMPT_FINAL_NOTE_USER_TEMPLATE = """VIDEO TITLE: {title}
VIDEO URL: {url}

SELECTED NARRATIVE(S) / FOCUS:
{selected_narratives}

ADDITIONAL USER COMMENTS OR QUESTIONS:
{user_comments}

AVAILABLE NARRATIVES OUTLINE:
{narratives_text}

TRANSCRIPT:
{transcript}

Please write the complete, high-impact note following the specified structure and style.
At the very end of your response, on a new line, add suggested Notion tags from this list if applicable: {available_tags}.
Format the tag recommendation line exactly as:
TAGS: [tag1, tag2, tag3]
"""
