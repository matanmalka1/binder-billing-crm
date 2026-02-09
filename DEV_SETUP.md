# Developer Setup

## Prerequisites
- Python 3.14+
- `pip`

## Environment
1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Create env file:
```bash
cp .env.example .env
```
4. Ensure required variables exist (the app fails fast if missing):
   - `JWT_SECRET` (required; must be non-empty)
   - `DATABASE_URL` (optional; defaults are in `app/config.py`)
   - `JWT_TTL_HOURS` (optional; defaults to `8`)
   - `LOG_LEVEL` (optional; defaults to `INFO`)
5. Load `.env` into your shell (so `python`, `alembic`, and `uvicorn` can read it):
```bash
set -a
source .env
set +a
```

## Database
This repo uses SQLAlchemy ORM models as the source of truth for the core schema.

For a new local SQLite database, initialize the core tables from ORM metadata:
```bash
python -c "from app.database import Base, engine; import app.models; Base.metadata.create_all(bind=engine)"
```

Sprints 3–4 introduced Alembic migrations for additional tables (per the frozen sprint specifications).
Apply migrations up to the current head to create the billing + notifications/documents tables:
```bash
alembic upgrade head
```

## Run API
```bash
python -m app.main
```

Useful endpoints:
- OpenAPI docs: `http://localhost:8000/docs`
- Health: `GET http://localhost:8000/health`
- Info: `GET http://localhost:8000/info`

## Run Tests
```bash
JWT_SECRET=test-secret pytest -q
```
