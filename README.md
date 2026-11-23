# SmartStudy AI

A personalised learning companion for Singapore Primary 2–4 students. Parents upload Mathematics and English worksheets; the app generates simple explanations, practice questions and progress tracking. See [spec.md](spec.md) for the full behaviour.

| Part | Tech |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript (`frontend/`) |
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic (`backend/`) |
| Database | PostgreSQL (also stores worksheet files, table `stored_files`) |
| AI / documents | OpenAI API, PyMuPDF, Tesseract OCR |

## Local development

Prerequisites: Node.js 20.9+, [uv](https://docs.astral.sh/uv/), PostgreSQL, and [Tesseract](https://github.com/tesseract-ocr/tesseract) on your PATH (or set `TESSERACT_CMD`).

```bash
# Backend
cd backend
cp .env.example .env          # then fill in DATABASE_URL, SESSION_SECRET, OPENAI_API_KEY
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
uv run pytest                 # tests use SQLite in memory and mock OpenAI

# Frontend (second terminal)
cd frontend
cp .env.local.example .env.local
npm install
npm run dev                   # http://localhost:3000
```

## Deployment (free tier)

| Part | Host | Notes |
|---|---|---|
| Frontend | Vercel (Hobby) | Root directory `frontend`. Hobby is for non-commercial use only. |
| Backend | Render (Free web service, Docker) | Root directory `backend`, region Singapore. Sleeps after 15 min idle; first request then takes ~1 min. |
| Database | Neon (Free) | Region AWS Singapore. 1 GB shared by data and worksheet files. |

The browser only talks to the Vercel site. `frontend/proxy.ts` forwards `/api/*` to the backend with a shared secret and the visitor's IP, so login cookies stay first-party and the backend refuses direct calls (except `/health`).

### 1. Neon
Create a project in **AWS Asia Pacific 1 (Singapore)** with only Postgres enabled. Under **Connect**, turn **Connection pooling off** and copy the direct connection string. Paste it into Render unchanged; the backend converts it for asyncpg.

### 2. Render (backend)
New **Web Service** → this repo → **Language: Docker**, **Root Directory: `backend`**, **Region: Singapore**, **Instance type: Free**, **Health Check Path: `/health`**. Environment variables:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon direct connection string |
| `SESSION_SECRET` | new random value: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `PROXY_SHARED_SECRET` | another new random value (also goes into Vercel) |
| `OPENAI_API_KEY` | your key (set a monthly usage limit in the OpenAI dashboard) |
| `OCR_PROVIDER` | `tesseract` |
| `TRUST_PROXY_HEADER` | `x-client-ip` |
| `COOKIE_SECURE` | `true` |

Migrations run automatically on each start (`alembic upgrade head`). Check `https://<service>.onrender.com/health` returns `{"status":"ok"}`.

### 3. Vercel (frontend)
Import this repo, **Root Directory: `frontend`**. Environment variables:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `/` |
| `BACKEND_URL` | `https://<service>.onrender.com` |
| `PROXY_SHARED_SECRET` | same value as on Render |

`NEXT_PUBLIC_API_URL` is baked in at build time, so redeploy after changing it.

### 4. Smoke test
- Register, log in, add a child, select the child with the PIN, practise.
- Upload a worksheet and wait for it to become ready; check the dashboard.
- Upload a file close to 10 MB.
- Calling `https://<service>.onrender.com/api/auth/me` directly returns 404.
- After 15+ idle minutes, the site wakes up and still works.

Secrets live only in the host dashboards. Never commit `.env` files.
