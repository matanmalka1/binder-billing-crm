# Domain Model Review Summary

Last updated: 2026-04-19
Scope: current-state analysis of the existing internal workflow system for Israeli bookkeeping / tax advisory offices.

## 1. Current-State Model

### What the system is doing today

- `Client` is effectively the legal/tax entity.
- `Business` is an operational activity under a `Client`.
- `Binder` is a client-scoped physical/logistics container.
- `VatWorkItem` is a client-scoped VAT workflow item.
- `AnnualReport` is a client-scoped annual tax workflow item.
- `TaxDeadline` is a client-scoped tax obligation.
- `Reminder` is a client-anchored operational reminder with optional business context.
- `PermanentDocument` is client-scoped or business-scoped, optionally linked to an annual report.
- `Timeline` is a client-scoped operational event feed.
- `EntityAuditLog` is a technical cross-entity audit trail.
- `Dashboard` is a derived aggregation view only.

### Important implemented meaning

- `Client != person`
- `Client ~= legal entity + CRM record + some person/contact fields`
- `Business != legal entity`
- `Business ~= operational activity under one legal entity`

## 2. Structural Findings

### Finding 1: `Client` is a mixed entity

`Client` currently mixes at least three concepts:

- `Person`
  - `full_name`
  - `phone`
  - `email`
  - `address_*`
- `LegalEntity`
  - `id_number`
  - `id_number_type`
  - `entity_type`
  - `vat_reporting_frequency`
  - `vat_exempt_ceiling`
  - `advance_rate`
  - `advance_rate_updated_at`
- `Office CRM Record`
  - `status`
  - `office_client_number`
  - `accountant_id`
  - `notes`

Severity: High

### Finding 2: Missing `Person`

- There is no separate entity for the human behind multiple legal entities.
- A person with a sole trader + company + another company does not exist as one first-class object.
- The system can represent multiple legal entities, but not their common human owner as an aggregate.

Severity: High

### Finding 3: `Business` is operational, not legal

- `Business` does not hold its own legal identity.
- It has no independent:
  - ID number
  - legal type
  - VAT profile
  - tax profile
- Therefore `Business` cannot represent a second legal entity under one `Client`.

Severity: Not a bug by itself, but a hard domain boundary that must stay explicit.

### Finding 4: `Client = LegalEntity` is the real implemented truth

This is the practical model that emerged from the code:

- `Client = LegalEntity`
- `Business = OperationalActivity under LegalEntity`
- `Person` is absent

This matters because several names in the product language may imply otherwise.

Severity: High if terminology in product thinking assumes otherwise.

## 3. Cross-Domain Drift Findings

### Finding 5: Snapshot Drift on `AnnualReport`

- `AnnualReport.client_type` is a snapshot at creation time.
- `Client.entity_type` can later change.
- Existing annual reports are not reconciled.
- No warning or mismatch detector exists.

Possible outcome:

- annual report continues using the wrong filing profile silently

Severity: High

### Finding 6: Snapshot Drift on `TaxDeadline`

When `entity_type` changes:

- `generate_client_obligations()` runs again
- `DeadlineGeneratorService` does not update or delete old deadlines
- it only creates new ones when `(client_id, deadline_type, due_date)` does not already exist

Possible outcome:

- old deadlines remain
- new deadlines can be created beside them
- one logical obligation can produce multiple active deadlines

Severity: High

### Finding 7: Snapshot Drift propagates into `Reminder`

- reminders linked to old deadlines remain linked to those deadlines
- no global reconciliation runs after `entity_type` change
- no warning exists

Possible outcome:

- reminders continue pointing to obsolete deadlines

Severity: High

### Finding 8: Drift is system-wide, not local

Changing `entity_type` can create silent inconsistency across:

- `AnnualReport`
- `TaxDeadline`
- `Reminder`

Possible combined state:

- wrong annual-report type
- duplicate deadline set
- reminders on obsolete deadlines

Severity: Critical from a workflow-integrity perspective

## 4. Reminder Findings

### Finding 9: `CUSTOM` reminder has the wrong scope

- `CUSTOM` reminder requires `business_id`
- many office reminders are naturally client-level, not business-level
- there is no client-level custom reminder path

Example of unsupported natural use case:

- "Call Yossi about signature document"

Severity: Medium

### Finding 10: No automatic fallback business selection

- no default-business resolution exists
- no "pick first business" heuristic exists
- user must provide `business_id`

Practical risk:

- staff may choose an arbitrary business just to satisfy validation

Severity: Medium

### Finding 11: Client close/freeze does not cancel reminders

