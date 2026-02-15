# SPRINT 7 FORMAL SPECIFICATION: Tax CRM Core Features

**Project:** Binder & Billing CRM → Tax Consultant CRM Evolution
**Sprint:** 7
**Status:** PROPOSED
**Dependencies:** Sprints 1-6 (FROZEN)

---

## 1. SPRINT SCOPE

### 1.1 Objectives
Implement core tax-specific features that transform the general Binder CRM into a specialized Tax Consultant CRM:

1. Annual report tracking with workflow stages
2. Tax deadline management with visual urgency indicators
3. Client profile tax-specific extensions
4. Dashboard tax submission widget

### 1.2 Out of Scope (Deferred to Sprint 8+)
- Capital statement management
- Time tracking / billable hours
- Bulk messaging system
- Client upload portal
- Revenue analytics graphs

---

## 2. DATA MODEL EXTENSIONS

### 2.1 New Models

#### AnnualReport
```python
class ReportStage(str, PyEnum):
    MATERIAL_COLLECTION = "material_collection"
    IN_PROGRESS = "in_progress"
    FINAL_REVIEW = "final_review"
    CLIENT_SIGNATURE = "client_signature"
    TRANSMITTED = "transmitted"

class AnnualReport(Base):
    __tablename__ = "annual_reports"
    
    id: int (PK)
    client_id: int (FK → clients.id, NOT NULL, indexed)
    tax_year: int (NOT NULL)  # e.g., 2025
    stage: ReportStage (NOT NULL, default=MATERIAL_COLLECTION)
    status: str  # "not_started", "in_progress", "completed"
    
    # Dates
    created_at: datetime (NOT NULL)
    due_date: date (nullable)
    submitted_at: datetime (nullable)
    
    # Metadata
    form_type: str (nullable)  # "106", "856", etc.
    notes: text (nullable)
    
    # Constraints
    UNIQUE(client_id, tax_year)
```

#### TaxDeadline
```python
class DeadlineType(str, PyEnum):
    VAT = "vat"  # Ma'am
    ADVANCE_PAYMENT = "advance_payment"  # Mikdamot
    NATIONAL_INSURANCE = "national_insurance"  # Bituach Leumi
    ANNUAL_REPORT = "annual_report"
    OTHER = "other"

class UrgencyLevel(str, PyEnum):
    GREEN = "green"  # > 7 days
    YELLOW = "yellow"  # 3-7 days
    RED = "red"  # < 3 days
    OVERDUE = "overdue"

class TaxDeadline(Base):
    __tablename__ = "tax_deadlines"
    
    id: int (PK)
    client_id: int (FK → clients.id, NOT NULL, indexed)
    deadline_type: DeadlineType (NOT NULL)
    due_date: date (NOT NULL, indexed)
    status: str (NOT NULL)  # "pending", "completed", "canceled"
    
    # Financial
    payment_amount: Decimal(10, 2) (nullable)
    currency: str (default="ILS")
    
    # Computed (derived)
    # urgency_level: computed dynamically, NOT persisted
    
    # Metadata
    description: text (nullable)
    created_at: datetime (NOT NULL)
    completed_at: datetime (nullable)
```

#### AuthorityContact
```python
class ContactType(str, PyEnum):
    ASSESSING_OFFICER = "assessing_officer"  # Pakid Shuma
    VAT_BRANCH = "vat_branch"
    NATIONAL_INSURANCE = "national_insurance"
    OTHER = "other"

class AuthorityContact(Base):
    __tablename__ = "authority_contacts"
    
    id: int (PK)
    client_id: int (FK → clients.id, NOT NULL, indexed)
    contact_type: ContactType (NOT NULL)
    
    # Contact details
    name: str (NOT NULL)
    office: str (nullable)
    phone: str (nullable)
    email: str (nullable)
    
    # Metadata
    notes: text (nullable)
    created_at: datetime (NOT NULL)
    updated_at: datetime (nullable)
```

---

### 2.2 Modified Models

#### Client (Extensions)
```python
# ADD fields to existing Client model:
tax_id: str (nullable)  # Company tax ID (H.P)
spouse_name: str (nullable)
spouse_id_number: str (nullable)
```

#### PermanentDocument (Extensions)
```python
# ADD fields to existing PermanentDocument model:
tax_year: int (nullable)  # Document belongs to which tax year
form_type: str (nullable)  # "106", "PENSION_CERT", etc.
```

---

## 3. SERVICE LAYER

### 3.1 AnnualReportService
**Location:** `app/services/annual_report_service.py`

**Responsibilities:**
- Create annual reports for clients
- Transition between workflow stages
- Validate stage prerequisites
- Query reports by stage, client, year

**Key Methods:**
```python
def create_report(client_id: int, tax_year: int, form_type: str = None) -> AnnualReport
def transition_stage(report_id: int, new_stage: ReportStage, user_id: int) -> AnnualReport
def get_reports_by_stage(stage: ReportStage) -> list[AnnualReport]
def get_client_reports(client_id: int, tax_year: int = None) -> list[AnnualReport]
def mark_submitted(report_id: int, submitted_at: datetime) -> AnnualReport
```

