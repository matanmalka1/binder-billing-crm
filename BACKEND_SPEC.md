# Backend Specification: 6 New API Endpoints
## Binder & Billing CRM — Post Sprint 6 Extension

This document specifies every new API endpoint required by the frontend
feature set built in the Sprint 7 frontend pass. All rules from
`PROJECT_RULES.md` apply in full. This document does not relax any of
them.

---

## 0. Context

The frontend calls six areas that have no backend implementation yet:

| # | Feature | Prefix |
|---|---------|--------|
| 1 | Tax Profile | `GET/PATCH /clients/{id}/tax-profile` |
| 2 | Correspondence Log | `GET/POST /clients/{id}/correspondence` |
| 3 | Annual Report Detail | `GET/PATCH /annual-reports/{id}/details` |
| 4 | Advance Payments | `GET/PATCH /advance-payments` |
| 5 | Authority Contacts | already implemented ✅ |
| 6 | Dashboard widgets | already served by existing endpoints ✅ |

Features 5 and 6 are fully implemented. This document covers 1–4 only.

---

## 1. Engineering Rules (from PROJECT_RULES.md)

Non-negotiable — do not deviate:

- **150 lines max** per Python file.
- **No raw SQL**. ORM only.
- Strict layering: **API → Service → Repository → ORM**.
- **No business logic** in API routers.
- All new background jobs must be idempotent (none required here).
- Health endpoint stays deterministic and safe.
- **Derived state is never persisted** (SLA, WorkState, signals).
- Authorization enforced at both endpoint level and service/action level.

---

## 2. General Conventions

- All new routers mount under `/api/v1` (matching `app/main.py`).
- All new routers require `Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))` unless noted.
- Response schemas use `model_config = {"from_attributes": True}`.
- Nullable fields use `Optional[X] = None`.
- Dates use `datetime.date`; timestamps use `datetime.datetime` (naive UTC via `utcnow()`).
- New ORM models are auto-created by `Base.metadata.create_all` in `APP_ENV=development`. No migration files needed now.
- Register each new router in `app/api/__init__.py` and `app/main.py` following the existing pattern exactly.

---

## 3. Feature 1 — Tax Profile

### 3.1 Purpose

Store per-client tax metadata that does not belong on the core `Client`
model: VAT type, business classification, the month the client's tax year
starts, and the name of any external accountant.

### 3.2 ORM Model — `app/models/client_tax_profile.py`

```
Table: client_tax_profiles
Columns:
  id           INTEGER  PK autoincrement
  client_id    INTEGER  FK → clients.id  NOT NULL  UNIQUE  INDEX
  vat_type     Enum("monthly","bimonthly","exempt")  nullable
  business_type  String  nullable
  tax_year_start  Integer  nullable   -- e.g. 1 = January, 4 = April
  accountant_name  String  nullable
  created_at   DateTime  default=utcnow  NOT NULL
  updated_at   DateTime  nullable
```

Add `ClientTaxProfile` and `VatType` to `app/models/__init__.py`.

### 3.3 Repository — `app/repositories/client_tax_profile_repository.py`

Methods:

```
get_by_client_id(client_id: int) -> Optional[ClientTaxProfile]
upsert(client_id: int, **fields) -> ClientTaxProfile
    # Create if not exists, update otherwise. Set updated_at = utcnow().
```

### 3.4 Service — `app/services/client_tax_profile_service.py`

```
get_profile(client_id: int) -> Optional[ClientTaxProfile]
    # Returns None (not an error) if no profile row exists yet.

update_profile(client_id: int, **fields) -> ClientTaxProfile
    # Validates client exists. Calls repo.upsert().
    # Raises ValueError if client not found.
```

### 3.5 Schemas — `app/schemas/client_tax_profile.py`

```python
class TaxProfileResponse(BaseModel):
    client_id: int
    vat_type: Optional[str] = None          # "monthly" | "bimonthly" | "exempt"
    business_type: Optional[str] = None
    tax_year_start: Optional[int] = None
    accountant_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class TaxProfileUpdateRequest(BaseModel):
    vat_type: Optional[str] = None
    business_type: Optional[str] = None
    tax_year_start: Optional[int] = None
    accountant_name: Optional[str] = None
```

When `GET` finds no profile row, return a `TaxProfileResponse` with all
optional fields `None` and `client_id` set (do not return 404).

### 3.6 API Router — `app/api/client_tax_profile.py`

```
prefix = /clients
tags   = ["client-tax-profile"]
auth   = require_role(ADVISOR, SECRETARY)

GET  /clients/{client_id}/tax-profile
     → TaxProfileResponse
     404 if client does not exist.

PATCH /clients/{client_id}/tax-profile
     body: TaxProfileUpdateRequest
     → TaxProfileResponse
     400 if vat_type value is not a valid enum member.
     404 if client does not exist (service raises ValueError).
```

