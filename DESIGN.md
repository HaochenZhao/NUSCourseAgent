# NUS Course Agent -- System Design Document

**Authors:** Wu Lyucheng, Gao Yiwen, Zhao Haochen, Zhang Haotian

---

## 1. Vision

NUS students face a fragmented course selection experience: official programme handbooks describe complex requirements in prose, NUSMods provides raw timetable data, and peer advice is scattered across forums. No single tool helps a student go from "I want to take AI courses next semester" to a concrete, conflict-free course plan.

**NUS Course Agent** is a conversational AI system that bridges this gap. The student describes their situation in natural language -- programme, year, interests, constraints -- and the agent searches NUSMods in real time, reasons about lecture schedules, checks prerequisites where applicable, and produces a personalised, conflict-free semester plan with a visual weekly timetable.

### Core design principles

1. **The LLM is the reasoner, not the database.** All factual course information (descriptions, schedules, prerequisites, exam dates) comes exclusively from NUSMods API calls. The LLM never invents module data.

2. **No hardcoded programme rules.** The system does not embed specific degree requirements (e.g. "MComp CS requires 10 modules, at least 5 from Annex A"). Instead, the student describes their eligible course pool (e.g. "all CS-prefixed courses") and the LLM works within that scope. This makes the system universally applicable to any NUS programme without code changes.

3. **Conflict prevention, not conflict repair.** The system prompt instructs the LLM to compare lecture times before recommending, and the `build_timetable` tool provides deterministic verification. Conflicts are caught early, not patched after the fact.

4. **Prerequisite handling adapts to degree level.** Postgraduate students at NUS are not bound by undergraduate prerequisite requirements. The system prompt and tool outputs are dynamically generated based on whether the student is undergraduate or postgraduate -- postgrad students never see prerequisite information at all.

---

## 2. Expected User Experience

### 2.1 Profile setup (left sidebar)

The student fills in four fields before chatting:

| Field | Example | Purpose |
|-------|---------|---------|
| **Programme** | MComp Computer Science | Free text. Gives the LLM context about the student's degree. |
| **Level** | Postgraduate / Undergraduate | Toggle. Controls two behaviours: (a) which course levels the LLM prioritises, and (b) whether prerequisite information is shown. |
| **Year of Study** | 1 | Number. The LLM uses this to prioritise appropriate course levels (Year 3 undergrad -> 3xxx courses; postgrad -> 5xxx/6xxx). |
| **Eligible Courses** | All CS-prefixed courses offered by SoC | Free text description of what courses the student may take. The LLM interprets this to decide search prefixes and filters. |
| **Semester** | 1 or 2 | Determines which semester's timetable and offering data to use. |

There is deliberately **no** "completed modules" field, **no** programme-specific dropdown, and **no** focus area selector. The system is designed to be lightweight: the student describes their situation, and the LLM handles the rest through conversation.

### 2.2 Conversation flow

**Example 1: Postgraduate student (no prerequisites)**

```
Student: Help me pick 4 AI-related courses for this semester

Agent:   [Searching modules...]
         [Fetching module details...]
         [Building timetable...]

         Here are 4 AI-related courses for Semester 1:

         | Module | Title                              | Lecture Time       | Workload |
         |--------|------------------------------------|--------------------|----------|
         | CS5242 | Neural Networks and Deep Learning  | Tue 18:30-20:30    | 3-0-0-4-3 |
         | CS5284 | Graph Machine Learning             | Wed 18:30-20:30    | 3-0-0-3-4 |
         | CS5562 | Trustworthy Machine Learning       | Fri 16:00-18:00    | 3-0-0-3-4 |
         | CS6216 | Advanced Topics in ML              | Wed 10:00-12:00    | 3-0-0-3-4 |

         No lecture conflicts. Total weekly contact: 8 hours.

         [Visual weekly timetable rendered below]
```

**Example 2: Undergraduate student (prerequisites matter)**

