# NUS Course Agent

An AI-powered NUS module planning assistant with:

- a FastAPI backend that streams SSE events
- a Next.js frontend chat UI
- live module data from NUSMods
- module search, detail lookup, and timetable generation

This README describes how the current codebase works and how to run it locally.

## Current Architecture

- `backend/`
  - `main.py`: FastAPI app, `/`, `/health`, `/chat/stream`, `/auth/*`, `/users/*`
  - `agent.py`: LLM tool-calling loop (supports dynamic config)
  - `tools.py`: NUSMods search, module detail lookup, timetable builder
  - `database/models/auth`: Auth logic and SQLite persistence
- `frontend/`
  - `src/app/page.tsx`: main chat page with integrated auth
  - `src/components/`: Login and Settings modals

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
- `JWT_SECRET_KEY`
  - Random string for signing login tokens.
- `DB_ENCRYPTION_KEY`
  - Fernet key for encrypting API keys in the database.

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

### User Authentication & Data Security

This project now features a **local authentication system**:
- **Login**: Passwordless login using NUS Email OTP (verification code is printed to the terminal in local mode).
- **Domain Restriction**: Only emails ending in `.nus.edu` or `nus.edu.sg` are allowed.
- **Data Persistence**: User settings (including custom API keys) are stored in `backend/app.db`.
- **Security**: 
  - `app.db` is excluded from Git.
  - Sensitive database fields (API Keys) are **encrypted** using the `DB_ENCRYPTION_KEY` from your `.env`.
  - API keys are **masked** in the UI.

## 🚀 Quick Start with Docker (Recommended)

The easiest way to deploy this project locally or on a cloud server (Aliyun, etc.) is using Docker.

1. **Clone the repo**
2. **Setup environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```
3. **Run with one command**:
   ```bash
   docker-compose up --build -d
   ```
4. **Access the app**:
   - Frontend: `http://localhost`
   - Backend API: `http://localhost/api`

---

## Backend Startup (Manual)

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
- `sqlalchemy`
- `python-jose[cryptography]`
- `passlib`

Frontend scripts from `frontend/package.json`:

- `npm run dev`
- `npm run build`
- `npm run start`
- `npm run lint`

## Deployment (Cloud)

To deploy this project to a remote server (e.g., Aliyun):

### 1. Backend Setup
- Use a production server like Gunicorn: `pip install gunicorn`
- Set `ALLOWED_ORIGINS` in `.env` to your frontend domain.
- To enable real email OTP:
  - Sign up for [Resend](https://resend.com).
  - Add `RESEND_API_KEY` to your `.env`.
- Run: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000`

### 2. Frontend Setup
- Create a `.env.production` file in the `frontend` directory:
  ```env
  NEXT_PUBLIC_API_URL=https://api.yourdomain.com
  ```
- Build the app: `npm run build`
- Start the server: `npm run start` (or serve via Nginx).

### 3. Nginx Configuration
It is highly recommended to use Nginx as a reverse proxy for SSL and to handle both frontend and backend on ports 80/443.

---

## Reference Files
...
