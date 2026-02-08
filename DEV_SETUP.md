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
- Apply migrations:
```bash
alembic upgrade head
```
- Create a new migration:
```bash
alembic revision --autogenerate -m "your_message"
```
- Roll back one migration:
```bash
alembic downgrade -1
```

## Run API
```bash
python -m app.main
```

## Run Tests
```bash
JWT_SECRET=test-secret pytest -q
```