```
Student: I'm a Year 3 CS undergrad, recommend 3 courses in security

Agent:   [Searching modules...]
         [Fetching module details...]

         Here are 3 security courses for Semester 1:

         | Module | Title                    | Lecture Time       | Prerequisites |
         |--------|--------------------------|--------------------|----|
         | CS3235 | Computer Security        | Mon 14:00-16:00    | CS2105 and CS2107 |
         | CS3236 | Introduction to InfoSec  | Thu 10:00-12:00    | CS2107 |
         | CS4238 | Computer Security Practice | Fri 14:00-16:00  | CS3235 |

         Before I finalize:
         - CS3235 requires CS2105 and CS2107. Have you completed both?
         - CS4238 requires CS3235. Since you haven't taken it yet,
           it can't be taken this semester. Want me to find a replacement?

Student: I have CS2105 and CS2107. Replace CS4238 with something else.

Agent:   [Searching modules...]
         [Fetching module details...]
         [Building timetable...]

         Replaced CS4238 with CS3219 (Software Engineering Principles).
         Updated timetable: ...
```

### 2.3 Multi-turn adjustments

The system maintains full conversation history. Follow-up requests like "swap out CS5284 for something lighter" or "show me what's available on Thursdays" are handled incrementally -- the LLM only calls the tools it needs, not the entire pipeline from scratch.

---

## 3. System Architecture

```
                       Frontend (Next.js)
                     +-------------------+
                     | Sidebar | Chat UI |
                     | Profile | Messages|
                     | Form    | Table   |
                     +--------+----------+
                              |
                              | POST /chat/stream (SSE)
                              v
                       Backend (FastAPI)
                     +-------------------+
                     |    main.py        |  <-- Thin routing layer
                     +--------+----------+
                              |
                              v
                     +-------------------+
                     |    agent.py       |  <-- Orchestrator
                     |                   |
                     | System Prompt     |  <-- Dynamically generated
                     | (postgrad/ugrad)  |      based on profile.level
                     |                   |
                     | Agentic Loop      |  <-- LLM + tool calls, max 15 iterations
                     |   LLM call        |
                     |     |             |
                     |     +-> tool?     |
                     |     |   yes: exec |
                     |     |   append    |
                     |     |   loop back |
                     |     +-> stop?     |
                     |         emit text |
                     |         emit table|
                     +--------+----------+
                              |
                              v
                     +-------------------+
                     |    tools.py       |  <-- NUSMods data layer
                     |                   |
                     | NUSModsClient     |  <-- HTTP + LRU cache
                     | search_modules    |  <-- Tool 1
                     | get_module_details|  <-- Tool 2
                     | build_timetable   |  <-- Tool 3
                     +-------------------+
                              |
                              v
                     +-------------------+
                     | NUSMods API v2    |
                     | (external)        |
                     +-------------------+
```

### File structure

```
backend/
  .env                 # API key and model config
  requirements.txt     # fastapi, uvicorn, requests, openai, python-dotenv, pydantic
  main.py              # FastAPI app with one SSE streaming endpoint (56 lines)
  agent.py             # System prompt builder + agentic loop (376 lines)
  tools.py             # NUSMods client + 3 tool implementations (353 lines)

frontend/src/app/
  page.tsx             # Full UI: sidebar + chat + timetable renderer (535 lines)
  layout.tsx           # Next.js layout with fonts (33 lines)
  globals.css          # Tailwind imports + markdown prose styles (57 lines)
```

Total: ~1,400 lines of code.

---

## 4. The Three Tools

The LLM has access to exactly three tools. Each answers one distinct question; there is no overlap between them.

### 4.1 `search_modules` -- "What courses exist?"

**Purpose:** Discover modules by keyword search and/or code prefix filtering.

**Input:**
```json
{
  "query": "machine learning",   // keyword search in code + title
  "prefix": "CS5",               // code prefix filter (optional)
  "semester": 1                   // offered-in-semester filter (optional)
}
```

