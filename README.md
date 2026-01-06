# Surplus Med

A web application for managing surplus medical supply donations. Built to help NGOs and healthcare departments review and approve supply submissions with proper documentation and audit trails.

## What it does

Medical facilities often have excess supplies they want to donate, but there's no good way to verify if items are safe to redistribute. This system helps organizations:

- Accept supply submissions with photos and details
- Check eligibility (expiry dates, packaging condition, etc.)
- Make accept/reject decisions with proper justification
- Keep permanent records of all decisions
- Export audit reports when needed

## Tech stack

- Django 4.1
- Python 3.x
- SQLite (dev) / PostgreSQL (production)
- Custom CSS (no frameworks)

## Setup

1. Clone the repo
2. Install dependencies:
```bash
pip install django pillow reportlab
```

3. Run migrations:
```bash
cd sur-med/surmed
python manage.py migrate
python manage.py seed_data
```

4. Create admin user:
```bash
python manage.py createsuperuser
```

5. Start server:
```bash
python manage.py runserver
```

6. Visit http://127.0.0.1:8000/decision/

## Features

- Supply submission with evidence upload
- Automated eligibility checks based on configurable rules
- Multi-tier approval workflow
- Audit log with CSV and PDF export
- Admin panel for managing rules and reason codes

## Default credentials

After running seed_data:
- Username: admin
- Password: admin123

Change this immediately in production.

## Database

Currently using SQLite for development. For production, switch to PostgreSQL in settings.py.

## Project structure

```
sur-med/surmed/
├── decision_system/     # Main app
├── base/               # Legacy donor/NGO system
├── templates/          # HTML templates
└── media/              # Uploaded evidence files
```

## Notes

- All decisions are immutable once created
- File uploads go to media/evidence/
- Reason codes and rules can be managed in admin panel
- Export requires reportlab library for PDF generation

## License

MIT
