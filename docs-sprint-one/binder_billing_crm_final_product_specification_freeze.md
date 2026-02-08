# Binder & Billing CRM
## Final Product Specification (Freeze)

---

## 1. Product Overview
**Binder & Billing CRM** is an internal web-based system designed for a tax advisor or a small tax office. Its primary purpose is to manage the lifecycle of **physical binders** stored in the office (up to 90 days), track client billing and collections, and maintain a digital archive of permanent client documents.

The system is intentionally minimalistic and operational, focused on solving logistical and administrative pain points without introducing unnecessary technological complexity.

**Out of Scope (Explicitly Excluded):**
- No client portal
- No scanning of ongoing accounting materials
- No time tracking or profitability by hours

---

## 2. User Roles & Permissions

### Tax Advisor (Admin)
- Full access to all system data
- View and manage financial information
- Define retainers and pricing
- View management and exception reports
- Receive critical system alerts (overdue binders, unpaid balances)

### Secretary (Operational User)
- Intake and return physical binders
- Manage binder lifecycle statuses
- Generate existing charges and invoices
- Upload and manage permanent documents
- Send system-generated client notifications
- **No access** to profitability reports or pricing configuration

---

## 3. Core Business Rules (Golden Rules)

1. **90-Day Binder Rule**
   - Each binder is tracked from its intake date
   - The system automatically calculates a 90-day threshold
   - At day 90, the binder is marked as **Overdue** and highlighted visually

2. **Warnings Without Blocking**
   - Open client debt or missing permanent documents trigger warnings
   - Binder intake is never blocked by warnings

3. **No Hard Deletions**
   - Clients, binders, charges, and invoices are never deleted
   - Records are archived or marked inactive instead

4. **Mandatory Return Confirmation**
   - Returning a binder requires entering the name of the person who collected it
   - Ensures legal and operational traceability

---

## 4. Data Architecture Highlights

- **Client vs. Binder Separation**
  - Client is a permanent entity
  - Binder is a temporary entity with defined entry and exit dates

- **Charge vs. Invoice Separation**
  - Charge represents an internal payment request
  - Invoice represents an externally generated fiscal document (via API integration)

- **Full Audit Trail**
  - Every binder status change is logged with timestamp and user reference

---

## 5. Operations & Notifications

### Notification Engine
Automated messages (WhatsApp / SMS / Email) are triggered on:
- Binder intake confirmation
- Completion of work and readiness for pickup
- 90-day overdue binder reminder

All notifications:
- Can be manually disabled
- Are logged for audit purposes

### Binder Inventory Management
A live "Binder Inventory" view provides real-time visibility of all binders currently stored in the office, color-coded by duration:
- Green: under 60 days
- Orange: 60–90 days
- Red: over 90 days

---

## 6. Core Screens (Textual Wireframe)

### 6.1 Dashboard – Command Center
- Logistic widgets:
  - Binders currently in office
  - Binders ready for pickup
  - Overdue binders (90+ days)
  - Binders received but not yet reported
- Financial widget (Admin only):
  - Total outstanding balances
  - Monthly retainers pending generation
- Global search: client name or binder number

---

### 6.2 Binder Intake / Return – Secretary Station

**Binder Intake Flow**
- Search by binder number or client name
- Single action: "Receive Binder"
- Display warnings:
  - Missing permanent documents
  - Open client balance
- Optional: send intake confirmation via WhatsApp

**Binder Return Flow**
- Search binder
- Action: "Return Binder"
- Mandatory field: name of pickup person
- Send return confirmation notification

---

### 6.3 Client 360° Profile
- Client identification and binder number
- Tabs:
  - Reporting status history
  - Permanent documents checklist
  - Financial overview (charges & invoices)
  - Binder movement history (full audit)

---

## 7. Approved Notification Templates

**Binder Received**
> Hi [Client Name], your binder (No. [X]) has been safely received at our office. We will update you once processing is complete.

**Ready for Pickup**
> Good news! The reporting process is complete and your binder is ready for pickup. We look forward to seeing you.

**90-Day Reminder**
> Your binder has been stored at our office for an extended period. Please arrange pickup at your earliest convenience.

---

## 8. Development Roadmap (High-Level)

**Phase 1:** Database setup and client management

**Phase 2:** Binder lifecycle module and 90-day logic

**Phase 3:** Billing module and invoice integration

**Phase 4:** Notification engine (WhatsApp / SMS)

---

## 9. Specification Status
**Status: FREEZE**

This specification is complete, internally consistent, and production-ready.
Any further changes are considered formal change requests.

---

*End of Specification*

