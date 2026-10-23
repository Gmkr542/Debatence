# Debatence — Debate Platform

Debatence is a full-stack debate workspace for creating debate rooms, sharing For/Against arguments, reviewing point validity and correctness, and attaching evidence.

## Technology
- React + Vite frontend
- FastAPI backend
- PostgreSQL with SQLAlchemy
- Render Blueprint deployment (`render.yaml`)
- GitHub for source control and deployment integration

## Requirements
- Git
- Python 3.10+ (Python 3.11 recommended)
- Node.js 20+ and npm
- PostgreSQL (local install or hosted database)
- GitHub account and Render account for deployment

## Run locally
1. Clone the repository and enter its directory.
2. Create a PostgreSQL database named `debatence` (or choose another database).
3. Backend setup (Windows PowerShell):
   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   py -m pip install -r requirements.txt
   $env:DATABASE_URL = "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/debatence"
   py -m uvicorn app.main:app --reload
   ```
   On macOS/Linux, activate with `source .venv/bin/activate` and use `python` instead of `py` if needed.
4. In a second terminal, configure and run the frontend:
   ```bash
   cd frontend
   npm install
   # Optional when the API is not at localhost:8000/api: set VITE_API_URL
   npm run dev
   ```
5. Open the Vite URL shown in the terminal. API docs: `http://localhost:8000/docs`; health check: `http://localhost:8000/api/health`.

The backend defaults to `postgresql+psycopg://postgres:postgres@localhost:5432/debate_manager` if `DATABASE_URL` is not set. Set it to your own local database URL.

## GitHub setup
From the project root:
```bash
git init
git add .
git commit -m "Prepare Debatence for deployment"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```
Create the repository on GitHub first (do not initialize it with a README if you already have this project README). Replace the example remote with your repository URL. Never commit passwords, `.env` files, database credentials, uploaded evidence, or `node_modules`; `.gitignore` excludes common local files.

## Deploy to Render (Blueprint)
1. Push the repository to GitHub.
2. In Render, choose **New + → Blueprint** and connect the GitHub repository containing `render.yaml`.
3. Review and apply the blueprint. It provisions a PostgreSQL database, the FastAPI web service (`debatence-api`), and the React static site (`debatence`).
4. Confirm the frontend `VITE_API_URL` points to the deployed API URL ending in `/api`. Vite reads this at build time; trigger a new frontend deploy after changing it.
5. Update `CORS_ORIGINS` on the API service to the exact deployed frontend origin (for example, `https://debatence.onrender.com`) if Render assigns a different URL. Include comma-separated origins if you use multiple frontend domains.
6. Verify the frontend loads and visit the API `/api/health` endpoint.

### Manual Render setup
- **PostgreSQL:** create a Render database and use its Internal Database URL for the backend `DATABASE_URL` when services share the Render region.
- **Backend web service:** root directory `backend`; build command `pip install -r requirements.txt`; start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`; set `DATABASE_URL` and `CORS_ORIGINS`.
- **Frontend static site:** root directory `frontend`; build command `npm install && npm run build`; publish directory `dist`; set `VITE_API_URL` to `https://YOUR-API.onrender.com/api`.

## Evidence storage note
Evidence uploads are written to the API's local `uploads/` directory. Render web-service filesystems are ephemeral by default, so uploaded evidence can disappear after redeploy/restart. For persistence, attach a Render disk and set `UPLOAD_DIR` to its mount path, or use external object storage. GitHub is source control, not a runtime evidence-storage service.

## Current features
- Create and join debates
- Debate list and room view
- For/Against arguments
- Point status: valid / invalid / needs review
- Correctness: correct / incorrect / unverified
- Evidence attachments (local development storage)

This starter is not production-ready. Add authentication, authorization, database migrations, upload scanning/limits, moderation, and durable object storage before public use.


## Debate role requests (cross-device)

Viewer requests are now stored by the API in the `debate_role_requests` table. The debate initiator can see pending requests on any device and approve or reject them. Approval persists the user's `Debater` role for that debate in `debate_member_roles`; the client reads the role from the API when opening the debate.

The backend currently uses the user/initiator IDs supplied by the client for these checks. This makes the flow persist across devices, but is not a substitute for authenticated accounts and verified authorization. Add account authentication before treating role changes as security-sensitive in production.


## Product updates in this package

This build includes roadmap-oriented improvements:
- Debate discovery through title/description search.
- Debate lifecycle states (open, paused, completed), with initiator controls.
- Backend prevents new argument submissions while a debate is paused or completed.
- Debate activity summary endpoint and UI (counts, participants, recent arguments; not a winner verdict).
- Database health/readiness check.
- Additive database columns for lifecycle, debate format, duration, and timestamps.
- Automatic debate-feed refresh and initiator role-request queue polling.
- Existing AI stance analysis and evidence attachment workflows retained.

### Configuration
Set `VITE_API_URL` for the frontend API root (including `/api`), `DATABASE_URL` for the backend database,
`CORS_ORIGINS` for allowed frontend origins, and `OPENAI_API_KEY` / `OPENAI_MODEL` to enable AI stance analysis.

### Security and feature boundaries
The current app's identity mechanism uses a client-held generated user ID. It is suitable for a prototype,
not production authentication: IDs can be spoofed. Do not expose sensitive/private debates until real
authentication and server-verified ownership are integrated. This build's activity summary is deterministic;
it does not declare a debate winner. WebSocket delivery, robust user accounts, moderation workflows,
email notifications, follower/community features, tournaments, and infrastructure observability remain
separate production work and are not represented as completed here.
