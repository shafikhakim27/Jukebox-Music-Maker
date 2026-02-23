# Jukebox Music Maker (Personal Use Only)

A full-stack, self-hosted jukebox web app where one device is the **Host** (audio playback device) and other devices act as **controllers** to browse tracks and manage a shared queue.

## ⚠️ Personal-Use & Copyright Disclaimer

- This software is intended **only for private, personal, self-hosted use**.
- Do **not** use it as a public streaming platform or to redistribute copyrighted material.
- You are responsible for ensuring all uploaded audio files are legally owned/licensed by you.
- The project authors/contributors do not grant rights to copyrighted music.

## Stack

- **Frontend:** Next.js + TypeScript + Tailwind CSS
- **Backend:** FastAPI (Python)
- **Realtime:** Native WebSockets
- **Database:** PostgreSQL (Docker default), SQLite fallback for local dev
- **Orchestration:** Docker Compose

## Features

- Admin-only upload and delete for mp3/wav files
- Searchable music library with basic metadata
- Shared queue (add/remove/reorder)
- Host playback state controls (play/pause/seek/volume/current track)
- Roles: `admin`, `host`, `user`, `guest`
- Simple auth via basic login/shared passwords
- Queue rate limiting to reduce spam

## Project Structure

- `frontend/` — Next.js app (controllers + host web UI)
- `backend/` — FastAPI API + WebSocket + media serving
- `docker-compose.yml` — app + database stack

## Quick Start (Docker)

1. Copy env templates:
   - `cp backend/.env.example backend/.env`
   - `cp frontend/.env.example frontend/.env`
2. Start:
   - `docker compose up --build`
3. Open:
   - Frontend: `http://localhost:3000`
   - Backend docs: `http://localhost:8000/docs`

## Local Dev (Without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Host Mode Explained

- Log in on one device with host/admin credentials.
- That device uses the HTML5 `<audio>` player and controls playback.
- Other devices can queue songs and manage tracks depending on role.
- Playback/queue changes are broadcast through WebSockets to all connected clients.

## Default Credentials / Roles

Configured in `backend/.env`:

- `ADMIN_USERNAME` + `ADMIN_PASSWORD` → `admin`
- Username `host` + `HOST_PASSWORD` → `host`
- Any username + `SHARED_USER_PASSWORD` → `user`
- Unauthenticated requests use `guest`

## Scripts

### Frontend

- `npm run dev`
- `npm run build`
- `npm run start`
- `npm run lint`
- `npm run typecheck`

### Backend

- `uvicorn app.main:app --reload`
- `pytest backend/tests`

## Dependabot

Dependabot is enabled via `.github/dependabot.yml` for npm, pip, Docker, and GitHub Actions.