**Output:** Up to 30 results:
```json
[
  {"module_code": "CS5242", "title": "Neural Networks and Deep Learning", "semesters": [1, 2]},
  {"module_code": "CS5284", "title": "Graph Machine Learning", "semesters": [1]}
]
```

**Implementation:** Fetches the full NUSMods module list (cached after first call, ~7000 modules), filters by prefix and semester, scores by keyword match against code + title, returns top 30 sorted by relevance.

### 4.2 `get_module_details` -- "What is this course about? Can I take it?"

**Purpose:** Get complete information for specific modules so the LLM can evaluate and compare them.

**Input:**
```json
{
  "module_codes": ["CS5228", "CS5340", "CS5242"]
}
```

**Output per module:**
```json
{
  "module_code": "CS5228",
  "title": "Knowledge Discovery and Data Mining",
  "description": "This module covers the ...",
  "module_credit": "4",
  "workload": "3-0-0-3-4",
  "workload_total": 13.0,
  "lectures": ["Friday 18:30-20:30"],
  "has_exam": true,
  "exam_date": "2025-11-25T13:00:00.000Z",
  "semesters_offered": [1, 2],
  "nusmods_url": "https://nusmods.com/courses/CS5228",
  "prerequisite_text": "CS2040 and ST2334"     // ONLY for undergrad
}
```

**Key design decisions:**

- **Tutorial/Lab data is stripped.** The `semesterData[].timetable` array from NUSMods contains Lecture, Tutorial, Laboratory, and Recitation entries. This tool filters to `lessonType == "Lecture"` only. The LLM never sees tutorial information, which eliminates an entire category of irrelevant complexity.

- **Prerequisite field is conditional.** When `is_postgrad` is true, the `prerequisite_text` field is not included in the output at all. The LLM cannot mention what it cannot see. When `is_postgrad` is false, the raw prerequisite text from NUSMods is included so the LLM can present it to the student and ask for confirmation.

- **Descriptions are truncated** to 400 characters to keep LLM context manageable.

- **Batch support:** Accepts up to 10 module codes per call to minimize round-trips.

### 4.3 `build_timetable` -- "Do these courses fit together?"

**Purpose:** Validate that a set of modules have no lecture time conflicts, and produce the weekly schedule for the frontend to render as a visual timetable.

**Input:**
```json
{
  "module_codes": ["CS5228", "CS5340", "CS5242", "CS5260"]
}
```

**Output:**
```json
{
  "feasible": true,
  "conflicts": [],
  "schedule": {
    "Monday": [{"module_code": "CS5340", "start": "18:30", "end": "20:30"}],
    "Tuesday": [{"module_code": "CS5260", "start": "18:30", "end": "20:30"}],
    "Wednesday": [{"module_code": "CS5228", "start": "19:00", "end": "21:00"}],
    "Thursday": [{"module_code": "CS5242", "start": "18:30", "end": "20:30"}]
  },
  "total_contact_hours": 8.0,
  "exam_dates": {"CS5228": "2025-11-25T13:00:00.000Z"}
}
```

If conflicts exist:
```json
{
  "feasible": false,
  "conflicts": [
    {"module_a": "CS5340", "module_b": "CS5446", "slot": "Thursday 18:30-20:30"}
  ],
  "schedule": { ... },
  "total_contact_hours": 10.0,
  "exam_dates": { ... }
}
```

**Implementation:** Extracts lecture slots for each module (same lecture-only filter as `get_module_details`), performs pairwise overlap detection (same day + time range intersection), assembles the combined weekly schedule sorted by time, and calculates total contact hours.

**The frontend renders the timetable only when it receives a `timetable` SSE event**, which is emitted only when `build_timetable` returns `feasible: true`.

---

## 5. The Agent Loop

### 5.1 How it works

The agent uses the OpenAI function-calling protocol. Each iteration:

