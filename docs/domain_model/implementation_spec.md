# Layer 1 Implementation Spec

Last updated: 2026-04-19
Scope: implementation planning for Layer 1 only.

This document translates the agreed Layer 1 domain decisions into an implementation plan based on the current backend code.

Working assumptions:

- `docs/domain_model/DOMAIN_MODEL_REVIEW_SUMMARY.md` is the source of truth.
- This document does not authorize code changes by itself.
- Layer 2 and Layer 3 topics are out of scope except where they create execution dependencies or migration risk.

## 1. Layer 1 Goal

Implement the following structural split without breaking the system in one step:

- split `Client` into `Person`, `LegalEntity`, `ClientRecord`, `PersonLegalEntityLink`
- move `Business` ownership from `Client` to `LegalEntity`
- move workflow entities from `client_id` to `client_record_id`

Target ownership model:

- `Person`
  - physical person
- `LegalEntity`
  - legal and tax identity
- `ClientRecord`
  - office CRM and workflow anchor
- `PersonLegalEntityLink`
  - relationship between person and legal entity
- `Business`
  - operational activity under `LegalEntity`

## 2. Current Code Reality

The current code does not match the desired Layer 1 model.

Observed implementation truth:

- `Client` is still the active legal/workflow anchor in practice
- `Business` still belongs to `Client`
- workflow entities still anchor on `client_id`

Primary examples:

- [app/clients/models/client.py](/Users/matanmalka/Desktop/backend/app/clients/models/client.py:18)
  - `Client` contains person fields, legal fields, CRM fields, and lifecycle state
- [app/businesses/models/business.py](/Users/matanmalka/Desktop/backend/app/businesses/models/business.py:36)
  - `Business.client_id -> clients.id`
- [app/annual_reports/models/annual_report_model.py](/Users/matanmalka/Desktop/backend/app/annual_reports/models/annual_report_model.py:25)
  - `AnnualReport.client_id`
- [app/vat_reports/models/vat_work_item.py](/Users/matanmalka/Desktop/backend/app/vat_reports/models/vat_work_item.py:32)
  - `VatWorkItem.client_id`
- [app/tax_deadline/models/tax_deadline.py](/Users/matanmalka/Desktop/backend/app/tax_deadline/models/tax_deadline.py:56)
  - `TaxDeadline.client_id`
- [app/binders/models/binder.py](/Users/matanmalka/Desktop/backend/app/binders/models/binder.py:41)
  - `Binder.client_id`

Important mismatch to keep explicit:

- the review summary correctly states that `Client` is a mixed entity
- some code comments and repository docstrings still describe `Client` as identity-only
- that description is not accurate for the current implementation

## 3. New Tables Required

Layer 1 requires four new tables.

### 3.1 `persons`

Purpose:

- represent the physical individual behind one or more legal entities

Suggested minimum fields:

- `id`
- `full_name`
- `first_name`
- `last_name`
- `national_id`
- `phone`
- `email`
- `address_street`
- `address_building_number`
- `address_apartment`
- `address_city`
- `address_zip_code`
- `created_at`
- `updated_at`

Notes:

- `full_name` should exist even if name splitting is imperfect during backfill
- Layer 1 should not require perfect person de-duplication

### 3.2 `legal_entities`

Purpose:

- become the source of truth for legal and tax identity

Suggested minimum fields:

- `id`
- `id_number`
- `id_number_type`
- `entity_type`
- `vat_reporting_frequency`
- `vat_exempt_ceiling`
- `advance_rate`
- `advance_rate_updated_at`
- `created_at`
- `updated_at`

Notes:

- this table receives the legal/tax part of current `Client`

### 3.3 `client_records`

Purpose:

- become the office-facing CRM and workflow anchor

Suggested minimum fields:

- `id`
- `legal_entity_id`
- `office_client_number`
- `accountant_name`
- `status`
- `notes`
- `created_by`
- `created_at`
- `updated_at`
- `deleted_at`
- `deleted_by`
- `restored_at`
- `restored_by`

Notes:

- this table receives the CRM/lifecycle part of current `Client`
- Layer 1 workflows should anchor here

### 3.4 `person_legal_entity_links`