When client status becomes `closed` or `frozen`:

- reminders are not canceled automatically
- no `cancel_pending_by_client` policy exists
- only targeted cancellation exists for selected source entities such as charge/deadline

Possible outcome:

- daily job can continue dispatching reminders for a closed/frozen client

Severity: High

## 5. Document Findings

### Finding 12: Document linking is asymmetric

- `PermanentDocument` can link to `annual_report_id`
- there is no direct link to `VatWorkItem`

Current meaning:

- annual-report process can own documents explicitly
- VAT process cannot

Assumption:

- this may be intentional because VAT relies on invoices rather than permanent documents
- but no explicit business justification was found in the code/docs

Severity: Medium if VAT workflow requires process-level document ownership

## 6. Onboarding Findings

### Finding 13: Onboarding creates multiple entities automatically

Opening a new client creates automatically:

- `Client`
- first `Business`
- initial `Binder`
- generated `TaxDeadline` rows
- generated `AnnualReport` rows

This is implemented inside one request-scoped transaction.

Assessment:

- transactional behavior is mostly clean
- not a structural bug

Severity: Informational

### Finding 14: First `Business` is structurally mandatory

Every created client gets a first business through the create flow.

Assumption:

- this can be a placeholder if the office conceptually thinks in legal entities first and operational activities second

What is unclear:

- whether the first business always corresponds to a real operational activity
- or whether it exists partly because downstream workflows expect at least one business

Severity: Medium ambiguity

## 7. Delete / Archive Findings

### Finding 15: Soft delete exists on `Client`

- `Client` supports soft delete
- restore is supported

This part is implemented clearly.

Severity: Informational

### Finding 16: No lifecycle cascade from `Client`

Soft-deleting a client does not imply consistent downstream lifecycle handling.

Observed:

- no broad cascade delete/archive/disable flow
- businesses are not deleted automatically
- reminders/deadlines/binders are not centrally archived via client lifecycle

Possible outcome:

- dependent entities can remain operational after the parent client is deleted

Severity: High

## 8. RBAC Findings

### Finding 17: RBAC exists, but critical actions are under-protected

Current roles:

- `advisor`
- `secretary`

No stronger role above `advisor` exists in the backend model.

Severity: Informational

### Finding 18: `entity_type` update is too open

- `PATCH /clients/{id}` is available to both `advisor` and `secretary`
- `entity_type` is included in that update path
- changing it can impact annual reports, deadlines, and reminders indirectly

Possible outcome:

- structurally dangerous change can be triggered by a non-senior operational role

Severity: High

## 9. Binder / Intake Findings

### Finding 19: Binder itself is conceptually clean

- binder is client-scoped
- logistics-driven, not tax-period-driven
- multiple binders can exist over time per client

Assessment:

- concept is internally coherent

Severity: Informational

### Finding 20: Material-to-business attribution is manual

- `BinderIntakeMaterial.business_id` is user-entered
- no automatic inference exists
- validation only checks ownership consistency

Risk:

- wrong or missing business attribution depends on user discipline

Assessment:

- acceptable if intentional
- should be treated as a manual-classification workflow, not an automated one

Severity: Low to Medium depending on operational expectations

## 10. VAT Findings

### Finding 21: VAT work item creation is manual, not automatic

`VatWorkItem` is created through explicit intake/work-item creation flow:

- `POST /api/v1/vat/work-items`

Not found:

- no automatic generator comparable to annual reports or tax deadlines

Implication:

- VAT obligations are auto-generated as deadlines
- VAT operational work items are created manually when office workflow starts
- no automatic trigger creates a `VatWorkItem` when a VAT `TaxDeadline` is generated

Severity: Informational

### Finding 22: VAT scoping is internally consistent

- work item is client-scoped
- invoice may optionally tag `business_activity_id`
- validation enforces that tagged business belongs to the same client
- totals are aggregated automatically from invoices

Assessment:

- this area is structurally coherent

Severity: Informational

### Finding 23: `TaxDeadline` and `VatWorkItem` are separate worlds

There is no direct domain relationship between VAT `TaxDeadline` and `VatWorkItem`.

Observed:

- no FK from `TaxDeadline` to `VatWorkItem`
- no FK from `VatWorkItem` to `TaxDeadline`
- the practical join is only `client_id + period`
- VAT query responses expose deadline-style fields as computed enrichment, not as a linked entity

Possible outcome:

- a VAT deadline can exist without a matching VAT work item
- filing a VAT work item does not inherently complete the matching deadline
- a VAT deadline can remain open after VAT filing unless some separate logic handles it

Severity: High

