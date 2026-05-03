# seed_fake_data_lib

Fake-data seeder for local development. Populates all 21 domains with coherent, Hebrew-language demo data.

## Entry Point

```bash
# From repo root:
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset
```

## Common Flags

| Flag | Default | Description |
|---|---|---|
| `--reset` | off | Truncate all tables before seeding |
| `--clients` | 60 | Number of client records |
| `--users` | 8 | Staff users (mix of ADVISOR / SECRETARY) |
| `--annual-reports-per-client` | 3 | Historical annual report years per client, in addition to the onboarding-year report |
| `--min-binders-per-client` | 1 | Minimum historical binders per client, in addition to one active onboarding binder |
| `--max-binders-per-client` | 3 | Maximum historical binders per client, in addition to one active onboarding binder |
| `--min-vat-work-items-per-client` | 6 | Minimum historical VAT periods for VAT-reporting clients |
| `--max-vat-work-items-per-client` | 12 | Maximum historical VAT periods for VAT-reporting clients |
| `--preserve-users` | off | Reuse existing users, reset everything else |
| `--users-only` | off | Seed only users and user audit logs |
| `--onboarding-only` | off | Seed clients with only baseline onboarding records, no historical demo layer |
| `--reference-date` | today | Business reference date for periods, due dates and historical status choices |
| `--skip-validation` | off | Skip post-seed coverage and consistency validation |
| `--seed` | 42 | RNG seed for reproducible data |

Run `python scripts/seed_fake_data.py --help` for the full list.

## File Layout

```
seed_fake_data_lib/
├── README.md               ← this file
├── __init__.py             ← package root, exposes ROOT_DIR
├── config.py               ← SeedConfig dataclass + CLI arg parser
├── seeder.py               ← Seeder class — orchestrates all domain seeders in order
├── coverage.py             ← SeedCoverageValidator — asserts every enum value appears
├── runtime.py              ← helpers shared across the run (timing, printing)
├── constants.py            ← cross-domain constants (e.g. Israeli ID formats)
├── random_utils.py         ← name/phone/ID generators
├── demo_catalog.py         ← static catalogs: business names, addresses, authority contacts,
│                              correspondence subjects, VAT counterparties
├── realistic_seed_text.py  ← domain-specific Hebrew text: charge descriptions, material labels,
│                              income/expense descriptions, signature copy, invoice labels
└── domains/                ← one module per domain
    ├── __init__.py
    ├── _business_groups.py ← shared helper: group businesses by client
    ├── client_graph.py     ← shared helper: client → business graph traversal
    ├── users.py            ← User, UserAuditLog, EntityAuditLog
    ├── clients.py          ← Person, LegalEntity, PersonLegalEntityLink, ClientRecord, EntityNote
    ├── binders.py          ← Binder, BinderIntake, BinderIntakeMaterial,
    │                          BinderStatusLog, BinderHandover, BinderIntakeEditLog
    ├── charges.py          ← Charge, Invoice
    ├── taxes.py            ← TaxDeadline, AdvancePayment
    ├── reports.py          ← AnnualReport + all sub-models (detail, income/expense lines,
    │                          schedule entries, annex data, credit points, status history)
    ├── contacts.py         ← AuthorityContact, Correspondence
    ├── documents.py        ← PermanentDocument
    ├── reminders.py        ← Reminder
    ├── notifications.py    ← Notification
    ├── vat.py              ← VatWorkItem, VatInvoice, VatAuditLog
    └── signature_requests.py ← SignatureRequest, SignatureAuditEvent
```

## Seeding Order

The Seeder class first creates users, clients and businesses, then runs the same
client onboarding orchestrator used by the app. The default seed then adds a
coherent historical layer. `--onboarding-only` stops after the baseline layer.

The full seed runs domain seeders in dependency order:

1. Users → 2. Clients → 3. Businesses → 4. Onboarding baseline → 5. Historical binders →
6. Charges → 7. Tax deadlines → 8. Annual reports → 9. Authority contacts →
10. Correspondence → 11. Report sub-models → 12. Historical advance payments →
13. Reminders → 14. Documents → 15. Report expense lines → 16. Binder materials →
17. Binder logs → 18. Binder handovers → 19. Binder intake edit logs →
20. Entity audit logs → 21. Notifications → 22. Historical VAT work items →
23. VAT invoices → 24. VAT audit logs → 25. Signature requests → 26. Signature audit events

## Data Coverage Guarantees

After seeding, `SeedCoverageValidator` asserts:
- Every `ChargeStatus` enum value appears at least once
- Every `TaxDeadlineStatus` enum value appears at least once (including CANCELED)
- Every `VatWorkItemStatus` appears at least once
- All `AnnualReportStatus` values cycle through via `SEEDABLE_STATUSES`
- At least 3 PENDING tax deadlines with `due_date` in the past (triggers OVERDUE urgency in UI)
- At least one PENDING tax deadline of each type within the next 30 days (upcoming window)
- Annual reports include onboarding-year reports plus historical years
- Every VAT work item has a matching VAT deadline
- Every advance payment has a matching advance-payment deadline
- Every annual report has a matching annual-report deadline
- Every client has exactly one active binder
- VAT-exempt clients have no VAT work items
