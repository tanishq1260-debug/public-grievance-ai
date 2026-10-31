# GrievanceAI — Public Grievance AI Assistant

A hackathon MVP built with FastAPI, SQLite, Jinja templates, HTML/CSS/JavaScript.

## Features
- Citizen complaint submission with optional file attachment
- Ticket ID generation and complaint tracking
- Rule-based NLP classification, department recommendation, priority suggestion, and short summary
- Admin dashboard with search, status filters, staff notes, and status updates
- Duplicate-ready API/data structure; analytics endpoints
- REST endpoints: `/api/complaints`, `/api/analytics`, `/health`
- Responsive layout

## Quick start

Python 3.10+ recommended.

```bash
# Windows PowerShell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload
```

Then open http://127.0.0.1:8000

## Demo accounts
This MVP does not yet implement a login screen. These accounts are seeded as sample data for the future authentication flow:
- Citizen: `citizen@demo.local` / `citizen123`
- Admin: `admin@demo.local` / `admin123`

**Do not use these credentials or this app as-is in production.** Add proper password hashing, authentication, authorization, CSRF protection, rate limiting, malware scanning, secure file storage, and privacy controls before public deployment.

## AI behavior
The current `classify()` function uses transparent keyword rules. It is a working local prototype, not a trained ML model or LLM. Review AI suggestions before acting on a complaint. You can replace it with a model or LLM API in `app.py` while retaining the response shape.

## Database
SQLite database `grievances.db` is created automatically on first run. Tables: `complaints`, `users`.

## API
- `GET /health`
- `GET /api/complaints`
- `GET /api/analytics`

## Hackathon submission checklist
- Deploy the app to a host that supports Python/FastAPI
- Push source to GitHub (do not commit secrets or real citizen data)
- Record a demo video with fictional data
- Add team details, architecture/ER diagrams, and a project PPT
