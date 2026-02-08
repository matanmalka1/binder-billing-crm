# Binder & Billing CRM
## Testing Strategy

---

## 1. Purpose
Define test layers, ownership, and release gates for safe delivery.

---

## 2. Test Layers
1. Unit tests:
- Services, validators, date calculators, role guards.

2. Repository tests:
- CRUD, constraints, transaction behavior.

3. Integration tests:
- API endpoint behavior with database.

4. End-to-end tests:
- Key flows: receive binder, return binder, overdue marking, charge issuance.

---

## 3. Critical Business Rule Coverage
1. 90-day rule marks overdue correctly.
2. Intake never blocked by warning conditions.
3. Return requires `pickup_person_name`.
4. No hard delete paths for core entities.
5. Every binder status change writes audit log.

---

## 4. Contract Testing
1. API payloads must match `api_contracts.md`.
2. Error shape must remain stable.
3. Role-based forbidden scenarios must return `403`.

---

## 5. Test Data Strategy
1. Deterministic fixtures for date-sensitive logic.
2. Factory helpers for users, clients, binders, charges.
3. Isolated database per test run where possible.

---

## 6. Coverage Targets
1. Unit/repository combined: 85% line coverage target.
2. Mandatory coverage on state transitions and money fields.
3. New endpoint PRs require at least one integration test.

---

## 7. CI Gates
1. Lint and formatting checks.
2. Migration up/down test.
3. Full automated test suite.
4. Block merge on failures.

---

## 8. Manual QA Smoke Checklist
1. Login as advisor and secretary.
2. Create client and receive binder.
3. Move binder to ready-for-pickup and return.
4. Verify dashboard counters update.
5. Verify one overdue scenario appears correctly.

---

*End of Testing Strategy*
