# Debatence

Debatence is a debate workspace built with React + Vite and FastAPI + SQLAlchemy.

## Included in this update

- Debate creation with categories, formats, and optional duration.
- Debate lifecycle: open, paused, and completed states (creator controls).
- Debate discovery/search across title, description, and category.
- For/against argument posting, evidence attachments, and optional AI stance analysis.
- Debate voting (up/down; a user can toggle/change their vote).
- Debate bookmarking/save toggles.
- Debate comment threads.
- Role requests and creator approve/reject flow.
- Content reporting and a moderation report queue with resolve/dismiss API.
- Member profile/bio storage and contribution points/leaderboard APIs.
- Debate engagement stats and API health endpoint.
- Existing Render deployment configuration retained.

## Run locally

### Backend
```bash
cd backend
py -m venv .venv
.venv\\Scripts\\Activate.ps1
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL` for the frontend when deploying (the Render blueprint sets it).

## Environment

- `DATABASE_URL`: SQLAlchemy database URL. Render uses the configured PostgreSQL database.
- `CORS_ORIGINS`: comma-separated allowed frontend origins.
- `UPLOAD_DIR`: evidence upload folder (default `uploads`).
- `OPENAI_API_KEY`: optional; without it, AI stance analysis is marked unavailable.
- `OPENAI_MODEL`: optional model override (default `gpt-4.1-mini`).

## Important deployment/security note

This project currently uses client-generated profile IDs and role-request identity values. **It is not production-secure authentication**: a user can spoof a client ID, and moderation endpoints are not protected by authenticated moderator credentials. Do not treat profile IDs or creator IDs as proof of identity. A production launch should add server-side account authentication/authorization, rate limits, malware scanning for uploads, and authenticated moderator/admin access. The moderation, profile, notification, and leaderboard APIs are feature foundations; some are API-only in this version. The notification endpoint currently derives role-request status rather than delivering push/WebSocket notifications.

Database table creation and additive debate/argument migrations run at app startup. For larger production schema evolution, use Alembic migrations.
