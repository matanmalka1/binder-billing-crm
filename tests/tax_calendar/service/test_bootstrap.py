from datetime import date

from app.common.enums import DeadlineRuleType
from app.tax_calendar.models.deadline_rule import DeadlineRule
from app.tax_calendar.models.tax_calendar_entry import TaxCalendarEntry
from app.tax_calendar.services.bootstrap import (
    DEFAULT_EFFECTIVE_FROM,
    bootstrap_tax_calendar,
    seed_default_deadline_rules,
)


def _rule_count(db) -> int:
    return db.query(DeadlineRule).count()


def _entry_count(db) -> int:
    return db.query(TaxCalendarEntry).count()


def test_default_rules_are_created_when_missing(test_db):
    created = seed_default_deadline_rules(test_db)
    test_db.commit()

    assert created == {
        "vat_monthly": 1,
        "vat_bimonthly": 1,
        "advance_monthly": 1,
        "advance_bimonthly": 1,
        "annual_report": 1,
    }
    assert _rule_count(test_db) == 5
    rules = test_db.query(DeadlineRule).all()
    assert {r.rule_type for r in rules} == set(DeadlineRuleType)
    assert {r.effective_from for r in rules} == {DEFAULT_EFFECTIVE_FROM}
    assert {r.effective_to for r in rules} == {None}


def test_default_rules_are_not_duplicated_on_rerun(test_db):
    seed_default_deadline_rules(test_db)
    test_db.commit()
    created = seed_default_deadline_rules(test_db)
    test_db.commit()

    assert created == {
        "vat_monthly": 0,
        "vat_bimonthly": 0,
        "advance_monthly": 0,
        "advance_bimonthly": 0,
        "annual_report": 0,
    }
    assert _rule_count(test_db) == 5


def test_bootstrap_generates_entries_for_requested_year_range(test_db):
    result = bootstrap_tax_calendar(test_db, start_year=2026, end_year=2027)
    test_db.commit()

    assert result["start_year"] == 2026
    assert result["end_year"] == 2027
    assert result["entries_created"] == {
        2026: {
            "vat_monthly": 12,
            "vat_bimonthly": 6,
            "advance_monthly": 12,
            "advance_bimonthly": 6,
            "annual_report": 1,
        },
        2027: {
            "vat_monthly": 12,
            "vat_bimonthly": 6,
            "advance_monthly": 12,
            "advance_bimonthly": 6,
            "annual_report": 1,
        },
    }
    assert _entry_count(test_db) == 74


def test_bootstrap_rerun_creates_zero_new_entries(test_db):
    bootstrap_tax_calendar(test_db, start_year=2026, end_year=2026)
    test_db.commit()
    result = bootstrap_tax_calendar(test_db, start_year=2026, end_year=2026)
    test_db.commit()

    assert result["rules_created"] == {
        "vat_monthly": 0,
        "vat_bimonthly": 0,
        "advance_monthly": 0,
        "advance_bimonthly": 0,
        "annual_report": 0,
    }
    assert result["entries_created"] == {
        2026: {
            "vat_monthly": 0,
            "vat_bimonthly": 0,
            "advance_monthly": 0,
            "advance_bimonthly": 0,
            "annual_report": 0,
        },
    }
    assert _entry_count(test_db) == 37


def test_bootstrap_default_year_range_is_current_and_next_year(test_db):
    result = bootstrap_tax_calendar(test_db, today=date(2026, 5, 7))
    test_db.commit()

    assert result["start_year"] == 2026
    assert result["end_year"] == 2027