Purpose:

- link `Person` to one or more `LegalEntity` rows with a role

Suggested minimum fields:

- `id`
- `person_id`
- `legal_entity_id`
- `role`
- `created_at`

Notes:

- Layer 1 can keep role vocabulary small
- do not block the migration on perfect ownership semantics

## 4. Existing Tables Affected

### 4.1 Primary structural tables

- `clients`
- `businesses`

### 4.2 Primary workflow tables

- `annual_reports`
- `vat_work_items`
- `tax_deadlines`
- `binders`
- `advance_payments`

### 4.3 Secondary operational tables

- `reminders`
- `charges`
- `notifications`
- `correspondence`
- `signature_requests`
- `authority_contacts`
- `binder_handovers`
- `permanent_documents`

### 4.4 Secondary query/report surfaces

- search
- timeline
- dashboard
- export/report builders

## 5. FK Changes Required

### 5.1 `Business`

Current:

- `businesses.client_id -> clients.id`

Target:

- `businesses.legal_entity_id -> legal_entities.id`

### 5.2 Workflow entities

Current:

- workflow tables use `client_id`

Target:

- workflow tables use `client_record_id`

Tables in this group:

- `annual_reports`
- `vat_work_items`
- `tax_deadlines`
- `binders`
- `advance_payments`
- `reminders`
- `charges`
- `notifications`
- `correspondence`
- `signature_requests`
- `authority_contacts`
- `binder_handovers`

### 5.3 `business_id` validations

Many services currently validate business ownership with:

- `business.client_id == client_id`

Target validation:

- `business.legal_entity_id == client_record.legal_entity_id`

This affects service logic even where the `business_id` column itself does not change.

## 6. Impact Matrix

| Entity / Area | Current Owner | Target Owner | DB Change | Code Risk |
|---|---|---|---|---|
| `Client` | monolith | split into 3 entities | new tables, eventual legacy deprecation | critical |
| `Business` | `client_id` | `legal_entity_id` | add new FK, backfill, later remove old FK | critical |
| `AnnualReport` | `client_id` | `client_record_id` | add new FK and unique/index migration | critical |
| `VatWorkItem` | `client_id` | `client_record_id` | add new FK and unique/index migration | critical |
| `TaxDeadline` | `client_id` | `client_record_id` | add new FK and query migration | critical |
| `Binder` | `client_id` | `client_record_id` | add new FK and repository migration | critical |
| `AdvancePayment` | `client_id` | `client_record_id` | add new FK and analytics migration | high |
| `Reminder` | `client_id` | `client_record_id` | add new FK and factory/query migration | high |
| `Charge` | `client_id` | `client_record_id` | add new FK and service migration | high |
| `Notification` | `client_id` | `client_record_id` | add new FK and dispatch/query migration | medium |
| `Correspondence` | `client_id` | `client_record_id` | add new FK and ownership validation rewrite | high |
| `SignatureRequest` | `client_id` | `client_record_id` | add new FK and query rewrite | high |
| `AuthorityContact` | `client_id` | `client_record_id` | add new FK and list/count query rewrite | medium |
| `BinderHandover` | `client_id` | `client_record_id` | add new FK and history rewrite | medium |
| `PermanentDocument` | `client_id` | undecided between `client_record_id` and mixed ownership | requires explicit decision | high |

## 7. Main Modules That Will Break

### 7.1 Client creation and update

- [app/clients/services/create_client_service.py](/Users/matanmalka/Desktop/backend/app/clients/services/create_client_service.py:10)
- [app/clients/services/client_service.py](/Users/matanmalka/Desktop/backend/app/clients/services/client_service.py:24)
- [app/clients/api/clients.py](/Users/matanmalka/Desktop/backend/app/clients/api/clients.py:62)
- [app/clients/repositories/client_repository.py](/Users/matanmalka/Desktop/backend/app/clients/repositories/client_repository.py:13)

Reason:

- these modules assume one `Client` create/update flow creates the primary domain anchor

### 7.2 Onboarding flow

