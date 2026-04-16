# Dhaka Civic Complaints System

A professional Django web application for managing civic complaints in Dhaka. Citizens can file complaints, track status, and authorities can manage and respond to complaints.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Virtual environment activated (`.venv/`)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Apply database migrations
python manage.py migrate

# Create test users (optional)
python setup_users.py

# Start development server
python manage.py runserver
```

Visit: **http://127.0.0.1:8000/**

### Test Accounts

| Email | Password | Role |
|-------|----------|------|
| `admin@dhaka.gov` | `Admin@1234` | Admin |
| `citizen@example.com` | `Citizen@1234` | Citizen |
| `authority@dhaka.gov` | `Authority@1234` | Authority |

## 📁 Project Structure

```
Dhaka Nagorik Bot/
├── manage.py                 # Django management script
├── db.sqlite3               # SQLite database
├── requirements.txt         # Python dependencies
│
├── dhaka_web/               # Django project settings
│   ├── settings.py          # Configuration
│   ├── urls.py              # URL routing
│   └── wsgi.py              # Production WSGI
│
├── complaints/              # Main Django app
│   ├── models.py            # Database models
│   ├── views.py             # Business logic
│   ├── forms.py             # Form validation
│   ├── urls.py              # App URLs
│   ├── admin.py             # Admin interface
│   └── migrations/          # Database history
│
├── templates/               # HTML templates (TailwindCSS)
│   └── complaints/
│       ├── base.html
│       ├── login.html
│       ├── signup.html
│       ├── citizen_dashboard.html
│       ├── authority_dashboard.html
│       ├── admin_dashboard.html
│       └── complaint_detail.html
│
└── static/                  # CSS, JavaScript, images
```

## 🔐 Features

### Citizen
- File new complaints
- Track complaint status
- View history
- Communicate with authorities

### Authority
- Thana-specific dashboard
- Respond to complaints
- Update status
- Filter by category/status

### Admin
- System-wide overview
- Search and filter
- User management
- Statistics

## 🛠 Development

```bash
# Run server
python manage.py runserver

# Create admin user
python manage.py createsuperuser

# Create/apply migrations
python manage.py makemigrations
python manage.py migrate

# Access admin
# http://127.0.0.1:8000/admin/
```

## 📦 Technologies

- **Backend**: Django 6.0.4 (Python)
- **Frontend**: Django Templates + TailwindCSS
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Auth**: Django built-in authentication

## 🚢 Production

Set `DEBUG = False` in settings and deploy with Gunicorn + Nginx.

See COMMANDS.md for more commands.

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

## Supabase vector storage

The chatbot can use Supabase pgvector instead of local Chroma for policy retrieval and complaint similarity.

1. Run `supabase/schema.sql` in the Supabase SQL editor.
2. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env`.
3. Change `VECTOR_STORE_BACKEND=supabase`.
4. Pre-index your policies with `python manage.py index_policies`.

For deployment, keep `ENABLE_AUTO_POLICY_INDEXING=false` so the app reads from prebuilt vectors instead of writing them during request handling.

If `VECTOR_STORE_BACKEND=auto`, the app will use Supabase automatically when those credentials are present and fall back to local Chroma otherwise.

## Supabase Postgres for Django

The main Django database can also run on Supabase Postgres.

1. Replace the placeholder DB password in `.env`.
2. Run migrations with `python manage.py migrate`.
3. Create users or seed data as needed.

## Supabase Storage

Attachments and generated complaint documents can be stored in Supabase Storage instead of local folders.

1. Set `ENABLE_SUPABASE_STORAGE=true` in `.env`.
2. Choose bucket names with `SUPABASE_MEDIA_BUCKET` and `SUPABASE_DOCUMENT_BUCKET`.
3. Start using the app normally for new uploads/documents.
4. If you already have local files, run `python manage.py sync_supabase_storage`.
