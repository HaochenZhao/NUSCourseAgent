# NUS Course Agent

An AI-powered NUS module planning assistant with:

- a FastAPI backend that streams SSE events
- a Next.js frontend chat UI
- live module data from NUSMods
- module search, detail lookup, and timetable generation

This README describes how the current codebase works and how to run it locally.

## Current Architecture

- `backend/`
  - `main.py`: FastAPI app, `/`, `/health`, `/chat/stream`
  - `agent.py`: LLM tool-calling loop
  - `tools.py`: NUSMods search, module detail lookup, timetable builder
- `frontend/`
  - `src/app/page.tsx`: main chat page
  - `src/app/globals.css`: UI styling

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- One OpenAI-compatible API key

## Backend Configuration

The backend reads configuration from environment variables in `backend/agent.py`.

Required:

- `OPENAI_API_KEY`

Optional:

- `OPENAI_MODEL`
  - default: `gpt-5-mini`
- `OPENAI_BASE_URL`
  - default: `https://api.qingyuntop.top/v1`

Recommended setup:

1. Create a virtual environment.
2. Install backend dependencies.
3. Put your API settings in `backend/.env`.

Example `backend/.env`:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5-mini
OPENAI_BASE_URL=https://api.qingyuntop.top/v1
```

Notes:

- This project does not use the old `LLM_PROVIDER`, `GOOGLE_API_KEY`, or `OPENROUTER_API_KEY` settings anymore.
- There is no demo/simulation fallback in the current backend. If `OPENAI_API_KEY` is missing, `/health` will fail and chat requests will return an error.

## Backend Startup

Run the backend from the `backend/` directory.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Why port `8000`:

- the frontend currently calls `http://localhost:8000`
- `TEST_REPORT.md` also assumes backend on `localhost:8000`

Available backend endpoints:

- `GET /`
- `GET /health`
- `POST /chat/stream`

Quick check:

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
```

## Frontend Startup

Run the frontend from the `frontend/` directory.

```bash
cd frontend
npm install
npm run dev
```

Then open:

- `http://localhost:3000`

## Important Frontend Assumption

The frontend currently hardcodes the backend URL in `frontend/src/app/page.tsx`:

```ts
const API_BASE = "http://localhost:8000";
```

That means:

- backend should run on port `8000`
- if you want a different backend host or port, update `API_BASE` in the frontend code

## Typical Local Run Order

Open two terminals.

Terminal 1:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2:

```bash
cd frontend
npm run dev
```

After both are running:

1. Open `http://localhost:3000`
2. Fill in the student profile on the left
3. Ask the agent for module recommendations or a timetable

## How Streaming Works

The backend responds from `/chat/stream` as `text/event-stream`.

The frontend listens for events such as:

- `tool_call`
- `text_delta`
- `timetable`
- `error`
- `done`

This is why you see intermediate statuses like:

- `Searching modules...`
- `Fetching module details...`
- `Building timetable...`

## Common Issues

### 1. Frontend loads but chat fails

Check:

- backend is running on `localhost:8000`
- `OPENAI_API_KEY` is set
- `GET /health` returns success

### 2. `/health` fails

Usually caused by:

- missing `OPENAI_API_KEY`
- invalid `OPENAI_BASE_URL`
- invalid model name
- upstream provider/network issue

### 3. Frontend cannot reach backend

Check:

- backend command was run inside `backend/`
- backend is listening on port `8000`
- frontend `API_BASE` still matches backend address

### 4. Response feels slow

This is expected for some requests because the backend may:

- search modules multiple times
- fetch full details for several modules
- call timetable generation at the end

The frontend now shows loading progress more clearly, but the backend still depends on external LLM and NUSMods response times.

## Current Dependencies

Backend packages from `backend/requirements.txt`:

- `fastapi`
- `uvicorn`
- `requests`
- `openai`
- `python-dotenv`
- `pydantic`

Frontend scripts from `frontend/package.json`:

- `npm run dev`
- `npm run build`
- `npm run start`
- `npm run lint`

## Reference Files

- [TEST_REPORT.md](./TEST_REPORT.md): current tested scenarios
- [DESIGN.md](./DESIGN.md): design notes