- [app/clients/services/client_service.py](/Users/matanmalka/Desktop/backend/app/clients/services/client_service.py:81)
- [app/binders/services/client_onboarding_service.py](/Users/matanmalka/Desktop/backend/app/binders/services/client_onboarding_service.py:14)
- `generate_client_obligations` flow invoked from `ClientService`

Reason:

- binder opening and obligation generation currently depend on `client.id`

### 7.3 Business ownership and guards

- [app/businesses/services/business_service.py](/Users/matanmalka/Desktop/backend/app/businesses/services/business_service.py:18)
- [app/businesses/repositories/business_repository.py](/Users/matanmalka/Desktop/backend/app/businesses/repositories/business_repository.py:16)
- `client_businesses_router`
- every service that checks `business.client_id`

Reason:

- ownership checks must switch from legacy `Client` equality to legal-entity lineage

### 7.4 Workflow creation and querying

- [app/annual_reports/services/create_service.py](/Users/matanmalka/Desktop/backend/app/annual_reports/services/create_service.py:27)
- [app/tax_deadline/services/deadline_generator.py](/Users/matanmalka/Desktop/backend/app/tax_deadline/services/deadline_generator.py:16)
- [app/vat_reports/services/intake.py](/Users/matanmalka/Desktop/backend/app/vat_reports/services/intake.py:39)
- binder repositories and APIs
- reminders factory/query modules

Reason:

- uniqueness, ownership, and lookup logic all depend on `client_id`

### 7.5 Cross-cutting query surfaces

- `app/search/services/*`
- `app/timeline/services/*`
- `app/dashboard/services/*`
- `app/reports/services/*`

Reason:

- these surfaces join and enrich on `Client.full_name`, `Client.status`, and `Client.office_client_number`

## 8. Migration Strategy

Layer 1 should be executed with a compatibility-first migration strategy.

Do not attempt a big-bang replacement.

### 8.1 Batch A: foundation

Add new tables only:

- `persons`
- `legal_entities`
- `client_records`
- `person_legal_entity_links`

No behavioral change yet.

### 8.2 Batch B: transition columns

Add nullable transition columns:

- `businesses.legal_entity_id`
- `<workflow_table>.client_record_id` for all workflow tables in scope

Do not remove old columns in this batch.

### 8.3 Batch C: data backfill

Backfill mapping:

- each legacy `Client` creates one `LegalEntity`
- each legacy `Client` creates one `ClientRecord`
- optionally create one `Person` when backfill confidence is sufficient
- create `PersonLegalEntityLink` only where ownership can be inferred safely

Then backfill:

- `businesses.legal_entity_id`
- all new `client_record_id` columns

### 8.4 Batch D: repository compatibility

Introduce compatibility behavior in repositories/services:

- dual-read where needed
- write to new fields
- resolve old `client_id` route inputs to `client_record_id`

This is the batch that makes downstream service migration possible without changing every API at once.

### 8.5 Batch E: ownership cut

Move business logic to `legal_entity_id`.

Required updates:

- business repositories
- business services
- ownership guard helpers across domains

### 8.6 Batch F: primary workflow cut

Move the highest-risk workflow domains first:

- `TaxDeadline`
- `AnnualReport`
- `VatWorkItem`
- `Binder`
- `AdvancePayment`

Reason:

- onboarding and obligation generation depend on them

### 8.7 Batch G: secondary domain cut

Then migrate:

- `Reminder`
- `Charge`
- `Notification`
- `Correspondence`
- `SignatureRequest`
- `AuthorityContact`
- `BinderHandover`
- `PermanentDocument` if ownership decision is closed

### 8.8 Batch H: query/report cut

Update:

- search
- timeline
- dashboard
- exports
- reporting services

### 8.9 Batch I: hard cutover

Only after code is stable on the new model:

- enforce `NOT NULL`
- switch FK constraints fully
- migrate unique indexes to new owner columns
- remove legacy columns and legacy repository paths

## 9. Backfill Rules

### 9.1 Legacy `Client -> LegalEntity`

Use current legal/tax fields from `clients`:

- `id_number`
- `id_number_type`
- `entity_type`
- `vat_reporting_frequency`
- `vat_exempt_ceiling`
- `advance_rate`
- `advance_rate_updated_at`

### 9.2 Legacy `Client -> ClientRecord`

