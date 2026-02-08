# Binder & Billing CRM
## Technical Database Schema (Freeze)

---

## 1. Overview
This document defines the **authoritative database schema** for the Binder & Billing CRM system.
It is intended for backend developers and database engineers and serves as the single source of truth for data structure and relationships.

Database type: **Relational (PostgreSQL recommended)**
Deletion policy: **Soft delete / status-based only (no hard deletes)**

---

## 2. users
System users. Only two roles exist: Tax Advisor and Secretary.

**Table: users**
- `id` (PK, INTEGER, auto-increment; e.g., 1, 2, 3, ...)
- `full_name` (varchar, not null)
- `email` (varchar, unique, not null)
- `phone` (varchar, nullable)
- `role` (enum: `advisor`, `secretary`)
- `is_active` (boolean, default true)
- `created_at` (timestamp)
- `last_login_at` (timestamp, nullable)

---

## 3. clients
Represents a long-term client entity.

**Table: clients**
- `id` (PK, INTEGER, auto-increment; e.g., 1, 2, 3, ...)
- `full_name` (varchar, not null)
- `id_number` (varchar, unique, not null)  
- `client_type` (enum: `osek_patur`, `osek_murshe`, `company`, `employee`)
- `status` (enum: `active`, `frozen`, `closed`)
- `primary_binder_number` (varchar, unique)
- `phone` (varchar)
- `email` (varchar)
- `notes` (text)
- `opened_at` (date)
- `closed_at` (date, nullable)

---

## 4. binders
Represents a **physical binder instance** stored temporarily in the office.

**Table: binders**
- `id` (PK, INTEGER, auto-increment; e.g., 1, 2, 3, ...)
- `client_id` (FK → clients.id)
- `binder_number` (varchar, not null)
- `received_at` (date, not null)
- `expected_return_at` (date, not null)
- `returned_at` (date, nullable)
- `status` (enum: `in_office`, `ready_for_pickup`, `returned`, `overdue`)
- `received_by` (FK → users.id)
- `returned_by` (FK → users.id, nullable)
- `pickup_person_name` (varchar, nullable)
- `notes` (text)

Constraints:
- Only one active (non-returned) binder per binder_number

---

## 5. binder_status_logs
Full audit log for binder lifecycle changes.

**Table: binder_status_logs**
- `id` (PK, INTEGER, auto-increment; e.g., 1, 2, 3, ...)
- `binder_id` (FK → binders.id)
- `old_status` (varchar)
- `new_status` (varchar)
- `changed_by` (FK → users.id)
- `changed_at` (timestamp)
- `notes` (text, nullable)

---

## 6. permanent_documents
Tracks presence of required permanent documents.

**Table: permanent_documents**
- `id` (PK, INTEGER, auto-increment; e.g., 1, 2, 3, ...)
- `client_id` (FK → clients.id)
- `document_type` (enum: `id_copy`, `power_of_attorney`, `engagement_agreement`, `vat_registration`, `tax_registration`)
- `is_present` (boolean)
- `uploaded_at` (timestamp, nullable)
- `uploaded_by` (FK → users.id, nullable)
- `file_url` (varchar, nullable)
- `notes` (text)

---

## 7. charges
Internal billing requests (retainers or one-time charges).

**Table: charges**
- `id` (PK, INTEGER, auto-increment; e.g., 1, 2, 3, ...)
- `client_id` (FK → clients.id)
- `charge_type` (enum: `retainer`, `one_time`)
- `amount` (numeric)
- `charge_period` (varchar YYYY-MM, nullable)
- `status` (enum: `draft`, `issued`, `paid`, `overdue`)
- `created_at` (timestamp)
- `issued_at` (timestamp, nullable)
- `paid_at` (timestamp, nullable)
- `notes` (text)

---

## 8. invoices
Externally generated fiscal documents.

**Table: invoices**
- `id` (PK, INTEGER, auto-increment; e.g., 1, 2, 3, ...)
- `charge_id` (FK → charges.id)
- `external_invoice_id` (varchar)
- `provider_name` (varchar)
- `issued_at` (timestamp)
- `sent_to_client` (boolean)
- `invoice_url` (varchar, nullable)

---

## 9. notifications
All system-generated client communications.

**Table: notifications**
- `id` (PK, INTEGER, auto-increment; e.g., 1, 2, 3, ...)
- `client_id` (FK → clients.id)
- `binder_id` (FK → binders.id, nullable)
- `type` (enum: `binder_received`, `ready_for_pickup`, `payment_reminder`, `overdue_binder`)
- `channel` (enum: `whatsapp`, `sms`, `email`)
- `sent_at` (timestamp)
- `sent_by_system` (boolean)
- `content_snapshot` (text)

---

## 10. system_settings
Centralized configuration values.

**Table: system_settings**
- `key` (PK, varchar)
- `value` (varchar)

Examples:
- `binder_max_days = 90`
- `reminder_day_1 = 75`
- `reminder_day_2 = 90`

---

## 11. Key Relationships Summary
- One client → many binders
- One client → many charges
- One charge → one invoice
- One binder → many status logs
- One client → many permanent documents

---

## 12. Schema Status
**Status: FINAL / FROZEN**

This schema is production-ready and aligned with the approved product specification.
Any structural changes require a formal change request.

---

*End of Database Schema*
