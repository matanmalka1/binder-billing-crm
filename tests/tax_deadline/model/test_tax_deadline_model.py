from datetime import date

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline


def test_tax_deadline_repr_contains_core_fields():
    deadline = TaxDeadline(
        id=77,
        client_record_id=15,
        deadline_type=DeadlineType.VAT,
        due_date=date(2026, 1, 19),
    )

    rendered = repr(deadline)
    assert "id=77" in rendered
    assert "client_record_id=15" in rendered
    assert "2026-01-19" in rendered