Use current CRM/lifecycle fields from `clients`:

- `office_client_number`
- `accountant_name`
- `status`
- `notes`
- `created_by`
- `created_at`
- `updated_at`
- `deleted_at`
- `deleted_by`
- `restored_at`
- `restored_by`

### 9.3 Legacy `Client -> Person`

Recommended conservative rule:

- create `Person` automatically only when the row clearly represents a natural person
- at minimum, individual `id_number_type` is a candidate

Do not force company rows into synthetic persons during the first cut unless the business explicitly wants placeholder persons.

### 9.4 `PersonLegalEntityLink`

Recommended conservative rule:

- create links only where person identity is strong enough
- avoid speculative ownership backfill for company entities

Layer 1 should succeed even if some legal entities initially have no person link.

## 10. Compatibility Strategy

### 10.1 API compatibility

Keep external routes stable during most of Layer 1:

- continue accepting `/clients/{client_id}` where possible
- translate internally to `client_record_id`

Reason:

- route changes are not required to land the domain split
- API churn is avoidable during the schema migration phase

### 10.2 Service compatibility

Services should migrate in this order:

1. resolve `ClientRecord`
2. derive `LegalEntity`
3. validate `Business` against `LegalEntity`
4. perform workflow operation on `client_record_id`

### 10.3 Repository compatibility

Add temporary helpers such as:

- `resolve_client_record_id_from_legacy_client_id`
- `resolve_legal_entity_id_from_legacy_client_id`
- `get_client_record_or_raise`
- `get_legal_entity_for_client_record_or_raise`

These should be transitional and removed after hard cutover.

## 11. Risks

### 11.1 Onboarding transaction risk

Current onboarding still assumes:

- create `Client`
- create first `Business`
- create initial `Binder`
- generate deadlines and annual reports

This currently happens inside one flow and depends on legacy `client.id`.

Primary impact area:

- [app/clients/services/client_service.py](/Users/matanmalka/Desktop/backend/app/clients/services/client_service.py:81)

### 11.2 Ownership validation drift

Current validations compare:

- `business.client_id` against request `client_id`

After Layer 1 that logic becomes wrong even if the code still runs.

### 11.3 Hidden joins on `Client`

Many queries use `Client` as the source for:

- display name
- office client number
- status
- id number

Those fields will be split across:

- `Person`
- `LegalEntity`
- `ClientRecord`

### 11.4 Unique/index migration risk

Several domains rely on uniqueness by `client_id`:

- annual reports
- VAT work items
- advance payments
- tax deadlines by generated identity patterns

Those constraints must not be dropped before the new owner columns are fully populated and used.

### 11.5 Permanent document ambiguity

`PermanentDocument` currently mixes semantic claims:

- `scope=CLIENT` comments imply person-level meaning
- the actual FK points to legacy `clients.id`

This is not resolved cleanly by current Layer 1 artifacts and needs an explicit decision before final migration.

## 12. Decision Gates Before Coding

These items should be closed before implementation starts.

### 12.1 Person backfill policy

Need a decision:

- create `Person` for all legacy clients
- or only for legacy rows that clearly represent natural persons

Recommended:

- conservative creation only for clear natural-person cases

### 12.2 Company rows without a person

Need a decision:

- allow `LegalEntity` without `PersonLegalEntityLink` during Layer 1
- or create placeholder persons

Recommended:

- allow missing person link during Layer 1

### 12.3 `PermanentDocument` ownership

Need a decision:

- `scope=CLIENT` becomes `Person`
- `scope=CLIENT` becomes `ClientRecord`
- or the model splits by document category

Recommended:

- defer hard document ownership change unless explicitly decided

### 12.4 External API naming

Need a decision:

- preserve `/clients/{client_id}` routes through Layer 1
- or rename public APIs early to `/client-records/{id}`

Recommended:

- preserve public route shape during Layer 1

## 13. Recommended Execution Order

1. finalize unresolved Layer 1 decisions
2. add new tables
3. add transition columns
4. backfill data
5. add repository compatibility helpers
6. migrate `Business` ownership
7. migrate onboarding flow
8. migrate primary workflow domains
9. migrate secondary operational domains
10. migrate search/timeline/dashboard/reporting
11. enforce constraints and remove legacy fields