**Business Rules:**
- Cannot skip stages (must go sequentially)
- Cannot transition to TRANSMITTED without CLIENT_SIGNATURE
- Submitted reports cannot be edited (only viewed)

---

### 3.2 TaxDeadlineService
**Location:** `app/services/tax_deadline_service.py`

**Responsibilities:**
- Track tax deadlines per client
- Compute urgency levels (RED/YELLOW/GREEN)
- Detect overdue deadlines
- Generate alerts for upcoming deadlines

**Key Methods:**
```python
def create_deadline(client_id: int, deadline_type: DeadlineType, due_date: date, amount: Decimal = None) -> TaxDeadline
def mark_completed(deadline_id: int) -> TaxDeadline
def get_upcoming_deadlines(days_ahead: int = 7) -> list[TaxDeadline]
def compute_urgency(deadline: TaxDeadline, reference_date: date = None) -> UrgencyLevel
def get_client_deadlines(client_id: int, status: str = None) -> list[TaxDeadline]
```

**Urgency Calculation Logic:**
```python
def compute_urgency(deadline: TaxDeadline, reference_date: date) -> UrgencyLevel:
    if deadline.status == "completed":
        return None  # No urgency for completed
    
    days_remaining = (deadline.due_date - reference_date).days
    
    if days_remaining < 0:
        return UrgencyLevel.OVERDUE
    elif days_remaining <= 2:
        return UrgencyLevel.RED
    elif days_remaining <= 7:
        return UrgencyLevel.YELLOW
    else:
        return UrgencyLevel.GREEN
```

---

### 3.3 AuthorityContactService
**Location:** `app/services/authority_contact_service.py`

**Responsibilities:**
- Manage authority contacts per client
- CRUD operations
- Validate contact information

**Key Methods:**
```python
def add_contact(client_id: int, contact_type: ContactType, name: str, **details) -> AuthorityContact
def update_contact(contact_id: int, **fields) -> AuthorityContact
def list_client_contacts(client_id: int, contact_type: ContactType = None) -> list[AuthorityContact]
def delete_contact(contact_id: int) -> None
```

---

### 3.4 DashboardTaxService
**Location:** `app/services/dashboard_tax_service.py`

**Responsibilities:**
- Aggregate data for tax-specific dashboard widgets
- Submission statistics
- Deadline summaries

**Key Methods:**
```python
def get_submission_widget_data(tax_year: int = None) -> dict
def get_deadline_summary() -> dict
def get_urgent_deadlines() -> list[dict]
```

**Widget Response Example:**
```json
{
  "tax_year": 2025,
  "total_clients": 150,
  "reports_submitted": 45,
  "reports_in_progress": 32,
  "reports_not_started": 73,
  "submission_percentage": 30.0
}
```

---

## 4. API ENDPOINTS

### 4.1 Annual Reports

#### POST /api/v1/annual-reports
**Auth:** ADVISOR + SECRETARY
**Request:**
```json
{
  "client_id": 123,
  "tax_year": 2025,
  "form_type": "106",
  "due_date": "2026-04-30",
  "notes": "Standard annual report"
}
```
**Response 201:**
```json
{
  "id": 1,
  "client_id": 123,
  "tax_year": 2025,
  "stage": "material_collection",
  "status": "not_started",
  "form_type": "106",
  "due_date": "2026-04-30",
  "created_at": "2026-02-15T10:00:00",
  "submitted_at": null
}
```

---

#### GET /api/v1/annual-reports
**Auth:** ADVISOR + SECRETARY
**Query Params:**
- `client_id` (optional)
- `tax_year` (optional)
- `stage` (optional)
- `page` (default: 1)
- `page_size` (default: 20)

**Response 200:**
```json
{
  "items": [...],
  "page": 1,
  "page_size": 20,
  "total": 45
}
```

---

#### GET /api/v1/annual-reports/{report_id}
**Auth:** ADVISOR + SECRETARY

---

#### POST /api/v1/annual-reports/{report_id}/transition
**Auth:** ADVISOR + SECRETARY
**Request:**
```json
{
  "to_stage": "in_progress"
}
```
**Response 200:** Updated report

**Errors:**
- `400`: Invalid stage transition
- `404`: Report not found

---

#### POST /api/v1/annual-reports/{report_id}/submit
**Auth:** ADVISOR only
**Request:**
```json
{
  "submitted_at": "2026-04-15T14:30:00"
}
```
**Response 200:** Updated report

---

#### GET /api/v1/annual-reports/kanban
**Auth:** ADVISOR + SECRETARY
**Response 200:**
```json
{
  "stages": [
    {
      "stage": "material_collection",
      "reports": [
        {
          "id": 1,
          "client_id": 123,
          "client_name": "Example Corp",
          "tax_year": 2025,
          "days_until_due": 45
        }
      ]
    },
    {
      "stage": "in_progress",
      "reports": [...]
    }
  ]
}
```

---

### 4.2 Tax Deadlines

