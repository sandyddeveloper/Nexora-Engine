# Nexora Engine

Nexora Engine is a scalable Django starter project with a modular structure for accounts, organizations, shared utilities, and health monitoring.

## Tech stack

- Python 3.10+
- Django
- Django REST Framework
- PostgreSQL
- Redis
- Docker Compose
- Black, Ruff, isort, and pre-commit

## Project structure

- apps/ for feature modules
- core/ for shared utilities and helpers
- config/ for Django settings and routing
- docs/, scripts/, tests/, docker/, logs/, static/, and media/ for project assets

## Requirements

- Python 3.10+
- PostgreSQL
- Redis
- Docker (optional, for containerized development)

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Docker setup

```bash
docker compose up --build
docker compose exec web python manage.py migrate
```

## Environment variables

Create a .env file with values such as:

```env
DEBUG=True
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=nexora-dev
DB_USER=postgres
DB_PASSWORD=12102006
DB_HOST=postgres
DB_PORT=5432
REDIS_URL=redis://redis:6379/0
TIME_ZONE=Asia/Kolkata
LANGUAGE_CODE=en-us
```

## Development guidelines

- Run formatting and lint checks before committing:

```bash
black .
ruff check .
isort .
```

- Pre-commit hooks are installed and will run automatically on commit.

- Follow Conventional Commits for all changes, for example: `feat: add authentication`, `fix: resolve login bug`, or `chore: update dependencies`.