1. Send the full message history (system prompt + conversation + tool results) to the LLM
2. If the LLM responds with `finish_reason: "tool_calls"`, execute each tool, append results to the message history, and loop back to step 1
3. If the LLM responds with `finish_reason: "stop"`, the loop ends and the final text is emitted

Maximum 15 iterations. On the last iteration, tools are disabled to force a text response.

```
User message
    |
    v
[System prompt + history + user msg]
    |
    v
+-- LLM call (with tools) <---------+
|       |                            |
|   finish_reason?                   |
|   +--- "tool_calls" ---+          |
|   |                     |          |
|   |  Execute tools      |          |
|   |  Emit tool_call SSE |          |
|   |  Append results     +----------+
|   |                                
|   +--- "stop" ---------+
|                         |
|   Emit text_delta SSE   |
|   Emit timetable SSE    |
|   Emit done SSE         |
+-------------------------+
```

### 5.2 SSE event protocol

The backend streams Server-Sent Events to the frontend:

| Event | Payload | Frontend behaviour |
|-------|---------|-------------------|
| `tool_call` | `{name, display}` | Show spinner with status text (e.g. "Searching modules...") |
| `text_delta` | `{text}` | Append to assistant message bubble, render as markdown |
| `timetable` | `{schedule, total_contact_hours, ...}` | Render visual weekly timetable below the message |
| `error` | `{message}` | Show error in message bubble |
| `done` | `{}` | Stop loading state |

### 5.3 Typical execution trace

For the query "Help me pick 4 AI-related courses" from a postgrad student:

```
Iteration 1:  LLM -> search_modules(query="artificial intelligence", prefix="CS5", semester=1)
Iteration 2:  LLM -> search_modules(query="machine learning", prefix="CS5", semester=1)
Iteration 3:  LLM -> search_modules(query="deep learning neural network", prefix="CS6", semester=1)
Iteration 4:  LLM -> get_module_details(["CS5242","CS5284","CS5340","CS5562","CS6208","CS6216"])
Iteration 5:  LLM compares lecture times, picks 4 non-conflicting modules
              LLM -> build_timetable(["CS5242","CS5284","CS5562","CS6216"])
Iteration 6:  LLM -> stop, emits final markdown text
```

Total: 6 LLM calls, 5 tool executions. The LLM drives the process end-to-end.

---

## 6. System Prompt Design

The system prompt is **not a static template**. It is generated dynamically by `build_system_prompt(profile)` based on the student's level (undergraduate vs postgraduate). The two versions differ in meaningful ways:

### 6.1 Common structure

Both versions share:
- Student context block (programme, year, eligible courses, semester)
- Tool usage instructions (search -> details -> build_timetable)
- Core rules (never invent data, never recommend overlapping lectures, always call build_timetable)

### 6.2 Postgraduate-specific prompt

```
COURSE LEVEL GUIDELINES
-----------------------
This student is a postgraduate student.
Recommend 5xxx and 6xxx level courses.
```

- **No mention of prerequisites anywhere.** The word "prerequisite" does not appear.
- The `get_module_details` tool also omits the `prerequisite_text` field for postgrad, so even if the LLM tried to look for it, the data isn't there.

### 6.3 Undergraduate-specific prompt

```
COURSE LEVEL GUIDELINES
-----------------------
This student is a Year 3 undergraduate.
Prioritize 3xxx level courses, but adjacent levels are acceptable.
```

Additional instructions:
```
- Read the prerequisite_text for each module. If a module has
  prerequisites, TELL the student what they are and ASK whether
  they have completed them. Do not assume. Do not skip this.
  If the student says they cannot meet a prerequisite, find a
  replacement and re-verify the timetable.
```

Additional rule:
```
- ALWAYS show prerequisite requirements to the student and ask for
  confirmation before finalizing.
```

This means undergrad students experience a two-phase interaction: the agent proposes courses, asks about prerequisites, and then adjusts based on the student's answers. Postgrad students get direct recommendations with no prerequisite back-and-forth.

