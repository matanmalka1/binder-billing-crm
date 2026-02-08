# Binder & Billing CRM - Sprint 1

Backend implementation for Binder & Billing CRM system.

## Sprint 1 Complete

**Implemented:**
- ✅ Alembic database migrations
- ✅ User authentication with bcrypt and JWT
- ✅ Client management (CRUD)
- ✅ Binder intake/return lifecycle
- ✅ 90-day overdue calculation
- ✅ Dashboard summary counters
- ✅ Minimal test suite (auth, clients, binders)

**NOT Implemented (Future Sprints):**
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

### 3. Run Database Migrations

```bash
alembic upgrade head
```

### 4. Create Seed Users

```python
from app.database import SessionLocal
from app.repositories import UserRepository
from app.services import AuthService

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

API: `http://localhost:8000`  
Docs: `http://localhost:8000/docs`

---

## Run Tests

```bash
pytest
```

---

## Database Migrations

### Create New Migration
```bash
alembic revision --autogenerate -m "description"
```

### Apply Migrations
```bash
alembic upgrade head
```

### Rollback
```bash
alembic downgrade -1
```

---

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login and get JWT token

### Clients
- `POST /api/v1/clients` - Create client
- `GET /api/v1/clients` - List clients
- `GET /api/v1/clients/{id}` - Get client
- `PATCH /api/v1/clients/{id}` - Update client

### Binders
- `POST /api/v1/binders/receive` - Receive binder
- `POST /api/v1/binders/{id}/return` - Return binder
- `GET /api/v1/binders` - List active binders
- `GET /api/v1/binders/{id}` - Get binder

### Dashboard
- `GET /api/v1/dashboard/summary` - Get summary counters

---

## Architecture

```
app/
├── models/          # SQLAlchemy ORM models
├── repositories/    # Data access layer
├── services/        # Business logic
├── api/             # FastAPI routes
├── schemas/         # Pydantic request/response models
├── middleware/      # HTTP middleware
├── config.py        # Configuration
└── database.py      # DB session management

alembic/
└── versions/        # Database migrations

tests/
├── conftest.py      # Test fixtures
├── test_auth.py
├── test_clients.py
└── test_binders.py
```

---

## Key Business Rules

1. **90-Day Rule**: `expected_return_at = received_at + 90 days`
2. **No Hard Deletes**: Records soft-deleted via status
3. **Return Validation**: `pickup_person_name` mandatory
4. **Audit Trail**: Every status change logged
5. **Warnings Don't Block**: Intake never blocked

---

## Security

- Passwords hashed with bcrypt
- JWT tokens with proper claims (sub, iat, exp, role)
- Role-based access control
- Active user validation
- Secure session management

---

## Sprint 2 Planning

Next sprint priorities:
- Billing module (charges, invoices)
- Background jobs for overdue marking
- Notification engine foundation
- Enhanced test coverage
- Performance monitoring