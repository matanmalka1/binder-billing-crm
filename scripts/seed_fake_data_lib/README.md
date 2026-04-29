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
| `--annual-reports-per-client` | 3 | Spread across last 3 tax years |
| `--preserve-users` | off | Reuse existing users, reset everything else |
| `--users-only` | off | Seed only users and user audit logs |
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

The Seeder class runs domain seeders in dependency order:

1. Users → 2. Clients → 3. Businesses → 4. Binders → 5. Charges → 6. Tax Deadlines →
7. Annual Reports → 8. Authority Contacts → 9. Correspondence → 10. Report sub-models →
11. Advance Payments → 12. Reminders → 13. Documents → 14. Report expense lines →
15. Binder materials → 16. Binder logs → 17. Binder handovers → 18. Binder intake edit logs →
19. Entity audit logs → 20. Notifications → 21. VAT work items → 22. VAT invoices →
23. VAT audit logs → 24. Signature requests → 25. Signature audit events

## Data Coverage Guarantees

After seeding, `SeedCoverageValidator` asserts:
- Every `BinderStatus` enum value appears at least once
- Every `ChargeStatus` enum value appears at least once
- Every `TaxDeadlineStatus` enum value appears at least once (including CANCELED)
- Every `VatWorkItemStatus` appears at least once
- All `AnnualReportStatus` values cycle through via `SEEDABLE_STATUSES`
- At least 3 PENDING tax deadlines with `due_date` in the past (triggers OVERDUE urgency in UI)
- At least one PENDING tax deadline of each type within the next 30 days (upcoming window)
- Annual reports span current year and last 3 years (SeasonSummaryWidget shows real data)
