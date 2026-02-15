# Tax Consultant CRM - Feature Analysis & Implementation Plan

## Executive Summary

This document analyzes the gap between the current **Binder & Billing CRM** and the required **Tax Consultant CRM** features, providing a comprehensive implementation roadmap.

---

## Current System Capabilities (Sprint 6)

### ✅ Already Implemented
1. **Client Management**: Full CRUD with status tracking (Active/Frozen/Closed)
2. **Document Tracking**: Permanent document presence tracking (ID Copy, Power of Attorney, Engagement Agreement)
3. **Binder Lifecycle**: Intake → In Office → Ready for Pickup → Returned
4. **Billing System**: Charges (Draft/Issued/Paid/Canceled), Invoice attachments
5. **Notifications**: WhatsApp/Email with fallback
6. **Operational Signals**: Missing documents, SLA tracking, idle binders
7. **Dashboard**: Work queue, alerts, attention items
8. **Timeline**: Unified client event history
9. **Search**: Multi-criteria search across clients and binders
10. **User Management**: ADVISOR and SECRETARY roles with audit logs

### 🔧 System Architecture
- **Layer Separation**: API → Service → Repository → ORM
- **150-line file limit** (strict enforcement)
- **No raw SQL** (ORM-only)
- **Derived state policy**: SLA, WorkState, Signals computed dynamically
- **Idempotent background jobs**

---

## Gap Analysis: New Features Required

### 1. Dashboard Enhancements

#### **Tax Submission Status Widget**
**Requirements:**
- Visual progress indicator (Submitted vs. Total)
- Annual report tracking per client
- Status categories: Not Started, In Progress, Submitted

**Implementation:**
```
NEW MODELS:
- AnnualReport (client_id, tax_year, status, submitted_at, due_date)

NEW SERVICES:
- AnnualReportService (create, update_status, get_submission_stats)
- DashboardTaxService (get_submission_widget_data)

NEW ENDPOINTS:
- GET /api/v1/dashboard/tax-submissions
- POST /api/v1/annual-reports
- PATCH /api/v1/annual-reports/{id}
```

**Status:** 🆕 NEW FEATURE

---

