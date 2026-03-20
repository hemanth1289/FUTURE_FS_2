# LeadFlow CRM 🚀

A lightweight Client Lead Management System built with **Flask + SQLite + Tailwind CSS**.

---

## Features

- 📋 **Lead submission form** — name, email, phone, source, message
- 🗄️ **SQLite database** via SQLAlchemy ORM
- 📊 **Admin dashboard** — sortable table, analytics cards
- 🔄 **Status management** — new → contacted → converted (inline dropdown)
- 🗑️ **Delete leads** with confirmation
- 🔍 **Search & filter** by name, email, or status
- 📤 **CSV export** (filtered or full)
- 🔐 **Session-based login** (no external auth library)
- ⚡ **Flash notifications** for all actions
- 📱 **Responsive design** — works on mobile

---

## Quick Start (Local)

```bash
# 1. Clone / download the project
cd mini-crm

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file
cp .env.example .env
# Edit .env to set SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD

# 5. Run the development server
python app.py
```

Visit **http://127.0.0.1:5000** — the database is created automatically on first run.

Default admin credentials (change in `.env`):
- Username: `admin`
- Password: `admin123`

---

## Project Structure

```
mini-crm/
├── app.py                  # All Flask routes and models
├── requirements.txt
├── render.yaml             # Render.com deployment config
├── .env.example            # Environment variable template
├── .gitignore
└── templates/
    ├── base.html           # Shared layout, nav, flash messages
    ├── index.html          # Public lead submission form
    ├── login.html          # Admin login page
    └── dashboard.html      # Admin dashboard
```

---

## Deploy to Render

1. Push your project to a GitHub repository
2. Go to [render.com](https://render.com) → **New Web Service** → connect your repo
3. Render detects `render.yaml` automatically
4. Set your environment variables in the Render dashboard:
   - `SECRET_KEY` — use a long random string
   - `ADMIN_USERNAME` — your chosen username
   - `ADMIN_PASSWORD` — a strong password
5. Click **Deploy** — done!

> **Note:** The `render.yaml` includes a persistent disk for the SQLite database so your data survives redeploys.

---

## Environment Variables

| Variable         | Default         | Description                              |
|-----------------|-----------------|------------------------------------------|
| `SECRET_KEY`    | dev-secret-...  | Flask session secret (use random string) |
| `ADMIN_USERNAME`| `admin`         | Dashboard login username                 |
| `ADMIN_PASSWORD`| `admin123`      | Dashboard login password                 |
| `DATABASE_URL`  | `sqlite:///leads.db` | Database connection string          |

---

## Tech Stack

- **Backend:** Python 3.11+, Flask 3, SQLAlchemy, Gunicorn
- **Frontend:** Jinja2 templates, Tailwind CSS (CDN), DM Sans font
- **Database:** SQLite (dev & small-scale production)
