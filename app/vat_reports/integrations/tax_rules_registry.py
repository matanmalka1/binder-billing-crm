"""Adapter for tax_rules registry access used by VAT reports."""

from __future__ import annotations

import logging
from datetime import date

_log = logging.getLogger(__name__)

_REGISTRY_COLUMN = "effective_vat_periodic_and_income_tax_advances"

try:
    from tax_rules.registry import get_effective_periodic_date as _registry_periodic
except Exception:
    _registry_periodic = None


def get_effective_periodic_vat_due_date(
    calendar_year: int,
    period_key: str,
) -> date | None:
    if _registry_periodic is None:
        return None
    try:
        raw = _registry_periodic(calendar_year, period_key, _REGISTRY_COLUMN)
        return date.fromisoformat(raw) if raw else None
    except Exception as exc:
        _log.warning(
            "tax_rules VAT periodic due date lookup failed. "
            "calendar_year=%s period_key=%s column=%s error=%r",
            calendar_year,
            period_key,
            _REGISTRY_COLUMN,
            exc,
        )
        return None
