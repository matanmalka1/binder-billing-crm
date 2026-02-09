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
4. Set `JWT_SECRET` in `.env` (required in all environments).

## Database
This repo uses SQLAlchemy ORM models as the source of truth for the core schema.

For a new local SQLite database, initialize tables from ORM metadata:
```bash
python -c "from app.database import Base, engine; import app.models; Base.metadata.create_all(bind=engine)"
```

Sprints 3–4 introduced Alembic migrations for new tables only (per the frozen sprint specifications).
If you have an existing database with the core tables already present, you can apply migrations up to the current head:
```bash
alembic upgrade head
```

## Run API
```bash
python -m app.main
```

## Run Tests
```bash
JWT_SECRET=test-secret pytest -q
```