### Finding 24: VAT sync is one-way and weak

The only meaningful bridge found between VAT work items and VAT deadlines is in overdue-compliance background processing.

Observed:

- background job finds overdue/unfiled VAT work items
- then looks up a VAT deadline by `client_id + period`
- then creates reminder records keyed by `tax_deadline_id`
- no equivalent work-item status transition closes/reopens VAT deadlines

Assessment:

- this is not lifecycle synchronization
- this is only operational reminder generation

Severity: High

## 11. Annual Report Findings

### Finding 25: `AnnualReport` has a full lifecycle after auto-creation

After onboarding creates the report, its lifecycle is managed through explicit status transitions.

Implemented statuses:

- `not_started`
- `collecting_docs`
- `docs_complete`
- `in_preparation`
- `pending_client`
- `submitted`
- `amended`
- `accepted`
- `assessment_issued`
- `objection_filed`
- `closed`

Assessment:

- annual report lifecycle is much more explicitly modeled than VAT lifecycle

Severity: Informational

### Finding 26: Annual report status transitions are explicit and role-gated

Observed:

- transitions run through a dedicated status service
- valid transitions are enforced centrally
- readiness is checked before `submitted`
- status history is append-only
- status-change routes are advisor-only

Assessment:

- this is one of the cleaner lifecycle implementations in the current system

Severity: Informational

### Finding 27: `AnnualReport` and annual `TaxDeadline` have behavioral sync but no hard link

Observed:

- no FK exists between `AnnualReport` and `TaxDeadline`
- on entering filed statuses, annual-report logic completes matching annual deadlines
- on leaving filed statuses, it reopens them and may recreate reminders
- matching is done by client and due-date year window, not by explicit relationship

Implication:

- annual-report sync is behaviorally stronger than VAT sync
- but it still depends on logical lookup rather than a durable domain link

Severity: Medium to High

### Finding 28: Annual deadline sync is not one-to-one

If more than one `ANNUAL_REPORT` deadline exists for the same client and tax year, status sync operates on all of them.

Observed:

- deadline sync loads all matching annual deadlines for the client in `tax_year + 1`
- it loops over all matches and completes/reopens each one
- deadline uniqueness is effectively deduped only by `(client_id, deadline_type, due_date)` at generator time
- changing filing profile can produce another annual deadline with a different due date

Possible outcome:

- one annual report can close multiple annual deadlines
- one rollback/amend flow can reopen multiple annual deadlines
- the sync is many-to-many in behavior, even though business meaning suggests one-to-one

Severity: High

## 12. Binder / Intake Findings

### Finding 29: Binder lifecycle is explicit and operationally clean

Implemented statuses:

- `in_office`
- `closed_in_office`
- `ready_for_pickup`
- `returned`

Observed:

- first binder is created automatically on onboarding
- later lifecycle transitions are manual office actions
- both `advisor` and `secretary` can perform binder lifecycle actions
- status logs are recorded for transitions

Assessment:

- binder lifecycle is explicit and understandable

Severity: Informational

### Finding 30: Returning a binder does not open a new binder

When a binder is returned to the client:

- status becomes `returned`
- `returned_at` is set
- `period_end` may be closed if it was still null
- no new binder is created automatically

A new binder is opened only through the intake flow:

- when no active `in_office` binder exists
- or when intake is called with `open_new_binder=true`

Assessment:

- this is a deliberate operational model, not an automatic lifecycle continuation

Severity: Informational
## 13. Dashboard Findings

### Finding 31: Dashboard has no state of its own

- dashboard is pure aggregation/derived view
- no dedicated persistent tables

Assessment:

- structurally clean

Severity: Informational

## 14. Entry-Point Findings

### Finding 32: `Client` is the primary anchor, but not the only API entry point

Observed:

- many workflows are nested directly under `/clients/{client_id}/...`
- many other entities are created through top-level routes carrying `client_id` in the request body
- many read/update flows later operate by direct entity id (`report_id`, `binder_id`, `deadline_id`, `work_item_id`)

Implication:

- `Client` is the primary business anchor for most entities
- but redesigning `Client` cannot assume all workflows enter through client-nested routes

Severity: Architectural note

## 15. Consolidated Problem List

### High / Critical

1. `Client` mixes person, legal-entity, and CRM-record concerns.
2. `Person` entity is missing completely.
3. Snapshot drift on `AnnualReport`.
4. Snapshot drift on `TaxDeadline`.
5. Snapshot drift propagates into `Reminder`.
6. Drift is silent and cross-domain.
7. Client close/freeze does not cancel reminders.
8. No lifecycle cascade from client delete/archive.
9. `entity_type` update is allowed to `secretary`.
10. VAT `TaxDeadline` and `VatWorkItem` are separate domains with no hard lifecycle link.
11. Annual report deadline sync is many-to-many in behavior when duplicate annual deadlines exist.