Register as `client_tax_profile` in `app/api/__init__.py` and
`app/main.py`.

---

## 4. Feature 2 — Correspondence Log

### 4.1 Purpose

Per-client log of communications with tax authorities or the client
themselves. Each entry records who was spoken to, what type of
communication it was, a subject line, optional notes, and when it
occurred.

### 4.2 ORM Model — `app/models/correspondence.py`

```
Table: correspondence_entries
Columns:
  id                    INTEGER  PK autoincrement
  client_id             INTEGER  FK → clients.id  NOT NULL  INDEX
  contact_id            INTEGER  FK → authority_contacts.id  nullable  INDEX
  correspondence_type   Enum("call","letter","email","meeting")  NOT NULL
  subject               String  NOT NULL
  notes                 Text  nullable
  occurred_at           DateTime  NOT NULL
  created_by            INTEGER  FK → users.id  NOT NULL
  created_at            DateTime  default=utcnow  NOT NULL

Indexes:
  idx_correspondence_client  (client_id)
  idx_correspondence_occurred (occurred_at)
```

Add `Correspondence`, `CorrespondenceType` to `app/models/__init__.py`.

### 4.3 Repository — `app/repositories/correspondence_repository.py`

```
create(
    client_id, contact_id, correspondence_type,
    subject, notes, occurred_at, created_by
) -> Correspondence

list_by_client(client_id: int) -> list[Correspondence]
    # Order by occurred_at DESC
```

### 4.4 Service — `app/services/correspondence_service.py`

```
add_entry(
    client_id, contact_id, correspondence_type,
    subject, notes, occurred_at, created_by
) -> Correspondence
    # Validates client exists.
    # Validates contact_id belongs to client_id when provided.
    # Raises ValueError on any violation.

list_client_entries(client_id: int) -> list[Correspondence]
```

### 4.5 Schemas — `app/schemas/correspondence.py`

```python
class CorrespondenceCreateRequest(BaseModel):
    contact_id: Optional[int] = None
    correspondence_type: str          # validated against enum in API layer
    subject: str
    notes: Optional[str] = None
    occurred_at: datetime             # ISO string from frontend

class CorrespondenceResponse(BaseModel):
    id: int
    client_id: int
    contact_id: Optional[int] = None
    correspondence_type: str
    subject: str
    notes: Optional[str] = None
    occurred_at: datetime
    created_by: int
    created_at: datetime
    model_config = {"from_attributes": True}

class CorrespondenceListResponse(BaseModel):
    items: list[CorrespondenceResponse]
```

### 4.6 API Router — `app/api/correspondence.py`

```
prefix = /clients
tags   = ["correspondence"]
auth   = require_role(ADVISOR, SECRETARY)

GET  /clients/{client_id}/correspondence
     → CorrespondenceListResponse

POST /clients/{client_id}/correspondence
     body: CorrespondenceCreateRequest
     → CorrespondenceResponse  201
     400 if correspondence_type is invalid.
     404 if client not found (service ValueError).
     400 if contact_id is provided but does not belong to the client.
```

The `created_by` field is taken from `user.id` (the current authenticated
user), not from the request body.

Register as `correspondence` in `app/api/__init__.py` and `app/main.py`.

---

## 5. Feature 3 — Annual Report Detail

### 5.1 Purpose

Extend existing `AnnualReport` records with four advisory fields:
tax refund amount, tax due amount, the datetime the client approved the
report, and internal notes. These are optional enrichment fields — they
are never required to create or transition a report.

### 5.2 Approach — extend existing model via a companion table

Do **not** add columns to `annual_reports`. Create a companion table
`annual_report_details` with a 1:1 relationship.

### 5.3 ORM Model — `app/models/annual_report_detail.py`

```
Table: annual_report_details
Columns:
  id                 INTEGER  PK autoincrement
  report_id          INTEGER  FK → annual_reports.id  NOT NULL  UNIQUE  INDEX
  tax_refund_amount  Numeric(10,2)  nullable
  tax_due_amount     Numeric(10,2)  nullable
  client_approved_at  DateTime  nullable
  internal_notes     Text  nullable
  created_at         DateTime  default=utcnow  NOT NULL
  updated_at         DateTime  nullable
```

Add `AnnualReportDetail` to `app/models/__init__.py`.

### 5.4 Repository — `app/repositories/annual_report_detail_repository.py`

```
get_by_report_id(report_id: int) -> Optional[AnnualReportDetail]
upsert(report_id: int, **fields) -> AnnualReportDetail
    # Create if not exists, update otherwise. Set updated_at = utcnow().
```

