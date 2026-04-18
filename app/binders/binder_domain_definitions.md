# Binder Domain Definitions

## Domain Purpose

A **Binder** is a physical office object used to hold all physical documents that belong to a single client.
It is a logistics layer for material intake and storage inside the office.
A binder is always client-level, never business-level.

A client may own multiple businesses or activities, and material may belong to a specific business, but the physical binder itself belongs to the client.

---

## Core Domain Rules

### 1. Binder Ownership

A binder always belongs to exactly one client.
A binder never belongs directly to a business.

Material inside the binder may be:
- linked to a specific business of the client, or
- linked only to the client level.

Examples of client-level material:
- mail
- power of attorney
- ID copy
- other client-wide documents

---

### 2. Binder Number

A binder has a physical and operational identifier in the format:

`client_number / binder_sequence`

Example:
- `7/5` = client number `7`, binder sequence `5`
- when that binder is full, the next binder may be `7/25`

Rules:
- the first part is the office client number
- the second part is the binder sequence for that client
- binder numbers are never reused
- when a binder is full, a new binder is opened with the next available sequence

The binder number is a physical label used by the office.

---

### 3. Binder Lifecycle Meaning

A binder represents a **logistics time span**, not a strict accounting/reporting period.
It is a physical storage sequence that remains active until it becomes full.

### 4. Binder Period Fields

`period_start`
- set from the reporting period of the first material inserted into the binder

`period_end`
- set when the binder becomes full

Important:
- a binder does **not** necessarily contain only one reporting period
- old reporting-period material may still be inserted later into the current active binder, with a note, if no older suitable binder is available

---

## Binder Operational States

The domain requires a clear distinction between these operational meanings:

### Open Active Binder
A binder that:
- is not full
- can still receive new material
- is physically in the office

### Closed Binder Still in Office
A binder that:
- is full
- can no longer receive new material
- is still physically stored in the office
- has not yet been returned to the client

### Returned Binder
A binder that:
- was physically handed back to the client
- is no longer in office storage
- remains in system history
- its binder number must never be reused

Important:
- **"closed but still in office" is not the same as "returned"**
- `is_full` alone is not enough to represent all logistics states cleanly

---

## Intake Definition

A **BinderIntake** is a single physical material-receipt event from a client.

Examples:
- VAT material
- income tax material
- annual report material
- capital declaration material
- other office-relevant client material

Rules:
- one intake always belongs to one binder
- one intake may contain multiple material rows
- one intake may include different material types
- one intake may include material for multiple businesses of the same client
- one intake may also include client-level-only material

An intake represents a physical reception event in the office.
It is not an email event, phone event, or digital upload event.

---

## Intake Creation Rules

An intake must always be attached to a single binder.

Possible flows:
- material arrives and is inserted into an existing active binder
- material arrives and that same intake causes a new binder to be opened
- a new binder may also be opened manually by office action

If the client brings additional material later, a **new intake** is created.
The system does not merge separate physical arrivals into one intake.

If a client brings more material for the same reporting period later:
- keep separate intakes
- duplicate material rows for the same type, period, and business are allowed
- the office only needs to know that **at least some material was received**

---

## Intake Edit Rules

Intakes may be edited when mistakes happen.

Examples:
- entered under the wrong client
- entered under the wrong business
- incorrect period
- incorrect material type

Edit policy:
- adding is allowed
- correcting is allowed
- audit trail is required

If an intake is moved to another client:
- the intake data must also move to a binder belonging to the new client
- logistics ownership must stay consistent

A field-level audit trail is required for intake changes.
A full snapshot history is not required.

---

## Material Row Definition

A **BinderIntakeMaterial** is a single material row inside an intake.

Each material row must store:
- material type
- structured reporting period
- business linkage or client-level linkage
- optional note/description
- optional system-entity linkage, when required by the material type

### Material Business Rules

A material row may be:
- linked to a specific business, or
- client-level only (`business_id = null`)

If material belongs to different businesses, it must be stored in separate rows.
One row must not represent multiple businesses.

Client-level material must still have a reporting period.

---

## Reporting Period Rule

The reporting period must be a **structured field**.
It must not be stored only as free text.

Examples:
- monthly VAT: `January 2026`
- bi-monthly VAT: `January-February 2026`

This period belongs to the **material row**, not to the binder as the single source of truth.

---

## Material Type Rules

The list of material types is **closed and strict**.
The office does not need open-ended custom material types.

Examples of expected types:
- VAT
- income tax
- annual report
- capital declaration
- bookkeeping material
- client-level legal/identity material

The system should treat material type as a controlled enum.

---

## System Entity Linkage

Each material type may have at most one valid system-entity linkage kind.

Examples:
- `annual_report` material must link to a specific `annual_report`
- VAT material should link to a real VAT reporting-period entity

Rules:
- some material types require a linked domain entity
- some material types are client-level logistics only
- client-level material may still have a linked system entity if the domain requires it

This linkage is determined by material type.

---

## Old-Period Material Rule

If a client brings material for an old reporting period after a newer binder already exists:
- the office first tries to place it in the binder for that old period
- if no suitable old binder exists, the material goes into the current active binder
- a note should be stored to explain the mismatch

This confirms that binder storage is logistics-driven, not purely period-driven.

---

## Ready for Pickup Meaning

`ready_for_pickup` is a logistics/office status.
It means:
- the office finished the relevant work for the material stored in the binder(s)
- the physical binder(s) are ready to be returned to the client

Important:
- readiness may apply to **multiple binders together**, based on a reporting-period cutoff
- this is not always a purely single-binder decision

Example:
- all binders up to `January 2026` may be marked ready together
- a binder from `February 2026` may remain in office

Readiness is decided by **manual staff action**.

If new material later affects only some of those binders, readiness may be reversed only for the relevant binders.

---

## Return / Handover Rules

Returning binders to a client is a **group handover event**, not just an isolated binder status change.

A return event may include multiple binders together.

The handover event must store at least:
- who received the binders on the client side
- when the binders were handed over
- until which reporting period the binders were returned

This means the domain needs a grouped return concept, not only a per-binder `returned` flag.

---

## Practical Meaning of "At Least Some Material Was Received"

The office does not need to know document quantity.
The office does not need material completeness tracking at intake-row level.

The main question is:
- **was some material received for this type / period / business?**

Therefore:
- duplicate rows for the same type/period/business are valid
- multiple intakes for the same period are valid
- no strict merge is required
- no "complete / partial" status is required at material-row level

---

## Domain Implications for the Current Model

The current domain model is not fully accurate if it only relies on:
- a single binder status without separating "closed but still in office"
- free-text period inside material description
- single-binder return semantics

The domain requires at least these concepts:

- `Binder` as the physical client-level binder
- `BinderIntake` as the physical receipt event
- `BinderIntakeMaterial` as the material row
- `BinderStatusLog` for binder lifecycle audit
- field-level audit trail for intake/material edits
- grouped binder return / handover event for multi-binder return flows

---

## Recommended Domain Interpretation

The cleanest interpretation is:

- **Binder** = physical logistics container for one client
- **BinderIntake** = one physical material arrival
- **BinderIntakeMaterial** = one classified material row
- **Binder closed** = full, no more material enters, still in office
- **Ready for pickup** = office finished work and can return relevant binder(s)
- **Returned** = physically handed back to the client through a grouped handover event

This is the operational truth of the domain.
