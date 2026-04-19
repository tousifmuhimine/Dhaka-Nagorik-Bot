# Dhaka Nagorik Bot

Supabase-first civic complaint system for Dhaka with a split architecture:

- `frontend/`: Next.js app (entry UI, Supabase auth flow)
- `backend/`: Django app (business logic, complaint workflow, chatbot, document and storage services)

## Monorepo Structure

```text
Dhaka Nagorik Bot/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
├── backend/
│   ├── complaints/
│   ├── dhaka_web/
│   ├── templates/
│   ├── static/
│   ├── supabase/
│   ├── manage.py
│   └── requirements.txt
└── README.md
```

## Supabase-Only Rules

- Supabase Postgres is required for Django DB.
- Supabase Storage is required for attachments/documents.
- Supabase pgvector is required for vector search.
- SQLite/local storage fallbacks are disabled in backend settings.

## Quick Start

### 1. Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

### 2. Frontend setup

```bash
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Frontend: `http://127.0.0.1:3000`

Backend: `http://127.0.0.1:8000`

## Auth Model

- Login/signup happens through Supabase Auth (`backend/api/auth/*`).
- Backend mirrors Supabase users into relational profile records needed by complaint workflow.
- Next.js establishes a backend session bridge (`/api/auth/session/`) after Supabase login.
- All role dashboards, complaint detail workflow, and chatbot screens now run as native Next.js pages using JSON APIs.

## Required Environment Variables

Set these in `backend/.env`:

- `DATABASE_URL` (Supabase Postgres)
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ENABLE_SUPABASE_STORAGE=true`
- `VECTOR_STORE_BACKEND=supabase`
- `CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000`

Set this in `frontend/.env.local`:

- `NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000`