#### POST /api/v1/tax-deadlines
**Auth:** ADVISOR + SECRETARY
**Request:**
```json
{
  "client_id": 123,
  "deadline_type": "vat",
  "due_date": "2026-02-25",
  "payment_amount": 5000.00,
  "description": "February VAT payment"
}
```

---

#### GET /api/v1/tax-deadlines
**Auth:** ADVISOR + SECRETARY
**Query Params:**
- `client_id` (optional)
- `deadline_type` (optional)
- `status` (optional)
- `from_date` (optional)
- `to_date` (optional)

---

#### GET /api/v1/tax-deadlines/{deadline_id}

---

#### POST /api/v1/tax-deadlines/{deadline_id}/complete
**Auth:** ADVISOR + SECRETARY

---

#### GET /api/v1/dashboard/tax-deadlines
**Auth:** ADVISOR + SECRETARY
**Response 200:**
```json
{
  "urgent": [
    {
      "id": 5,
      "client_id": 123,
      "client_name": "Example Corp",
      "deadline_type": "vat",
      "due_date": "2026-02-16",
      "urgency": "red",
      "days_remaining": 1,
      "payment_amount": 5000.00
    }
  ],
  "upcoming": [...]
}
```

---

### 4.3 Authority Contacts

#### POST /api/v1/clients/{client_id}/authority-contacts
**Auth:** ADVISOR + SECRETARY

---

#### GET /api/v1/clients/{client_id}/authority-contacts
**Auth:** ADVISOR + SECRETARY

---

#### PATCH /api/v1/authority-contacts/{contact_id}
**Auth:** ADVISOR + SECRETARY

---

#### DELETE /api/v1/authority-contacts/{contact_id}
**Auth:** ADVISOR only

---

### 4.4 Dashboard Enhancements

#### GET /api/v1/dashboard/tax-submissions
**Auth:** ADVISOR + SECRETARY
**Query Params:**
- `tax_year` (optional, defaults to current year)

**Response 200:**
```json
{
  "tax_year": 2025,
  "total_clients": 150,
  "reports_submitted": 45,
  "reports_in_progress": 32,
  "reports_not_started": 73,
  "submission_percentage": 30.0
}
```

---

## 5. AUTHORIZATION RULES

### 5.1 Role-Based Access

**ADVISOR:**
- Full access to all annual reports endpoints
- Can submit reports
- Can delete authority contacts

**SECRETARY:**
- Read access to annual reports
- Can create and transition reports
- Cannot submit reports (ADVISOR only)
- Can create/update authority contacts
- Cannot delete authority contacts

---

## 6. NOTIFICATIONS & JOBS

### 6.1 New Background Jobs

#### DailyDeadlineReminderJob
**Frequency:** Daily at 8:00 AM
**Purpose:** Send reminders for upcoming tax deadlines

**Logic:**
1. Fetch all deadlines with `status = "pending"`
2. Filter deadlines due within 3 days (RED urgency)
3. Check if reminder already sent (idempotency)
4. Send WhatsApp/Email notification per client

---

### 6.2 New Notification Triggers

```python
class NotificationTrigger(str, PyEnum):
    # Existing triggers...
    TAX_DEADLINE_URGENT = "tax_deadline_urgent"
    TAX_DEADLINE_APPROACHING = "tax_deadline_approaching"
    ANNUAL_REPORT_DUE = "annual_report_due"
```

---

## 7. DATA MIGRATION

### 7.1 Client Extensions
- Add nullable columns to `clients` table
- No data migration required (fields optional)

### 7.2 Document Extensions
- Add nullable columns to `permanent_documents` table
- Existing documents have `tax_year = NULL` (valid state)

---

## 8. TESTING REQUIREMENTS

### 8.1 Unit Tests
- `test_annual_report_service.py`: Stage transitions, validations
- `test_tax_deadline_service.py`: Urgency calculation, filtering
- `test_authority_contact_service.py`: CRUD operations

### 8.2 API Tests
- `test_annual_reports_api.py`: Full lifecycle
- `test_tax_deadlines_api.py`: Authorization, filters
- `test_dashboard_tax_api.py`: Widget data accuracy

### 8.3 Regression Tests
- Verify Sprints 1-6 unchanged
- All existing endpoints return same responses

---

## 9. SUCCESS CRITERIA

Sprint 7 is complete when:

✅ All 3 new models created and migrated
✅ All 4 new services implemented (< 150 lines each)
✅ All 15+ new endpoints functional
✅ Dashboard tax widgets rendering
✅ 100% test coverage for new features
✅ No regressions in existing features
✅ Documentation updated

---

## 10. FREEZE DECLARATION TEMPLATE

Upon completion, create `SPRINT_7_FREEZE_DECLARATION.md`:

```
# Sprint 7 Freeze Declaration

Date: [YYYY-MM-DD]
Status: FROZEN

## Completed Features
- Annual Report Tracking
- Tax Deadline Management
- Authority Contacts
- Dashboard Tax Widgets

## Contract Endpoints (IMMUTABLE)
[List all new endpoints]

## Known Limitations
[Document any deferred items]

## Next Sprint
Sprint 8: Capital Statements & Time Tracking
```

---

End of Sprint 7 Specification