### 5.5 Service — `app/services/annual_report_detail_service.py`

```
get_detail(report_id: int) -> Optional[AnnualReportDetail]
    # Returns None if no detail row. Never raises on missing detail.

update_detail(report_id: int, **fields) -> AnnualReportDetail
    # Validates report exists via AnnualReportRepository.
    # Raises ValueError if report not found.
    # Calls repo.upsert().
```

### 5.6 Schemas — `app/schemas/annual_report_detail.py`

```python
class AnnualReportDetailResponse(BaseModel):
    report_id: int
    tax_refund_amount: Optional[float] = None
    tax_due_amount: Optional[float] = None
    client_approved_at: Optional[datetime] = None
    internal_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class AnnualReportDetailUpdateRequest(BaseModel):
    tax_refund_amount: Optional[float] = None
    tax_due_amount: Optional[float] = None
    client_approved_at: Optional[datetime] = None
    internal_notes: Optional[str] = None
```

When `GET` finds no detail row, return `AnnualReportDetailResponse` with
all optional fields `None` and `report_id` set. Do **not** 404.

### 5.7 API Router — `app/api/annual_report_detail.py`

```
prefix = /annual-reports
tags   = ["annual-report-detail"]
auth   = require_role(ADVISOR, SECRETARY)

GET  /annual-reports/{report_id}/details
     → AnnualReportDetailResponse
     404 if the parent annual_report does not exist.

PATCH /annual-reports/{report_id}/details
     body: AnnualReportDetailUpdateRequest
     → AnnualReportDetailResponse
     400 on validation errors.
     404 if the parent annual_report does not exist.
```

Register as `annual_report_detail` in `app/api/__init__.py` and
`app/main.py`. Mount **before** the existing `annual_report` router in
`app/main.py` (same ordering hygiene as `binders_operations` before
`binders`).

---

## 6. Feature 4 — Advance Payments

### 6.1 Purpose

Track monthly advance tax payments (מקדמות מס) per client per year. Each
row represents one calendar month for one client. The advisor sets the
expected amount when creating a tax deadline; the secretary records what
was actually paid.

### 6.2 ORM Model — `app/models/advance_payment.py`

```
Table: advance_payments
Columns:
  id               INTEGER  PK autoincrement
  client_id        INTEGER  FK → clients.id  NOT NULL  INDEX
  tax_deadline_id  INTEGER  FK → tax_deadlines.id  nullable  INDEX
  month            Integer  NOT NULL   -- 1..12
  year             Integer  NOT NULL
  expected_amount  Numeric(10,2)  nullable
  paid_amount      Numeric(10,2)  nullable
  status           Enum("pending","paid","partial","overdue")  default="pending"  NOT NULL
  due_date         Date  NOT NULL
  created_at       DateTime  default=utcnow  NOT NULL
  updated_at       DateTime  nullable

Unique constraint: (client_id, year, month)
Index: idx_advance_payment_client_year (client_id, year)
Index: idx_advance_payment_status (status)
```

Add `AdvancePayment`, `AdvancePaymentStatus` to
`app/models/__init__.py`.

### 6.3 Repository — `app/repositories/advance_payment_repository.py`

```
list_by_client_year(client_id: int, year: int) -> list[AdvancePayment]
    # Returns up to 12 rows. Order by month ASC.

get_by_id(id: int) -> Optional[AdvancePayment]

update(id: int, **fields) -> Optional[AdvancePayment]
    # Sets updated_at = utcnow(). Returns None if not found.

create(
    client_id, year, month, due_date,
    expected_amount=None, paid_amount=None,
    tax_deadline_id=None
) -> AdvancePayment
    # status defaults to "pending".
```

### 6.4 Service — `app/services/advance_payment_service.py`

```
list_payments(client_id: int, year: int) -> list[AdvancePayment]
    # No business logic beyond fetching. Returns existing rows.
    # Does NOT auto-generate missing months — rows are created externally
    # (manually or via a future job).

update_payment(payment_id: int, **fields) -> AdvancePayment
    # Validates payment exists.
    # Validates status is a valid enum value when provided.
    # Raises ValueError on any violation.
    # Calls repo.update().
```

### 6.5 Schemas — `app/schemas/advance_payment.py`

```python
class AdvancePaymentRow(BaseModel):
    id: int
    client_id: int
    tax_deadline_id: Optional[int] = None
    month: int
    year: int
    expected_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    status: str                        # "pending"|"paid"|"partial"|"overdue"
    due_date: date
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class AdvancePaymentListResponse(BaseModel):
    items: list[AdvancePaymentRow]
    page: int
    page_size: int
    total: int

class AdvancePaymentUpdateRequest(BaseModel):
    paid_amount: Optional[float] = None
    status: Optional[str] = None
```

