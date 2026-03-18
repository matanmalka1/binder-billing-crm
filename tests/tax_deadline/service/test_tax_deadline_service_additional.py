from datetime import date, timedelta

import pytest

from app.clients.models import Client, ClientType
from app.core.exceptions import AppError, NotFoundError
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService


def _client(test_db, suffix="X"):
    c = Client(
        full_name=f"Tax Extra {suffix}",
        id_number=f"TDEX{suffix}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


def test_tax_deadline_update_and_delete_not_found(test_db):
    service = TaxDeadlineService(test_db)
    with pytest.raises(NotFoundError):
        service.update_deadline(999999, description="x")
    with pytest.raises(NotFoundError):
        service.delete_deadline(999999)
    with pytest.raises(NotFoundError):
        service.get_deadline(999999)


def test_tax_deadline_update_requires_fields(test_db):
    service = TaxDeadlineService(test_db)
    with pytest.raises(AppError):
        service.update_deadline(1)


def test_get_deadlines_by_client_name_and_summary(test_db):
    c = _client(test_db, "A")
    service = TaxDeadlineService(test_db)
    d1 = service.create_deadline(
        client_id=c.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() - timedelta(days=1),
    )
    service.create_deadline(
        client_id=c.id,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
        due_date=date.today() + timedelta(days=2),
    )

    by_name = service.get_deadlines_by_client_name("Tax Extra")
    assert len(by_name) >= 2
    none = service.get_deadlines_by_client_name("no-such-client")
    assert none == []

    summary = service.get_urgent_deadlines_summary(reference_date=date.today())
    assert "urgent" in summary and "upcoming" in summary

    name_map = service.build_client_name_map([d1])
    assert name_map[d1.client_id].startswith("Tax Extra")
