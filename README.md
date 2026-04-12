# Dhaka Nagorik Bot

Dhaka Nagorik Bot is a full-stack AI civic complaint automation scaffold for Dhaka city operations. It combines FastAPI, Flet, Groq-powered extraction, PDF-based policy retrieval, lifecycle timestamp tracking, document generation, and dashboard analytics.

## What is included

- Multi-role flow for citizen, authority, and admin
- FastAPI endpoints for complaint lifecycle updates
- AI complaint extraction with Bangla and English support
- RAG policy review from the project PDFs `DNCC.pdf` and `dscc.pdf`
- Explicit lifecycle timestamps plus delayed-complaint tracking
- Generated PDF and DOCX submission documents
- Authority and admin dashboard building blocks
- Local JSON demo storage plus Supabase-ready REST integration

## Project Structure

```text
app/
  api/
  core/
  db/
  models/
  schemas/
  services/
  ui/
docs/
supabase/
main.py
flet_app.py
requirements.txt
```

## Key API Functions

- `create_complaint()`
- `acknowledge_complaint()`
- `mark_in_progress()`
- `mark_done()`
- `confirm_resolution()`

These are implemented inside `ComplaintService` and exposed through FastAPI routes.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
python flet_app.py
```

## Headers for demo mode

The current scaffold uses request headers to emulate authenticated roles while Supabase JWT validation is being integrated:

```text
X-User-Id: citizen-001
X-User-Role: citizen
X-User-Thana: Dhanmondi
```

## Supabase schema

See `supabase/schema.sql` for tables, status handling, and timestamp columns.