## 14. Out of Scope

The following are not part of this document's execution scope:

- Layer 2 identity-hardening decisions
- domain sync redesign for obligations
- terminal state redesign from Layer 3
- RBAC redesign
- future `Obligation` entity

These may influence sequencing but should not be implemented as part of Layer 1 execution unless separately approved.

## 15. Task Breakdown

This section converts the Layer 1 plan into execution-sized work items.

### 15.1 Migration Tasks

#### Task M1: add new core tables

Deliverables:

- add Alembic migration for:
  - `persons`
  - `legal_entities`
  - `client_records`
  - `person_legal_entity_links`
- add base indexes and unique constraints needed for basic integrity

Files expected to change:

- `alembic/versions/<new_revision>.py`
- new model files under `app/clients` or a new domain package if the implementation chooses to split them

Primary risks:

- choosing constraints that are too strict before backfill rules are finalized

Test scope:

- migration upgrade on a clean database
- ORM model import and metadata registration

#### Task M2: add transition ownership columns

Deliverables:

- add `businesses.legal_entity_id`
- add nullable `client_record_id` to workflow tables in scope

Files expected to change:

- `alembic/versions/<new_revision>.py`
- affected ORM models

Primary risks:

- missing one of the workflow tables and creating a partial migration state

Test scope:

- migration upgrade from current production-like schema
- verification that legacy code still runs with nullable transition columns

#### Task M3: backfill data

Deliverables:

- create one-time data migration for:
  - `Client -> LegalEntity`
  - `Client -> ClientRecord`
  - optional `Client -> Person`
  - ownership links where safe
- populate `businesses.legal_entity_id`
- populate `*.client_record_id`

Files expected to change:

- `alembic/versions/<new_revision>.py` or a dedicated migration helper if the team prefers

Primary risks:

- incorrect mapping for edge-case clients
- implicit assumptions around person creation

Test scope:

- migration on seeded data
- row-count parity checks
- nullability checks for backfilled columns
- spot checks on individual and company scenarios

#### Task M4: enforce new constraints

Deliverables:

- mark transition columns `NOT NULL`
- switch FK constraints to the new owners
- migrate relevant unique indexes from legacy owner columns

Files expected to change:

- `alembic/versions/<new_revision>.py`
- affected ORM models

Primary risks:

- enforcing constraints before all code paths write the new columns

Test scope:

- migration on a fully migrated staging-like snapshot
- insert/update regression checks through service layer

### 15.2 Core Domain Tasks

#### Task D1: introduce new domain models and repositories

Deliverables:

- add ORM models for:
  - `Person`
  - `LegalEntity`
  - `ClientRecord`
  - `PersonLegalEntityLink`
- add repositories for new models
- add transitional resolver helpers

Files expected to change:

- new model files
- new repository files
- model registration imports where needed

Primary risks:

- import-order issues with SQLAlchemy model registration

Test scope:

- repository create/get flows
- metadata import smoke tests

#### Task D2: refactor legacy `Client` creation flow

Deliverables:

- change create flow to create:
  - `LegalEntity`
  - `ClientRecord`
  - optional `Person`
  - optional `PersonLegalEntityLink`
- keep external API behavior stable

Primary files:

- [app/clients/services/create_client_service.py](/Users/matanmalka/Desktop/backend/app/clients/services/create_client_service.py:10)
- [app/clients/services/client_service.py](/Users/matanmalka/Desktop/backend/app/clients/services/client_service.py:24)
- [app/clients/api/clients.py](/Users/matanmalka/Desktop/backend/app/clients/api/clients.py:62)

Primary risks:

- breaking conflict checks
- breaking office client number assignment
- breaking onboarding side effects

Test scope:

- create client API
- conflict API
- restore/delete flow if it remains on legacy `Client` during transition

#### Task D3: move `Business` to `LegalEntity`

Deliverables:

- write/read `businesses.legal_entity_id`
- update repository queries and service validations
- replace legacy ownership checks

Primary files:

