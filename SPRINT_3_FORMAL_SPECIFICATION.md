# Sprint 3 – Formal Specification  
## Billing & Invoicing Module

**Project:** Binder & Billing CRM  
**Document Type:** Functional & Technical Specification  
**Sprint:** 3  
**Status:** Pending Freeze Approval  
**Audience:** Product Owner, Backend Engineering, Technical Audit  

---

## 1. Objective

The objective of Sprint 3 is to introduce **internal billing capabilities** into the Binder & Billing CRM system.

This sprint enables the system to:
- Track client payment obligations
- Manage the lifecycle of those obligations
- Link obligations to externally issued invoices

Sprint 3 does **not** transform the system into an accounting or payment platform.

---

## 2. Scope Definition

### 2.1 In Scope

Sprint 3 includes:
- Internal billing entities (Charges)
- External invoice references (Invoices)
- Controlled lifecycle management
- Authorization enforcement
- Database schema expansion via migration

---

### 2.2 Out of Scope

The following are explicitly excluded from Sprint 3:

- Payment processing or clearing
- Tax or VAT calculation
- Partial or split payments
- Discounts, credits, or refunds
- Bank reconciliation
- Financial reporting
- Notifications or reminders
- Background or scheduled jobs
- File generation (PDFs)
- Client-facing billing portals

Any of the above require a future sprint.

---

## 3. Conceptual Overview

### 3.1 Charge

A **Charge** represents a monetary obligation of a client toward the firm.

A Charge:
- Is an internal system entity
- Exists independently of invoices
- Is immutable after issuance
- Serves as the source of truth for billing state

A Charge answers:

> “What does the client owe, for which service, and what is its current state?”

---

### 3.2 Invoice

An **Invoice** represents a reference to a document issued by an **external invoicing provider**.

An Invoice:
- Contains metadata only
- Is linked one-to-one with a Charge
- Is optional but permanent once attached

The system does not generate, calculate, or validate invoice contents.

---

## 4. Data Model Specification

### 4.1 Charges Table

| Field | Description |
|------|-------------|
| id | Unique identifier |
| client_id | Reference to client |
| amount | Positive monetary value |
| currency | Default: ILS |
| charge_type | `retainer` or `one_time` |
| period | Billing period (`YYYY-MM`), nullable |
| status | `draft`, `issued`, `paid`, `canceled` |
| created_at | Creation timestamp |
| issued_at | Issuance timestamp |
| paid_at | Payment timestamp |

**Constraints:**
- Charges may not be deleted
- Amount is immutable after issuance
- No partial payments are allowed

---

### 4.2 Invoices Table

| Field | Description |
|------|-------------|
| id | Unique identifier |
| charge_id | One-to-one reference to Charge |
| provider | External provider name |
| external_invoice_id | Provider-issued identifier |
| document_url | Optional reference |
| issued_at | External issue timestamp |
| created_at | Record creation timestamp |

**Constraints:**
- An Invoice must reference a valid Charge
- A Charge may exist without an Invoice
- An Invoice cannot be modified after creation

---

## 5. Business Rules

### 5.1 Charge Lifecycle Rules

1. Charges are created in `draft` status
2. Draft charges may be edited or canceled
3. Issued charges:
   - Lock amount and type
   - Cannot be deleted
4. Paid charges:
   - Are fully immutable
   - Represent final settlement

---

### 5.2 Invoice Rules

- Invoices may only be attached to issued charges
- Each charge may have at most one invoice
- Invoice metadata is immutable once stored

---

### 5.3 Data Integrity Rules

- No charge may exist without a valid client
- No invoice may exist without a valid charge
- No hard deletion of billing records is permitted

---

## 6. Authorization Model

### 6.1 Roles

| Role | Description |
|------|-------------|
| ADVISOR | Administrative user |
| SECRETARY | Operational, read-only user |

---

### 6.2 Permissions

| Operation | ADVISOR | SECRETARY |
|---------|---------|-----------|
| Create Charge | Allowed | Not allowed |
| Issue Charge | Allowed | Not allowed |
| Mark Charge Paid | Allowed | Not allowed |
| Cancel Charge | Allowed | Not allowed |
| View Charges | Allowed | Allowed |
| View Invoices | Allowed | Allowed |

---

## 7. API Surface (Sprint 3)

### 7.1 Write Operations (Advisor Only)

- `POST /charges`
- `POST /charges/{id}/issue`
- `POST /charges/{id}/mark-paid`
- `POST /charges/{id}/cancel`

---

### 7.2 Read Operations

- `GET /charges`
- `GET /charges/{id}`

**Notes:**
- No delete endpoints
- No update endpoints after issuance
- No payment or invoice generation endpoints

---

## 8. Database Migration Policy

Sprint 3 introduces database migrations under the following rules:

- Alembic is the sole migration tool
- Exactly one migration is permitted
- Migration scope is limited to:
  - Creation of `charges` table
  - Creation of `invoices` table
- Existing tables must not be modified
- No data backfills or transformations

Any schema change beyond this scope requires a new sprint.

---

## 9. Definition of Done

Sprint 3 is considered complete only when:

- Charges and Invoices exist in the database
- A single migration has been applied
- All business rules are enforced at the service layer
- Authorization rules are fully enforced
- No raw SQL is introduced
- No file exceeds 150 lines
- Sprint 1 and Sprint 2 behavior remains unchanged

---

## 10. Freeze Statement

Upon approval, this specification is **frozen**.

Any modification to:
- Billing logic
- Database schema
- Payment handling
- Automation or notifications

requires a new sprint and a new specification document.

---

## 11. Approval Checkpoint

To finalize and freeze this specification, confirm the following:

**Charge Creation Policy for Sprint 3:**

- [ ] Manual creation only  
- [ ] Manual now, automated in future sprint  
- [ ] One-time charges only in this sprint  

Once confirmed, this document status will be updated to:

**Status: FROZEN**