### Medium

12. `CUSTOM` reminder is forced into business scope.
13. No fallback/default resolution for custom reminder scope.
14. Document linking is asymmetric: annual-report link exists, VAT link does not.
15. First business on onboarding may be a required placeholder rather than a clean domain object.
16. Annual report deadline sync is still logical, not relation-based, even though behavior is richer than VAT.

### Low / Informational

17. Binder material business attribution is fully manual.
18. VAT work-item creation is manual while deadlines are generated automatically.
19. Binder return does not imply opening a successor binder.
20. Dashboard is a pure derived view.

## 16. Flow Summary

| Flow | Healthy? | Main issue |
|---|---|---|
| Onboarding | Mostly yes | First `Business` may be a placeholder rather than a clean domain object |
| `entity_type` update | No | Drift across `AnnualReport`, `TaxDeadline`, and `Reminder` |
| Client close/delete | No | No cascade lifecycle policy; reminders can remain active |
| VAT lifecycle | No | Separate from `TaxDeadline`; work item is manual and not synced |
| Annual report lifecycle | Partially | Better than VAT, but sync to deadlines is logical and can fan out to duplicates |
| Binder lifecycle | Yes | Operationally clean, but successor binder opening is manual/intake-driven |

## 17. Remediation Layers

### Layer 1: Foundation

Must precede the rest.

- Findings 1-2 come first
- the current `Client` model should be split into distinct concepts
- a dedicated `Person` layer should be introduced

Why:

- every other workflow currently depends on `Client`
- fixing downstream integrity on top of a mixed root entity would harden the wrong model

### Layer 2: Integrity

Primary targets:

- drift findings around structural regeneration
- VAT deadline/work-item separation
- annual deadline sync multiplicity

Why:

- these are the main sources of silent bad data and broken domain truth

### Layer 3: Lifecycle

Primary targets:

- close/delete cascades
- reminders and other operational children remaining active past parent closure

Why:

- this layer prevents inconsistent "still operational after closure" states

### Layer 4: Permissions and UX

Primary targets:

- dangerous structural edits exposed too broadly
- workflow affordance gaps

Why:

- important, but secondary to fixing the domain truth itself

### Layer 5: Nice to Have

Primary target:

- process-level document ownership for VAT if the product needs it

Why:

- useful, but not foundational

## 18. Current Architectural Tensions

### Tension A

The system wants `Client` to be the legal entity.

But it also stores:

- person/contact fields
- office record fields

This creates naming confusion and weak boundaries.

### Tension B

The system supports regeneration of downstream obligations after client changes.

But it does not support reconciliation of already-created downstream entities.

This makes "regeneration" unsafe for mutable structural fields such as `entity_type`.

### Tension C

Some workflows are client-scoped by law or by filing logic.

But product needs sometimes appear person-scoped.

Without a `Person` layer, the product is forced to overload `Client` and `Business`.

### Tension D

Annual-report lifecycle already shows that the system wants stronger obligation-to-work-item coordination.

But VAT still operates with:

- generated deadlines
- manual work-item creation
- no hard relation
- no bidirectional sync

This creates different integrity guarantees for two conceptually parallel obligation flows.

## 19. Open Questions Requiring Product Decisions

1. Should `entity_type` be mutable at all on an existing client?
2. If yes, should it trigger an explicit migration/reclassification workflow rather than silent regeneration?
3. Should custom reminders support pure client-level scope?
4. Should deleting/closing/freezing a client trigger downstream lifecycle policies consistently?
5. Is the first business a real operational concept, or a technical placeholder required by current flows?
6. Does VAT workflow require direct document ownership at the work-item level?
7. Should VAT be aligned with annual reports by introducing a real obligation-to-work-item relationship?
8. Should annual report sync be made one-to-one by introducing an explicit annual-obligation identity rather than deadline lookup by date window?

## 20. Target Decision State

This section captures the agreed target model after the review. It is the required state for Layers 1-3 and should be treated as the decision baseline for future implementation work.

### 20.1 Layer 1: Target Model

The current `Client` concept must be split into separate identity and operational entities.

#### Identity Layer

- `Person`
- `LegalEntity`
- `PersonLegalEntityLink`

#### Operational Layer

- `ClientRecord`
  - `legal_entity_id` → FK to `LegalEntity`
  - this is the primary workflow anchor

