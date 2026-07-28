# Nexora Engine

A scalable Django starter project with a modular app structure for accounts, organizations, common utilities, and health checks.

## Project structure

- apps/ for feature modules
- core/ for shared utilities and helpers
- config/ for Django settings and routing
- docs/, scripts/, tests/, docker/, logs/, static/, media/ for project assets

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