- [app/businesses/models/business.py](/Users/matanmalka/Desktop/backend/app/businesses/models/business.py:18)
- [app/businesses/repositories/business_repository.py](/Users/matanmalka/Desktop/backend/app/businesses/repositories/business_repository.py:16)
- [app/businesses/services/business_service.py](/Users/matanmalka/Desktop/backend/app/businesses/services/business_service.py:18)
- business-related API routers

Primary risks:

- silent ownership bugs in domains that consume `business_id`

Test scope:

- create/list/update/delete business
- business ownership validation from external domains

#### Task D4: refactor onboarding to `ClientRecord`

Deliverables:

- ensure initial binder creation uses `client_record_id`
- ensure obligation generation uses `client_record_id`
- ensure the create transaction still succeeds atomically

Primary files:

- [app/clients/services/client_service.py](/Users/matanmalka/Desktop/backend/app/clients/services/client_service.py:81)
- [app/binders/services/client_onboarding_service.py](/Users/matanmalka/Desktop/backend/app/binders/services/client_onboarding_service.py:14)
- obligation orchestration modules

Primary risks:

- partial onboarding writes
- transactional rollback gaps

Test scope:

- full create-client happy path
- rollback on downstream failure

### 15.3 Workflow Migration Tasks

#### Task W1: migrate `AnnualReport`

Primary files:

- [app/annual_reports/models/annual_report_model.py](/Users/matanmalka/Desktop/backend/app/annual_reports/models/annual_report_model.py:18)
- [app/annual_reports/services/create_service.py](/Users/matanmalka/Desktop/backend/app/annual_reports/services/create_service.py:27)
- `app/annual_reports/repositories/*`
- `app/annual_reports/api/*`

Deliverables:

- write/read `client_record_id`
- update uniqueness queries
- update API/service lookups

Test scope:

- create report
- get by year
- list by client path
- annual report exports where applicable

#### Task W2: migrate `VatWorkItem`

Primary files:

- [app/vat_reports/models/vat_work_item.py](/Users/matanmalka/Desktop/backend/app/vat_reports/models/vat_work_item.py:29)
- [app/vat_reports/services/intake.py](/Users/matanmalka/Desktop/backend/app/vat_reports/services/intake.py:39)
- `app/vat_reports/repositories/*`
- `app/vat_reports/api/*`

Deliverables:

- write/read `client_record_id`
- update uniqueness by period
- update client summary and export queries

Test scope:

- create work item
- list periods
- query by client and period
- export and summary endpoints

#### Task W3: migrate `TaxDeadline`

Primary files:

- [app/tax_deadline/models/tax_deadline.py](/Users/matanmalka/Desktop/backend/app/tax_deadline/models/tax_deadline.py:50)
- [app/tax_deadline/services/deadline_generator.py](/Users/matanmalka/Desktop/backend/app/tax_deadline/services/deadline_generator.py:16)
- `app/tax_deadline/repositories/*`
- `app/tax_deadline/api/*`

Deliverables:

- write/read `client_record_id`
- update generation queries
- update timeline/upcoming query paths

Test scope:

- deadline generation
- upcoming deadlines
- timeline entries

#### Task W4: migrate `Binder`

Primary files:

- [app/binders/models/binder.py](/Users/matanmalka/Desktop/backend/app/binders/models/binder.py:20)
- `app/binders/repositories/*`
- `app/binders/services/*`
- `app/binders/api/*`

Deliverables:

- write/read `client_record_id`
- update active binder lookups
- update onboarding and search dependencies

Test scope:

- initial binder creation
- binder listing
- binder receive/return flow

#### Task W5: migrate `AdvancePayment`

Primary files:

- [app/advance_payments/models/advance_payment.py](/Users/matanmalka/Desktop/backend/app/advance_payments/models/advance_payment.py:68)
- `app/advance_payments/repositories/*`
- `app/advance_payments/api/*`

Deliverables:

- write/read `client_record_id`
- update analytics queries

Test scope:

- create/list payments
- yearly analytics

### 15.4 Operational Domain Tasks

#### Task O1: migrate `Reminder`

Primary files:

- [app/reminders/models/reminder.py](/Users/matanmalka/Desktop/backend/app/reminders/models/reminder.py:60)
- `app/reminders/services/factory.py`
- `app/reminders/services/reminder_queries.py`
- `app/reminders/api/*`