---

## 7. Data Flow: What the LLM Sees and Doesn't See

| NUSMods field | Given to LLM? | Reason |
|---------------|---------------|--------|
| moduleCode | Yes | Core identifier |
| title | Yes | Course name |
| description | Yes (truncated to 400 chars) | Helps LLM assess relevance |
| moduleCredit | Yes | Student workload planning |
| workload | Yes (formatted as "L-T-Lab-Proj-Prep") | Workload comparison |
| prerequisite (text) | **Undergrad only** | Not applicable to postgrad |
| prereqTree (structured) | **Never** | Too complex for LLM; not needed since LLM just shows text to user |
| Lecture timetable slots | Yes | For conflict checking |
| Tutorial timetable slots | **Never** | Deliberately excluded to reduce noise |
| Laboratory timetable slots | **Never** | Deliberately excluded |
| Recitation timetable slots | **Never** | Deliberately excluded |
| examDate | Yes | Exam scheduling awareness |
| preclusion | No | Edge case, LLM doesn't need it |
| corequisite | No | Edge case |

---

## 8. Frontend Design

### 8.1 Layout

```
+--[Sidebar 272px]--+--[Chat Area flex-1]------+
|                    |                          |
| Programme [input]  |  Message bubbles         |
| Level [toggle]     |  (markdown rendered)     |
| Year [number]      |                          |
| Eligible [textarea]|  Tool call indicators    |
| Semester [toggle]  |  (grey pills)            |
|                    |                          |
|                    |  Timetable visualization |
|                    |  (colour-coded grid)     |
|                    |                          |
|                    |--[Input bar]-------------|
|                    | [textarea] [Send button] |
+--------------------+--------------------------+
```

### 8.2 Timetable visualization

The timetable is rendered as a CSS-based grid:
- Y-axis: hours from 08:00 to 22:00 (48px per hour)
- X-axis: days of the week (only days with lectures shown)
- Each course gets a distinct colour from an 8-colour palette
- Slots are positioned absolutely based on start/end times
- Module code and time range displayed inside each slot

### 8.3 SSE stream handling

The frontend reads the SSE stream with a `ReadableStream` reader:
- `tool_call` events: show a spinner with the tool's display name
- `text_delta` events: append text to the assistant message and re-render markdown
- `timetable` events: attach timetable data to the current message, triggering the Timetable component
- `done` events: clear loading state

---

## 9. Configuration

All configuration is in `backend/.env`:

```
OPENAI_API_KEY=sk-...          # API key for the LLM provider
OPENAI_BASE_URL=https://...    # OpenAI-compatible API endpoint
OPENAI_MODEL=gpt-5-mini        # Model identifier
```

The system is compatible with any OpenAI-compatible API provider. To switch providers or models, only the `.env` file needs to change. No code modifications required.

---

## 10. Running the System

### Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8080
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in a browser. The frontend connects to the backend at `http://localhost:8080`.

---

## 11. Limitations and Future Work

### Current limitations

- **No tutorial/lab scheduling.** The system only considers lecture times. Students still need to arrange tutorials themselves on NUSMods.
- **Keyword search only.** `search_modules` matches on module code and title. It does not search within module descriptions, so a course about "Bayesian inference" won't match the query "AI" unless those words appear in the title.
- **No persistence.** Conversation history exists only in the browser session. Refreshing the page clears everything.
- **No course reviews or ratings.** The system only has NUSMods official data. Student sentiment, difficulty ratings, and instructor quality are not available.

### Potential improvements

- **Semantic search over descriptions.** Embed module descriptions with a small embedding model and use vector similarity instead of keyword matching.
- **Session persistence.** Store conversation history server-side so students can resume planning across sessions.
- **Multi-semester planning.** Currently the system plans one semester at a time. A future version could reason about multi-semester degree progression.
- **Integration with CourseReg data.** If bidding/enrollment data were available, the system could factor in demand and historical success rates.
