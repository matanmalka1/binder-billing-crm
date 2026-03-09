# Tests Layout

- Domain-first tree mirrors `app/<domain>` names (e.g., `charge`, not `charges`) so navigation is 1:1.
- Each domain has its own folder: `tests/<domain>/`.
  - API/route tests live in `tests/<domain>/api/` with any API helpers alongside.
  - Service/unit tests live in `tests/<domain>/service/` with domain fakes/enums beside them.
- Cross-domain suites stay in `tests/regression/`; shared fixtures stay in `tests/conftest.py`.
- Prefer intra-domain imports (`tests.<domain>.api.*` / `tests.<domain>.service.*`) instead of reaching across domains.
- File naming: test modules start with `test_*.py` (see `pytest.ini`).
