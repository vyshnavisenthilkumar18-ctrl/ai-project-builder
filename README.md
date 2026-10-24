# AI Project Builder

A full-stack starter application for turning a project brief into a generated codebase, previewing files, downloading a ZIP, and publishing to GitHub after OAuth authorization.

## Features
- React + Vite responsive dashboard.
- FastAPI backend with project analysis/generation, file listing, ZIP download, GitHub OAuth, repository listing, and publishing.
- Server-side OpenAI-compatible AI provider integration (OpenAI API or compatible endpoint).
- Upload TXT, PDF, DOCX, PNG, JPG/JPEG/WEBP. PDF/DOCX/TXT text extraction is supported; images use optional Tesseract OCR.
- ZIP excludes secrets, `.env`, dependency folders, caches, and build outputs.
- GitHub publishing requires a signed-in session and explicit confirmation from the UI.

## Requirements
- Python 3.11+
- Node.js 20+
- An AI provider API key for AI generation.
- A GitHub OAuth App for GitHub publishing (optional).

## Setup

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
uvicorn app.main:app --reload --port 8000
```

Edit `backend/.env`:
- `SECRET_KEY`: use a long random value.
- `AI_API_KEY`: your provider key.
- `AI_BASE_URL`: defaults to OpenAI API base URL.
- `AI_MODEL`: model available to your account.
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_CALLBACK_URL`: optional GitHub OAuth settings.
- Register callback URL in GitHub OAuth App as `http://localhost:8000/api/github/callback`.
- `FRONTEND_ORIGIN=http://localhost:5173`

### 2. Frontend
Open a second terminal:
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173`.

## Environment variables
See `backend/.env.example`. Never commit `.env`. The backend uses an HTTP-only session cookie. For production, serve HTTPS, set `COOKIE_SECURE=true`, use a persistent database/session store, add rate limiting, and deploy behind a trusted proxy.

## API
- `POST /api/projects/analyze` — analyze a brief or upload.
- `POST /api/projects/generate` — generate a project; JSON `{ "topic": "...", "language": "Python + FastAPI", "framework": "React + Vite" }`.
- `GET /api/projects/{project_id}/files`
- `GET /api/projects/{project_id}/download`
- `GET /api/github/login`
- `GET /api/github/callback`
- `GET /api/github/repositories`
- `POST /api/github/publish` — JSON includes `project_id`, `mode` (`create` or `existing`), `repo_name`, `description`, `private`, `branch`, and `confirm: true`.

## Notes and limitations
- Generated source is model-produced and must be reviewed and tested before use.
- The starter stores generated projects in process memory; restarting the backend clears them. Use a database/object store for production.
- OAuth tokens are held in the signed server-side session cookie in this starter. For production, prefer a server-side session store and encrypt tokens at rest; keep cookies small.
- Image OCR requires Tesseract installed on the host and `pytesseract` installed. OCR is best-effort.
- GitHub file publishing uses the Git Trees/Commits API to publish files as a single commit. It does not overwrite `.env` or other sensitive files.
- Never publish generated code without reviewing it for security and correctness.
