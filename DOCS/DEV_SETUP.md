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
For production deployments (Render), configure environment variables in the Render Dashboard (do not commit real secrets).
4. Ensure required variables exist (the app fails fast if missing):
   - `JWT_SECRET` (required; must be non-empty)
   - `DATABASE_URL` (optional; defaults are in `app/config.py`)
   - `JWT_TTL_HOURS` (optional; defaults to `8`)
   - `LOG_LEVEL` (optional; defaults to `WARNING`)
5. Load `.env` into your shell (so `python` and `uvicorn` can read it):
```bash
set -a
source .env
set +a
```

## Database
In early development, schema creation is done automatically from ORM models in development mode.

When `APP_ENV=development`, the API boot process runs `Base.metadata.create_all(bind=engine)` once at startup.
This is skipped in all other environments.

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
