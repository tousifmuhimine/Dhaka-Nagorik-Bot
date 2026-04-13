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
