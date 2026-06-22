# Book Shop

> 🇬🇧 English | [🇷🇺 Русский](README.ru.md)

A web application for an online bookstore built with Django. Browse the catalog, register an account, and place orders.

## Features

- Book catalog with cover images, descriptions, and stock status
- Book detail pages
- User registration and login
- Order placement with stock validation
- Personal order history
- Pagination for the catalog
- Responsive UI built with Bootstrap 5
- Django admin panel for content management

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Django 5 |
| Database | SQLite (default) |
| Frontend | Bootstrap 5.3 |
| Image handling | Pillow |

## Requirements

- Python 3.10+
- pip

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd exam_app

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# (Optional) Create an admin account
python manage.py createsuperuser

# Run the development server
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`.

## Environment Variables

For production deployments, set these environment variables instead of using defaults:

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | insecure dev key |
| `DEBUG` | Enable debug mode (`True`/`False`) | `True` |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | _(empty)_ |

## Running Tests

```bash
python manage.py test
```

## Project Structure

```
exam_app/
├── exam_app/          # Django project settings and root URL conf
├── main/              # Application: models, views, forms, templates
│   ├── migrations/    # Database migrations
│   ├── templates/     # HTML templates
│   ├── models.py      # Book and Order models
│   ├── views.py       # View functions
│   ├── forms.py       # Form classes
│   ├── admin.py       # Admin configuration
│   └── tests.py       # Test suite
├── media/             # User-uploaded files (book covers)
├── manage.py
└── requirements.txt
```

## License

[MIT](LICENSE)