#### Business Layer

- `Business`
  - belongs to `LegalEntity`, not to `ClientRecord`
  - represents operational activity under the legal entity
  - may be referenced by workflow entities only as attribution/tagging

### 20.2 Required Entities

#### `Person`

- `id`
- `first_name`
- `last_name`
- `national_id`
- `phone`
- `email`
- `address_*`

#### `LegalEntity`

- `id`
- `id_number`
- `id_number_type`
- `entity_type`
- `vat_reporting_frequency`
- `vat_exempt_ceiling`
- `advance_rate`

#### `ClientRecord`

- `id`
- `legal_entity_id`
- `office_client_number`
- `accountant_id`
- `notes`
- `status`

#### `PersonLegalEntityLink`

- `person_id`
- `legal_entity_id`
- `role`
  - `owner`
  - `authorized_signatory`
  - `controlling_shareholder`

#### `Business`

- `id`
- `legal_entity_id`
- business operational fields only

### 20.3 Anchor Rules

#### Workflow entities use `client_record_id` by default

- `VatReport`
- `AnnualReport`
- `TaxDeadline`
- `Binder`
- `Reminder`
- `Document` in most operational cases

#### Direct `legal_entity_id` is reserved for explicit exceptions

- `Business`
- `PersonLegalEntityLink`
- permanent legal identity documents
- external integrations that operate on the legal entity itself

### 20.4 Business Invariant

If a workflow entity carries `business_id`, the following invariant must be enforced:

`workflow_entity.business_id -> business.legal_entity_id`
`==`
`workflow_entity.client_record_id -> client_record.legal_entity_id`

Meaning:

- a business referenced from a workflow entity must belong to the same legal entity as the workflow entity's `ClientRecord`

### 20.5 Layer 2: Integrity Model

The system must stop relying on logical synchronization by `client_id + period/date range`.

The required direction is:

- strong domain identity
- uniqueness by obligation key
- sync by domain key, not by derived due date

#### Required uniqueness

##### `AnnualReport`

- unique: `(client_record_id, tax_year)`

##### `TaxDeadline`

- annual deadline unique: `(client_record_id, deadline_type, tax_year)`
- VAT deadline unique: `(client_record_id, deadline_type, period)`

This replaces the current deduplication by `(client_id, deadline_type, due_date)`.

##### `VatReport`

- unique: `(client_record_id, period)`

### 20.6 Required Sync Rules

#### Annual flow

- sync between `AnnualReport` and `TaxDeadline` must use `(client_record_id, tax_year)`
- never use due-date window lookup as the identity mechanism

#### VAT flow

- sync between `VatReport` and `TaxDeadline` must use `(client_record_id, period)`
- never use `due_date` as the primary join identity

### 20.7 Preferred Future Model

The ideal future model introduces an explicit `Obligation` entity:

- `client_record_id`
- `obligation_type`
  - `annual_report`
  - `vat`
  - `advance`
- `tax_year` or `period`
- unique: `(client_record_id, obligation_type, period)`

Then:

- `AnnualReport -> obligation_id`
- `TaxDeadline -> obligation_id`
- `VatReport -> obligation_id`

This is preferred over a direct FK from `AnnualReport` to `TaxDeadline`, because the real missing concept is shared obligation identity, not only linkage.

### 20.8 Layer 3: Lifecycle Policy

Client closure must not be implemented as blind cascade delete.

The required model is:

- explicit lifecycle policy by entity type
- preserved history
- blocked creation of new workflow on closed records

#### On `ClientRecord` close

##### Cancel automatically

- active `Reminder`

##### Freeze / archive

- open `TaxDeadline` -> `canceled`
- non-final `VatReport` -> `canceled` / `archived`
- non-final `AnnualReport` -> `canceled`
- open `Binder` -> `archived_in_office`

##### Preserve unchanged

- `Document`
- `EntityAuditLog`
- `StatusHistory`
- `PersonLegalEntityLink`
- `Business`

##### Block

- creation of new workflow entities on a closed `ClientRecord`

### 20.9 Missing Terminal States

The lifecycle policy above cannot be implemented cleanly with the current enums.

Required additions:

- `TaxDeadline` -> `canceled`
- `VatReport` -> `canceled`, `archived`
- `AnnualReport` -> `canceled`
- `Binder` -> `archived_in_office`

## 21. Recommended Next Step

The immediate next step after this document is not more domain analysis.

It should be:

1. freeze these decisions as the implementation baseline
2. derive an execution plan starting from Layer 1
3. defer Layer 4 permission/UX refinement until the Layer 1-3 model is stable
