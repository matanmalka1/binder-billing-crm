from datetime import date

from app.models import Binder, BinderStatus
from app.services.binder_helpers import BinderHelpers
from app.services.sla_service import SLAService


def test_binder_expected_return_is_90_days():
    received_at = date(2026, 1, 1)
    assert BinderHelpers.calculate_expected_return(received_at) == date(2026, 4, 1)


def test_sla_overdue_and_due_today_calculations():
    reference = date(2026, 2, 9)
    binder = Binder(
        client_id=1,
        binder_number="BND-TEST-1",
        received_at=reference,
        expected_return_at=reference,
        status=BinderStatus.IN_OFFICE,
        received_by=1,
    )

    assert SLAService.is_due_today(binder, reference_date=reference) is True
    assert SLAService.is_overdue(binder, reference_date=reference) is False
    assert SLAService.days_overdue(binder, reference_date=reference) == 0

    binder.expected_return_at = date(2026, 2, 1)
    assert SLAService.is_overdue(binder, reference_date=reference) is True
    assert SLAService.days_overdue(binder, reference_date=reference) == 8

    binder.status = BinderStatus.RETURNED
    assert SLAService.is_overdue(binder, reference_date=reference) is False
    assert SLAService.days_overdue(binder, reference_date=reference) == 0