#### **Deadline Countdown Widget**
**Requirements:**
- VAT (Ma'am) deadlines
- Advance Payments (Mikdamot) deadlines
- National Insurance (Bituach Leumi) deadlines
- Color-coded urgency (Red/Yellow/Green)

**Implementation:**
```
NEW MODELS:
- TaxDeadline (client_id, deadline_type, due_date, status, payment_amount)
- DeadlineType ENUM (VAT, ADVANCE_PAYMENT, NATIONAL_INSURANCE)

NEW SERVICES:
- TaxDeadlineService (track, calculate_urgency, get_upcoming)
- DeadlineAlertService (compute_color_coding)

NEW ENDPOINTS:
- GET /api/v1/dashboard/deadlines
- POST /api/v1/tax-deadlines
- PATCH /api/v1/tax-deadlines/{id}/mark-completed
```

**Status:** 🆕 NEW FEATURE

---

#### **Daily Tasks Integration**
**Requirements:**
- To-do list for consultant
- Task assignment to clients/binders
- Due date tracking

**Implementation:**
```
NEW MODELS:
- Task (title, description, due_date, status, assigned_to, client_id, binder_id)
- TaskStatus ENUM (PENDING, IN_PROGRESS, COMPLETED, CANCELED)

NEW SERVICES:
- TaskService (create, assign, update_status, list_by_user)

NEW ENDPOINTS:
- GET /api/v1/tasks
- POST /api/v1/tasks
- PATCH /api/v1/tasks/{id}
- POST /api/v1/tasks/{id}/complete
```

**Status:** 🆕 NEW FEATURE

---

#### **Revenue Metrics Graph**
**Requirements:**
- Retainer income vs. One-time projects
- Time-series visualization
- Filter by date range

**Implementation:**
```
EXTENDS EXISTING:
- Charge model already has charge_type (RETAINER, ONE_TIME)
- BillingService already tracks payments

NEW SERVICES:
- RevenueAnalyticsService (aggregate_by_type, get_time_series)

NEW ENDPOINTS:
- GET /api/v1/dashboard/revenue-metrics?from=2026-01-01&to=2026-12-31
```

**Status:** ✅ EXTENDS EXISTING (Charge system)

---

### 2. Client Profile Enhancements

#### **Entity Type Tracking**
**Requirements:**
- Expand ClientType to include tax-specific types
- Track Exempt (Patur) vs. Authorized Dealer (Osek Murshe) vs. Limited Company

**Implementation:**
```
MODIFY EXISTING:
ClientType ENUM:
  - OSEK_PATUR (already exists)
  - OSEK_MURSHE (already exists)
  - COMPANY (already exists)
  - EMPLOYEE (already exists)
  
ADD NEW FIELDS:
- tax_id: str (H.P number for companies)
- spouse_name: str (optional)
- spouse_id_number: str (optional)
```

**Status:** ⚡ EXTENDS EXISTING (Client model)

---

#### **Authorities Contacts**
**Requirements:**
- Assigned Assessing Officer (Pakid Shuma)
- VAT branch contact details

**Implementation:**
```
NEW MODELS:
- AuthorityContact (client_id, contact_type, name, office, phone, email, notes)
- ContactType ENUM (ASSESSING_OFFICER, VAT_BRANCH, OTHER)

NEW SERVICES:
- AuthorityContactService (add, update, list_by_client)

NEW ENDPOINTS:
- POST /api/v1/clients/{id}/authority-contacts
- GET /api/v1/clients/{id}/authority-contacts
- PATCH /api/v1/authority-contacts/{id}
```

**Status:** 🆕 NEW FEATURE

---

#### **Document Archive by Tax Year**
**Requirements:**
- Organize documents by tax year (not just type)
- Support multiple documents per type per year
- Form 106, certifications, appendices

**Implementation:**
```
MODIFY EXISTING:
PermanentDocument model:
  ADD: tax_year (int, nullable)
  ADD: form_type (str, nullable) - e.g., "106", "PENSION_CERT"

EXTENDS EXISTING:
- PermanentDocumentService already handles uploads
- Add tax_year filtering to list_client_documents()

NEW ENDPOINTS:
- GET /api/v1/documents/client/{id}?tax_year=2025
```

**Status:** ⚡ EXTENDS EXISTING (PermanentDocument)

---

#### **Activity Log / Audit Trail**
**Requirements:**
- Communication history (WhatsApp, Email, Phone)
- Manual log entries by consultant
- Searchable and filterable

**Implementation:**
```
EXTENDS EXISTING:
- Timeline already tracks system events
- Notification already tracks WhatsApp/Email

NEW MODELS:
- ManualActivityLog (client_id, user_id, activity_type, description, occurred_at)
- ActivityType ENUM (PHONE_CALL, IN_PERSON_MEETING, EMAIL, WHATSAPP, NOTE)

NEW SERVICES:
- ActivityLogService (log_manual_entry, get_client_activity_log)

NEW ENDPOINTS:
- POST /api/v1/clients/{id}/activity-log
- GET /api/v1/clients/{id}/activity-log
```

**Status:** ⚡ EXTENDS EXISTING (Timeline + Notifications)

---

### 3. Annual Reports Pipeline (Kanban View)

#### **Workflow Stages**
**Requirements:**
- Material Collection → In Progress → Final Review → Client Signature → Transmitted
- Drag-and-drop stage transitions
- Filtering by missing documents

**Implementation:**
```
NEW MODELS:
- AnnualReport (already defined above)
- ReportStage ENUM (MATERIAL_COLLECTION, IN_PROGRESS, FINAL_REVIEW, CLIENT_SIGNATURE, TRANSMITTED)

NEW SERVICES:
- AnnualReportWorkflowService (transition_stage, validate_stage_requirements)

NEW ENDPOINTS:
- GET /api/v1/annual-reports/kanban
- POST /api/v1/annual-reports/{id}/transition?to_stage=in_progress
- GET /api/v1/annual-reports/missing-documents
```

**Status:** 🆕 NEW FEATURE (Kanban abstraction on top of AnnualReport)

---

### 4. Capital Statements (Hatzharat Hon)

#### **Submission Tracking**
**Requirements:**
- History of capital statement submissions
- Projection for next required statement
- Built-in checklist (Assets, Bank balances, Vehicles, Loans)

**Implementation:**
```
NEW MODELS:
- CapitalStatement (client_id, submission_date, tax_year, status, next_due_date)
- CapitalStatementItem (statement_id, item_type, description, amount, completed)
- ItemType ENUM (ASSET, BANK_BALANCE, VEHICLE, LOAN, OTHER)

NEW SERVICES:
- CapitalStatementService (create, add_item, mark_item_complete, project_next_due)

NEW ENDPOINTS:
- GET /api/v1/capital-statements?client_id=123
- POST /api/v1/capital-statements
- POST /api/v1/capital-statements/{id}/items
- PATCH /api/v1/capital-statements/{id}/items/{item_id}/complete
```

**Status:** 🆕 NEW FEATURE

---

### 5. Finance & Billing Enhancements

#### **Retainer Tracking**
**Requirements:**
- Monthly payment status (Paid vs. Overdue)
- Automatic overdue detection

**Implementation:**
```
EXTENDS EXISTING:
- Charge model already supports RETAINER type
- Add monthly recurrence tracking

NEW SERVICES:
- RetainerManagementService (generate_monthly_retainers, detect_overdue)

NEW ENDPOINTS:
- GET /api/v1/charges/retainer-status?client_id=123
- POST /api/v1/charges/generate-monthly-retainers (background job)
```

**Status:** ⚡ EXTENDS EXISTING (Charge system)

---

#### **Extra Charges / Billable Hours**
**Requirements:**
- Track consulting hours beyond retainer
- Audit representation billable time
- Hourly rate configuration

**Implementation:**
```
NEW MODELS:
- TimeEntry (client_id, user_id, hours, hourly_rate, description, date, billable, invoiced)

NEW SERVICES:
- TimeTrackingService (log_time, get_unbilled_hours, generate_invoice)

NEW ENDPOINTS:
- POST /api/v1/time-entries
- GET /api/v1/time-entries?client_id=123&billable=true&invoiced=false
- POST /api/v1/time-entries/invoice-batch (converts to ONE_TIME charge)
```

**Status:** 🆕 NEW FEATURE

---

### 6. Automation & Communication

#### **Bulk Messaging**
**Requirements:**
- Send automated reminders to multiple clients
- Template-based messages
- Deadline-triggered notifications

**Implementation:**
```
EXTENDS EXISTING:
- NotificationService already supports WhatsApp/Email
- Add bulk send capability

NEW MODELS:
- MessageTemplate (name, content_template, trigger_type)
- BulkMessage (template_id, recipient_count, sent_at, status)

NEW SERVICES:
- BulkMessagingService (send_bulk, apply_template, filter_recipients)

NEW ENDPOINTS:
- POST /api/v1/notifications/bulk-send
- GET /api/v1/message-templates
- POST /api/v1/message-templates
```

**Status:** ⚡ EXTENDS EXISTING (NotificationService)

---

#### **Client Upload Portal**
**Requirements:**
- Secure upload link sent via WhatsApp/Email
- Direct upload to client's document archive
- No client authentication required (token-based access)

**Implementation:**
```
NEW MODELS:
- UploadToken (client_id, token, expires_at, used_at, created_by)

NEW SERVICES:
- UploadPortalService (generate_token, validate_token, process_upload)

NEW ENDPOINTS (NO AUTH REQUIRED):
- GET /portal/upload/{token} (public HTML page)
- POST /portal/upload/{token}/submit (file upload)

NEW ENDPOINTS (AUTH REQUIRED):
- POST /api/v1/clients/{id}/generate-upload-link
```

**Status:** 🆕 NEW FEATURE (Special case: public endpoints)

---

## Implementation Roadmap

### Phase 1: Core Tax Features (Sprint 7)
**Priority:** HIGH
**Estimated Effort:** 3-4 weeks

1. **Annual Report Tracking**
   - AnnualReport model + service
   - Dashboard submission widget
   - Kanban workflow stages

2. **Tax Deadline Management**
   - TaxDeadline model + service
   - Countdown widget with color coding
   - Automated deadline alerts

3. **Client Profile Extensions**
   - Spouse tracking
   - Authority contacts
   - Tax year organization for documents

**Deliverables:**
- 6 new models
- 4 new services
- 12 new endpoints
- Dashboard enhancements

---

### Phase 2: Capital Statements & Time Tracking (Sprint 8)
**Priority:** MEDIUM-HIGH
**Estimated Effort:** 2-3 weeks

1. **Capital Statement Management**
   - Full lifecycle tracking
   - Built-in checklist
   - Projection calculations

2. **Time Tracking & Extra Charges**
   - Time entry system
   - Billable hours tracking
   - Conversion to charges

**Deliverables:**
- 3 new models
- 2 new services
- 8 new endpoints

---

### Phase 3: Automation & Communication (Sprint 9)
**Priority:** MEDIUM
**Estimated Effort:** 2-3 weeks

1. **Bulk Messaging**
   - Template system
   - Bulk send capability
   - Filtering logic

2. **Client Upload Portal**
   - Token generation
   - Public upload page
   - Secure file handling

3. **Task Management**
   - Task CRUD
   - Assignment logic
   - Dashboard integration

**Deliverables:**
- 4 new models
- 3 new services
- 10 new endpoints
- 1 public portal page

---

### Phase 4: Analytics & Reporting (Sprint 10)
**Priority:** LOW-MEDIUM
**Estimated Effort:** 1-2 weeks

1. **Revenue Analytics**
   - Time-series reports
   - Retainer vs. One-time comparison
   - Export capabilities

2. **Activity Log Enhancements**
   - Manual entry interface
   - Search and filter
   - Timeline integration

**Deliverables:**
- 2 new services
- 4 new endpoints
- Enhanced dashboard

---

## Technical Considerations

### 1. **Maintain Architectural Integrity**
- All new services must respect 150-line limit
- No raw SQL (ORM queries only)
- Layer separation: API → Service → Repository → ORM
- Derived state where possible (avoid redundant persistence)

### 2. **Authorization Model**
- ADVISOR: Full access to all features
- SECRETARY: Read access to most features, limited mutation rights
- Consider new role: ACCOUNTANT (billing-only access)

### 3. **Backward Compatibility**
- All existing Sprint 1-6 endpoints remain unchanged
- Extend existing models carefully (nullable fields)
- Regression tests for all changes

### 4. **Performance Optimization**
- Dashboard widgets must load in < 500ms
- Kanban views need efficient filtering
- Bulk operations must be async (background jobs)

### 5. **Data Migration Strategy**
- Existing clients map naturally to tax clients
- Binders → Annual Reports (semantic mapping)
- Charges → Retainers + Extra Charges (expand existing)

---

## Risks & Mitigation

### Risk 1: Scope Creep
**Mitigation:** Strict sprint boundaries, freeze after each phase

### Risk 2: Performance Degradation
**Mitigation:** Database indexing strategy, pagination everywhere

### Risk 3: User Adoption
**Mitigation:** Gradual rollout, user training, migration guides

### Risk 4: Complexity Explosion
**Mitigation:** Modular design, clear service boundaries, documentation

---

## Success Metrics

### Phase 1 (Core Tax Features)
- ✅ 100% annual reports tracked
- ✅ Zero missed tax deadlines (with alerts)
- ✅ 50% reduction in "missing document" queries

### Phase 2 (Capital Statements)
- ✅ 100% capital statements tracked
- ✅ 80% reduction in checklist errors

### Phase 3 (Automation)
- ✅ 90% of clients receive automated reminders
- ✅ 70% of document uploads via portal

### Phase 4 (Analytics)
- ✅ Revenue visibility within 1 click
- ✅ 100% activity log coverage

---

## Conclusion

The Tax Consultant CRM builds naturally on the existing Binder & Billing CRM foundation. Key advantages:

1. **Reuse existing infrastructure**: Clients, Charges, Notifications, Timeline
2. **Extend, don't rebuild**: 60% of features are enhancements
3. **Preserve architectural quality**: Maintain Sprint 1-6 discipline
4. **Phased rollout**: Minimize risk, maximize learning

**Recommended Next Step:** Approve Phase 1 (Sprint 7) and begin formal specification.