### 6.6 API Router — `app/api/advance_payments.py`

```
prefix = /advance-payments
tags   = ["advance-payments"]
auth   = require_role(ADVISOR, SECRETARY)

GET  /advance-payments
     Query params:
       client_id: int  (required)
       year: int       (required)
       page: int = 1
       page_size: int = 20
     → AdvancePaymentListResponse
     400 if client_id or year is missing.
     404 if client does not exist.

PATCH /advance-payments/{payment_id}
     body: AdvancePaymentUpdateRequest
     → AdvancePaymentRow
     400 if status value is not a valid enum member.
     404 if payment not found (service ValueError).
```

Register as `advance_payments` in `app/api/__init__.py` and
`app/main.py`.

---

## 7. Registration Checklist

After implementing all four features, the following files must be
updated:

### `app/api/__init__.py`

Add to the import block and `__all__` list:

```python
from app.api import (
    ...
    annual_report_detail,
    advance_payments,
    client_tax_profile,
    correspondence,
)
```

### `app/main.py`

Add `include_router` calls. Ordering matters — detail routers before
their parent routers:

```python
app.include_router(annual_report_detail.router, prefix="/api/v1")  # before annual_report
app.include_router(annual_report.router, prefix="/api/v1")
...
app.include_router(client_tax_profile.router, prefix="/api/v1")
app.include_router(correspondence.router, prefix="/api/v1")
app.include_router(advance_payments.router, prefix="/api/v1")
```

### `app/models/__init__.py`

Add all new model classes and enums.

### `app/repositories/__init__.py`

Add all new repository classes.

---

## 8. Authorization Matrix

| Endpoint | ADVISOR | SECRETARY |
|----------|---------|-----------|
| GET /clients/{id}/tax-profile | ✅ | ✅ |
| PATCH /clients/{id}/tax-profile | ✅ | ✅ |
| GET /clients/{id}/correspondence | ✅ | ✅ |
| POST /clients/{id}/correspondence | ✅ | ✅ |
| GET /annual-reports/{id}/details | ✅ | ✅ |
| PATCH /annual-reports/{id}/details | ✅ | ✅ |
| GET /advance-payments | ✅ | ✅ |
| PATCH /advance-payments/{id} | ✅ | ✅ |

No endpoint in this batch is ADVISOR-only.

---

## 9. Error Response Conventions

All errors follow the existing `ErrorResponse.build()` envelope from
`app/core/exceptions.py`. Routers raise `HTTPException`; the centralized
handler formats them. Do not build custom error responses in routers.

```
404 → "Client not found" / "Report not found" / "Payment not found"
400 → descriptive message from ValueError caught in router
422 → handled automatically by FastAPI request validation
```

---

## 10. File Size Constraint

Each new file must be **≤ 150 lines**. Split if needed:

- If a service grows past 150 lines, extract a `*_helpers.py` or
  `*_validators.py` module (see `binder_helpers.py` as precedent).
- If a router grows past 150 lines, split into a sub-router module.

---

## 11. Testing Notes

The existing test suite uses `APP_ENV=test` with a fresh SQLite DB. All
four new ORM models will be auto-created by `Base.metadata.create_all`.
No test fixtures need to be seeded for the models to be present.

When writing tests:

- Use the existing `client` fixture to get a valid `client_id`.
- For Advance Payments, create rows manually via the repo in the test
  setup — the `GET` endpoint does not auto-generate rows.
- For Annual Report Detail and Tax Profile, `GET` before `PATCH` should
  return all-null fields (not 404).

---

## 12. Summary of New Files

```
app/models/client_tax_profile.py
app/models/correspondence.py
app/models/annual_report_detail.py
app/models/advance_payment.py

app/repositories/client_tax_profile_repository.py
app/repositories/correspondence_repository.py
app/repositories/annual_report_detail_repository.py
app/repositories/advance_payment_repository.py

app/services/client_tax_profile_service.py
app/services/correspondence_service.py
app/services/annual_report_detail_service.py
app/services/advance_payment_service.py

app/schemas/client_tax_profile.py
app/schemas/correspondence.py
app/schemas/annual_report_detail.py
app/schemas/advance_payment.py

app/api/client_tax_profile.py
app/api/correspondence.py
app/api/annual_report_detail.py
app/api/advance_payments.py
```

Updated files:
```
app/models/__init__.py
app/repositories/__init__.py
app/api/__init__.py
app/main.py
```

Total new files: **16**. Total changed files: **4**.

---

End of specification.
