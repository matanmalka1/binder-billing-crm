# Tests Layout

> Last audited: 2026-03-17 (domain-by-domain backend sync).

- Domain-first tree mirrors `app/<domain>` names (e.g., `charge`, not `charges`) so navigation is 1:1.
- Each domain has its own folder: `tests/<domain>/`.
  - API/route tests live in `tests/<domain>/api/` with any API helpers alongside.
  - Service/unit tests live in `tests/<domain>/service/` with domain fakes/enums beside them.
- Cross-domain suites stay in `tests/regression/`; shared fixtures stay in `tests/conftest.py`.
- Prefer intra-domain imports (`tests.<domain>.api.*` / `tests.<domain>.service.*`) instead of reaching across domains.
- File naming: test modules start with `test_*.py` (see `pytest.ini`).

## Run Commands

- Generic domain run: `pytest tests/<domain> -q`
- API-only inside a domain: `pytest tests/<domain>/api -q`
- Service-only inside a domain: `pytest tests/<domain>/service -q`
- Repository-only inside a domain: `pytest tests/<domain>/repository -q`

## Domain Commands

- `actions`: `pytest tests/actions -q`
- `advance_payments`: `pytest tests/advance_payments -q`
- `annual_reports`: `pytest tests/annual_reports -q`
- `auth`: `pytest tests/auth -q`
- `authority_contact`: `pytest tests/authority_contact -q`
- `binders`: `pytest tests/binders -q`
- `businesses`: `pytest tests/businesses -q`
- `charge`: `pytest tests/charge -q`
- `clients`: `pytest tests/clients -q`
- `core`: `pytest tests/core -q`
- `correspondence`: `pytest tests/correspondence -q`
- `dashboard`: `pytest tests/dashboard -q`
- `documents`: `pytest tests/documents -q`
- `health`: `pytest tests/health -q`
- `infrastructure`: `pytest tests/infrastructure -q`
- `invoice`: `pytest tests/invoice -q`
- `notification`: `pytest tests/notification -q`
- `permanent_documents`: `pytest tests/permanent_documents -q`
- `regression`: `pytest tests/regression -q`
- `reminders`: `pytest tests/reminders -q`
- `reports`: `pytest tests/reports -q`
- `search`: `pytest tests/search -q`
- `signature_requests`: `pytest tests/signature_requests -q`
- `tax_deadline`: `pytest tests/tax_deadline -q`
- `timeline`: `pytest tests/timeline -q`
- `users`: `pytest tests/users -q`
- `utils`: `pytest tests/utils -q`
- `vat_reports`: `pytest tests/vat_reports -q`
