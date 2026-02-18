# Sprint 7 Integration Guide

## Overview
This guide explains how to integrate Sprint 7 Tax CRM features into the existing Binder & Billing CRM codebase.

---

## Files to Copy

### 1. Models (app/models/)
Copy these new model files:
- `tax_crm_sprint7/models/annual_report.py`
- `tax_crm_sprint7/models/tax_deadline.py`
- `tax_crm_sprint7/models/authority_contact.py`

**Update** `app/models/__init__.py`:
```python
from app.models.annual_report import AnnualReport, ReportStage
from app.models.tax_deadline import TaxDeadline, DeadlineType, UrgencyLevel
from app.models.authority_contact import AuthorityContact, ContactType

# Add to __all__
__all__ = [
    # ... existing exports ...
    "AnnualReport",
    "ReportStage",
    "TaxDeadline",
    "DeadlineType",
    "UrgencyLevel",
    "AuthorityContact",
    "ContactType",
]
```

---

### 2. Repositories (app/repositories/)
Copy these repository files:
- `tax_crm_sprint7/repositories/annual_report_repository.py`
- `tax_crm_sprint7/repositories/tax_deadline_repository.py`
- `tax_crm_sprint7/repositories/authority_contact_repository.py`

**Update** `app/repositories/__init__.py`:
```python
from app.repositories.annual_report_repository import AnnualReportRepository
from app.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.repositories.authority_contact_repository import AuthorityContactRepository

# Add to __all__
__all__ = [
    # ... existing exports ...
    "AnnualReportRepository",
    "TaxDeadlineRepository",
    "AuthorityContactRepository",
]
```

---

### 3. Services (app/services/)
Copy these service files:
- `tax_crm_sprint7/services/annual_report_service.py`
- `tax_crm_sprint7/services/tax_deadline_service.py`
- `tax_crm_sprint7/services/authority_contact_service.py`
- `tax_crm_sprint7/services/dashboard_tax_service.py`

**Update** `app/services/__init__.py`:
```python
# Add lazy imports for new services
def __getattr__(name: str) -> Any:
    # ... existing imports ...
    
    if name == "AnnualReportService":
        from app.annual_reports.services.annual_report_service import AnnualReportService
        return AnnualReportService
    
    if name == "TaxDeadlineService":
        from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService
        return TaxDeadlineService
    
    if name == "AuthorityContactService":
        from app.authority_contact.services.authority_contact_service import AuthorityContactService
        return AuthorityContactService
    
    if name == "DashboardTaxService":
        from app.dashboard.services.dashboard_tax_service import DashboardTaxService
        return DashboardTaxService
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

---

### 4. Schemas (app/schemas/)
Copy these schema files:
- `tax_crm_sprint7/schemas/annual_report.py`
- `tax_crm_sprint7/schemas/tax_deadline.py`
- `tax_crm_sprint7/schemas/authority_contact.py`
- `tax_crm_sprint7/schemas/dashboard_tax.py`

**Update** `app/schemas/__init__.py`:
```python
from app.schemas.annual_report import (
    AnnualReportCreateRequest,
    AnnualReportResponse,
    AnnualReportListResponse,
    AnnualReportTransitionRequest,
    AnnualReportSubmitRequest,
    KanbanResponse,
)
from app.schemas.tax_deadline import (
    TaxDeadlineCreateRequest,
    TaxDeadlineResponse,
    TaxDeadlineListResponse,
    DashboardDeadlinesResponse,
)
from app.schemas.authority_contact import (
    AuthorityContactCreateRequest,
    AuthorityContactResponse,
    AuthorityContactListResponse,
)
from app.schemas.dashboard_tax import TaxSubmissionWidgetResponse

# Add to __all__
```

---

### 5. API Routes (app/api/)
Copy these API files:
- `tax_crm_sprint7/api/annual_reports.py`
- `tax_crm_sprint7/api/tax_deadlines.py`
- `tax_crm_sprint7/api/authority_contacts.py`
- `tax_crm_sprint7/api/dashboard_tax.py`

**Update** `app/api/__init__.py`:
```python
from app.api import (
    # ... existing imports ...
    annual_reports,
    tax_deadlines,
    authority_contacts,
    dashboard_tax,
)

__all__ = [
    # ... existing exports ...
    "annual_reports",
    "tax_deadlines",
    "authority_contacts",
    "dashboard_tax",
]
```

---

### 6. Main Application (app/main.py)
Add the new routers:

```python
from app.api import (
    # ... existing imports ...
    annual_reports,
    tax_deadlines,
    authority_contacts,
    dashboard_tax,
)

