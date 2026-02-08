# Binder & Billing CRM - Sprint 1

Backend implementation for Binder & Billing CRM system.

## Sprint 1 Scope

**Implemented:**
- User authentication (JWT)
- Client management (CRUD)
- Binder intake/return lifecycle
- 90-day overdue calculation
- Dashboard summary counters
- ORM-based database schema creation

**NOT Implemented (Future Sprints):**
- Database migrations (Alembic/Flyway)
- Billing execution (charges, invoices)
- Notification sending (WhatsApp/SMS/Email)
- Background jobs (overdue marking)
- File upload for permanent documents
- Advanced reporting

---

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Initialize Database

The database schema is created automatically from ORM models on first run.

```bash
python -m app.main
```

### 4. Create Seed Users (Optional)

Use Python REPL to create initial users:

```python
from app.database import SessionLocal, init_db
from app.repositories import UserRepository
from app.services import AuthService

init_db()
db = SessionLocal()
user_repo = UserRepository(db)

# Create advisor
user_repo.create(
    full_name="Tax Advisor",
    email="advisor@office.local",
    password_hash=AuthService.hash_password("password123"),
    role="advisor"
)

# Create secretary
user_repo.create(
    full_name="Office Secretary",
    email="secretary@office.local",
    password_hash=AuthService.hash_password("password123"),
    role="secretary"
)

db.close()
```

---

## Run Application

```bash
python -m app.main
```

API will be available at: `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

---

## API Endpoints (Sprint 1)

### Authentication
- `POST /api/v1/auth/login` - Login and get JWT token

### Clients
- `POST /api/v1/clients` - Create client
- `GET /api/v1/clients` - List clients
- `GET /api/v1/clients/{id}` - Get client
- `PATCH /api/v1/clients/{id}` - Update client

### Binders
- `POST /api/v1/binders/receive` - Receive binder (intake)
- `POST /api/v1/binders/{id}/return` - Return binder
- `GET /api/v1/binders` - List active binders
- `GET /api/v1/binders/{id}` - Get binder

### Dashboard
- `GET /api/v1/dashboard/summary` - Get summary counters

---

## Architecture

```
app/
├── models/          # ORM models (SQLAlchemy)
├── repositories/    # Data access layer
├── services/        # Business logic
├── api/             # HTTP endpoints (FastAPI)
├── schemas/         # Request/Response models (Pydantic)
├── config.py        # Configuration
└── database.py      # DB session management
```

---

## Key Business Rules

1. **90-Day Rule**: `expected_return_at = received_at + 90 days`
2. **No Hard Deletes**: Records are soft-deleted via status changes
3. **Return Validation**: `pickup_person_name` is mandatory
4. **Audit Trail**: Every binder status change is logged
5. **Intake Never Blocked**: Warnings don't prevent binder intake

---

## Database Schema

Schema is created directly from ORM models. No migration files exist.

Tables (Sprint 1):
- `users`
- `clients`
- `binders`
- `binder_status_logs`

All IDs are integer auto-increment (1, 2, 3, ...).

---

## Testing

Tests are planned but not implemented in Sprint 1.

Future test structure:
```
tests/
├── test_repositories/
├── test_services/
└── test_api/
```

---

## Phase 2 Features (Out of Scope)

- Charges and invoices
- External invoice provider integration
- Notification engine (WhatsApp/SMS/Email)
- Background jobs
- Permanent documents management
- Advanced reporting and analytics

---

## Development Notes

- **Python 3.11 - 3.14** (3.14 requires SQLAlchemy 2.0.36+)
- FastAPI 0.115+
- Pydantic 2.10+
- SQLAlchemy 2.0.36+
- SQLite (local), PostgreSQL (production recommended)
- JWT authentication
- No frontend included

### Python 3.14 Users
If using Python 3.14, ensure SQLAlchemy is 2.0.36 or later:
```bash
pip install 'sqlalchemy>=2.0.36'
```# binder-billing-crm
