from datetime import date, timedelta

from app.models import Client, ClientType, DeadlineType, UrgencyLevel
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService


def _create_client(test_db) -> Client:
    client = Client(
        full_name="Deadline Test Client",
        id_number="987654321",
        client_type=ClientType.OSEK_MURSHE,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_create_tax_deadline(test_db):
    """Test creating tax deadline."""
    client = _create_client(test_db)
    service = TaxDeadlineService(test_db)

    deadline = service.create_deadline(
        client_id=client.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=10),
        payment_amount=5000.00,
        description="February VAT",
    )

    assert deadline.client_id == client.id
    assert deadline.deadline_type == DeadlineType.VAT
    assert deadline.status == "pending"
    assert deadline.payment_amount == 5000.00


def test_urgency_calculation(test_db):
    """Test urgency level calculation."""
    client = _create_client(test_db)
    service = TaxDeadlineService(test_db)
    reference = date.today()

    # Overdue
    overdue = service.create_deadline(
        client.id,
        DeadlineType.VAT,
        reference - timedelta(days=1),
    )
    assert service.compute_urgency(overdue, reference) == UrgencyLevel.OVERDUE

    # Red (2 days or less)
    red = service.create_deadline(
        client.id,
        DeadlineType.ADVANCE_PAYMENT,
        reference + timedelta(days=2),
    )
    assert service.compute_urgency(red, reference) == UrgencyLevel.RED

    # Yellow (3-7 days)
    yellow = service.create_deadline(
        client.id,
        DeadlineType.NATIONAL_INSURANCE,
        reference + timedelta(days=5),
    )
    assert service.compute_urgency(yellow, reference) == UrgencyLevel.YELLOW

    # Green (>7 days)
    green = service.create_deadline(
        client.id,
        DeadlineType.ANNUAL_REPORT,
        reference + timedelta(days=30),
    )
    assert service.compute_urgency(green, reference) == UrgencyLevel.GREEN


def test_completed_deadline_has_no_urgency(test_db):
    """Test that completed deadlines have no urgency."""
    client = _create_client(test_db)
    service = TaxDeadlineService(test_db)

    deadline = service.create_deadline(
        client.id,
        DeadlineType.VAT,
        date.today() - timedelta(days=1),
    )

    # Before completion: urgent
    assert service.compute_urgency(deadline) == UrgencyLevel.OVERDUE

    # After completion: no urgency
    completed = service.mark_completed(deadline.id)
    assert service.compute_urgency(completed) is None


def test_get_upcoming_deadlines(test_db):
    """Test getting upcoming deadlines."""
    client = _create_client(test_db)
    service = TaxDeadlineService(test_db)
    reference = date.today()

    # Create deadlines at different dates
    service.create_deadline(client.id, DeadlineType.VAT, reference + timedelta(days=3))
    service.create_deadline(
        client.id,
        DeadlineType.ADVANCE_PAYMENT,
        reference + timedelta(days=10),
    )
    service.create_deadline(
        client.id,
        DeadlineType.NATIONAL_INSURANCE,
        reference + timedelta(days=30),
    )

    # Get upcoming within 7 days
    upcoming = service.get_upcoming_deadlines(7, reference)
    assert len(upcoming) == 1

    # Get upcoming within 15 days
    upcoming_15 = service.get_upcoming_deadlines(15, reference)
    assert len(upcoming_15) == 2


def test_get_overdue_deadlines(test_db):
    """Test getting overdue deadlines."""
    client = _create_client(test_db)
    service = TaxDeadlineService(test_db)
    reference = date.today()

    service.create_deadline(client.id, DeadlineType.VAT, reference - timedelta(days=1))
    service.create_deadline(
        client.id,
        DeadlineType.ADVANCE_PAYMENT,
        reference - timedelta(days=5),
    )
    service.create_deadline(
        client.id,
        DeadlineType.NATIONAL_INSURANCE,
        reference + timedelta(days=5),
    )

    overdue = service.get_overdue_deadlines(reference)
    assert len(overdue) == 2