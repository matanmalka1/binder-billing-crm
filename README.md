# Binder Billing CRM

FastAPI + SQLAlchemy backend for managing client records and physical binder lifecycle in a tax office workflow.

## Overview
- Authentication with JWT bearer tokens
- Client management endpoints
- Binder intake/return lifecycle with status logs
- Dashboard summary counters
- Alembic-managed schema migrations

## Tech Stack
- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- Pytest

## Local Run (Quick Start)
```bash
cp .env.example .env
pip install -r requirements.txt
alembic upgrade head
python -m app.main
```

- API base URL: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

## Documentation
- `DEV_SETUP.md` for environment setup, migrations, and test commands
- `API_CONTRACT.md` for current API behavior and endpoint contracts