Test scope:

- manual reminder creation
- automatic reminder creation
- list/cancel/send paths

#### Task O2: migrate `Charge`

Primary files:

- [app/charge/models/charge.py](/Users/matanmalka/Desktop/backend/app/charge/models/charge.py:39)
- `app/charge/repositories/*`
- `app/charge/services/*`

Test scope:

- create/list/query charges
- business ownership validation

#### Task O3: migrate `Notification`

Primary files:

- [app/notification/models/notification.py](/Users/matanmalka/Desktop/backend/app/notification/models/notification.py:65)
- `app/notification/services/*`

Test scope:

- notification creation and list filters

#### Task O4: migrate `Correspondence`

Primary files:

- [app/correspondence/models/correspondence.py](/Users/matanmalka/Desktop/backend/app/correspondence/models/correspondence.py:50)
- [app/correspondence/services/correspondence_service.py](/Users/matanmalka/Desktop/backend/app/correspondence/services/correspondence_service.py:25)
- `app/correspondence/api/*`

Test scope:

- create/update/list correspondence
- business-to-client ownership checks

#### Task O5: migrate `SignatureRequest`

Primary files:

- [app/signature_requests/models/signature_request.py](/Users/matanmalka/Desktop/backend/app/signature_requests/models/signature_request.py:65)
- `app/signature_requests/services/*`
- `app/signature_requests/api/*`

Test scope:

- advisor create
- list by client
- list by business

#### Task O6: migrate `AuthorityContact`

Primary files:

- [app/authority_contact/models/authority_contact.py](/Users/matanmalka/Desktop/backend/app/authority_contact/models/authority_contact.py:48)
- `app/authority_contact/repositories/*`
- `app/authority_contact/api/*`

Test scope:

- create/list/count flows

#### Task O7: migrate `BinderHandover`

Primary files:

- [app/binders/models/binder_handover.py](/Users/matanmalka/Desktop/backend/app/binders/models/binder_handover.py:19)
- `app/binders/repositories/binder_handover_repository.py`

Test scope:

- create/list history by client path

#### Task O8: decide and migrate `PermanentDocument`

Primary files:

- [app/permanent_documents/models/permanent_document.py](/Users/matanmalka/Desktop/backend/app/permanent_documents/models/permanent_document.py:64)
- `app/permanent_documents/services/*`
- `app/permanent_documents/api/*`

Dependencies:

- requires explicit ownership decision before implementation

Test scope:

- upload/list/versioning
- annual-report linked documents

### 15.5 Query Surface Tasks

#### Task Q1: update search

Primary files:

- `app/search/services/search_service.py`
- `app/search/services/document_search_service.py`

Test scope:

- client search
- binder search
- document search enrichment

#### Task Q2: update timeline

Primary files:

- `app/timeline/services/*`
- `app/timeline/api/*`

Test scope:

- client timeline feed
- tax and binder events

#### Task Q3: update dashboard and reports

Primary files:

- `app/dashboard/services/*`
- `app/reports/services/*`

Test scope:

- dashboard cards
- summary reports
- exports

### 15.6 Test Strategy by Phase

#### Phase T1: migration-only verification

- run schema migrations on empty DB
- run schema migrations on populated DB snapshot
- verify backfill parity and nullability

#### Phase T2: core service regression

- client creation
- business CRUD
- onboarding side effects

#### Phase T3: primary workflow regression

- annual reports
- VAT work items
- tax deadlines
- binders
- advance payments

#### Phase T4: operational domain regression

- reminders
- charges
- notifications
- correspondence
- signature requests
- authority contacts
- documents

#### Phase T5: read-model regression

- search
- timeline
- dashboard
- exports

### 15.7 Suggested Execution Tickets

Suggested ticket order:

1. schema foundation
2. transition columns
3. backfill
4. new model/repository layer
5. business ownership migration
6. onboarding migration
7. annual reports migration
8. VAT work item migration
9. tax deadline migration
10. binder migration
11. advance payment migration
12. reminder migration
13. secondary operational domains migration
14. search/timeline/dashboard/report migration
15. hard cutover and cleanup
