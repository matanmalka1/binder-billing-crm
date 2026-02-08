# Binder & Billing CRM
## Operations Runbook

---

## 1. Purpose
Provide day-to-day operational procedures for support, incidents, and routine jobs.

---

## 2. Daily Checks
1. API health endpoint status.
2. Error rate and latency dashboard.
3. Failed notification attempts.
4. Overdue binder count trend.
5. Failed billing/invoice jobs.

---

## 3. Routine Jobs
1. Overdue binder marking job (daily).
2. Payment reminder job (daily).
3. Invoice reconciliation job (daily).
4. Backup verification check (daily).

---

## 4. Incident Severity
1. Sev-1: full outage, data corruption risk.
2. Sev-2: major function down (billing, binder updates).
3. Sev-3: partial degradation or non-critical bug.

---

## 5. Incident Response Flow
1. Detect and acknowledge alert.
2. Assign incident owner.
3. Mitigate impact quickly.
4. Communicate status updates.
5. Execute fix or rollback.
6. Verify system recovery.
7. Publish post-incident summary.

---

## 6. Common Playbooks
## 6.1 Notification Provider Down
1. Disable outbound sending if retry storm occurs.
2. Keep event logging enabled.
3. Reprocess pending sends after recovery.

## 6.2 Migration Failure
1. Stop rollout immediately.
2. Restore last stable app version.
3. Roll back failed migration if safe.
4. Run integrity checks.

## 6.3 Unexpected Overdue Spike
1. Validate system date/time zone.
2. Validate overdue job logic.
3. Sample-check `expected_return_at` calculations.

---

## 7. Data Integrity Checks
1. Binders with `returned` state must have `returned_at`.
2. Returned binders must include `pickup_person_name`.
3. Every binder status change must have log row.
4. Charges in `paid` must have `paid_at`.

---

## 8. Escalation Contacts
1. Technical owner: backend lead.
2. Product owner: tax advisor/admin.
3. Infrastructure owner: DevOps/on-call.

---

## 9. Post-Incident Review Template
1. Incident timeline.
2. Root cause.
3. User/business impact.
4. Corrective actions.
5. Preventive actions and owners.

---

*End of Operations Runbook*