# Register routes (add after existing routes)
app.include_router(annual_reports.router, prefix="/api/v1")
app.include_router(tax_deadlines.router, prefix="/api/v1")
app.include_router(authority_contacts.router, prefix="/api/v1")
app.include_router(dashboard_tax.router, prefix="/api/v1")
```

---

### 7. Tests (tests/)
Copy test files to appropriate locations:
- `tax_crm_sprint7/tests/test_annual_report_service.py` → `tests/services/`
- `tax_crm_sprint7/tests/test_tax_deadline_service.py` → `tests/services/`

---

## Database Migration

### Option 1: Development (Schema Recreation)
Since APP_ENV=development recreates schema from ORM models:
```bash
# Stop the server
# Delete database file
rm binder_crm.db

# Restart server (schema will be recreated)
APP_ENV=development python -m app.main
```

### Option 2: Production (Manual Migration)
For production environments, create migration SQL:

```sql
-- Create annual_reports table
CREATE TABLE annual_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    tax_year INTEGER NOT NULL,
    stage VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'not_started',
    created_at DATETIME NOT NULL,
    due_date DATE,
    submitted_at DATETIME,
    form_type VARCHAR,
    notes TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE INDEX idx_annual_report_client_year ON annual_reports(client_id, tax_year);
CREATE UNIQUE INDEX idx_annual_report_client_year_unique ON annual_reports(client_id, tax_year);
CREATE INDEX idx_annual_report_stage ON annual_reports(stage);

-- Create tax_deadlines table
CREATE TABLE tax_deadlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    deadline_type VARCHAR NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    payment_amount DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'ILS',
    description TEXT,
    created_at DATETIME NOT NULL,
    completed_at DATETIME,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE INDEX idx_tax_deadline_client ON tax_deadlines(client_id);
CREATE INDEX idx_tax_deadline_due_date ON tax_deadlines(due_date);
CREATE INDEX idx_tax_deadline_status ON tax_deadlines(status);

-- Create authority_contacts table
CREATE TABLE authority_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    contact_type VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    office VARCHAR,
    phone VARCHAR,
    email VARCHAR,
    notes TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE INDEX idx_authority_contact_client ON authority_contacts(client_id);
CREATE INDEX idx_authority_contact_type ON authority_contacts(contact_type);

-- Add new fields to clients (if not exists)
ALTER TABLE clients ADD COLUMN tax_id VARCHAR;
ALTER TABLE clients ADD COLUMN spouse_name VARCHAR;
ALTER TABLE clients ADD COLUMN spouse_id_number VARCHAR;

-- Add new fields to permanent_documents (if not exists)
ALTER TABLE permanent_documents ADD COLUMN tax_year INTEGER;
ALTER TABLE permanent_documents ADD COLUMN form_type VARCHAR;
```

---

## Testing the Integration

### 1. Run Unit Tests
```bash
JWT_SECRET=test-secret pytest tests/services/test_annual_report_service.py -v
JWT_SECRET=test-secret pytest tests/services/test_tax_deadline_service.py -v
```

### 2. Start the Server
```bash
APP_ENV=development ENV_FILE=.env.development python -m app.main
```

### 3. Test API Endpoints

#### Create Annual Report
```bash
curl -X POST http://localhost:8000/api/v1/annual-reports \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "tax_year": 2025,
    "form_type": "106",
    "due_date": "2026-04-30"
  }'
```

#### Create Tax Deadline
```bash
curl -X POST http://localhost:8000/api/v1/tax-deadlines \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "deadline_type": "vat",
    "due_date": "2026-02-25",
    "payment_amount": 5000.00
  }'
```

#### Get Dashboard Tax Widget
```bash
curl http://localhost:8000/api/v1/dashboard/tax-submissions \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Verification Checklist

- [ ] All 3 new models imported in `app/models/__init__.py`
- [ ] All 3 new repositories imported in `app/repositories/__init__.py`
- [ ] All 4 new services imported in `app/services/__init__.py`
- [ ] All 4 new API routers registered in `app/main.py`
- [ ] Database schema created (dev) or migrated (prod)
- [ ] Unit tests pass
- [ ] API endpoints respond with 200/201
- [ ] OpenAPI docs show new endpoints at `/docs`
- [ ] No regressions in existing Sprint 1-6 tests

---

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError`:
1. Verify file paths match exactly
2. Check `__init__.py` files are present in all directories
3. Restart Python server to reload modules

### Database Errors
If you see `no such table`:
1. Delete database file in development
2. Restart server to recreate schema
3. Or run manual migration SQL

### Authorization Errors
If endpoints return 403:
1. Verify user has ADVISOR or SECRETARY role
2. Check JWT token is valid and not expired
3. Confirm endpoint has correct `require_role` decorator

---

## Next Steps

After successful integration:
1. Update `API_CONTRACT.md` with new endpoints
2. Create `SPRINT_7_FREEZE_DECLARATION.md`
3. Update frontend to consume new APIs
4. Plan Sprint 8 (Capital Statements & Time Tracking)
