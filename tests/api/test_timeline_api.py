from datetime import date, datetime, timedelta
from itertools import count
from decimal import Decimal

from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.clients.models import Client, ClientType
from app.invoice.models.invoice import Invoice
from app.notification.models.notification import Notification, NotificationChannel, NotificationTrigger
from app.reminders.models.reminder import Reminder, ReminderType, ReminderStatus
from app.signature_requests.models.signature_request import SignatureRequest, SignatureRequestStatus, SignatureRequestType
from app.tax_deadline.models.tax_deadline import TaxDeadline, DeadlineType, TaxDeadlineStatus
from app.timeline.repositories.timeline_repository import TimelineRepository
from app.utils.time import utcnow

_client_seq = count(1)


def _client(db) -> Client:
    c = Client(
        full_name=f"Timeline Client {next(_client_seq)}",
        id_number=f"2323232{next(_client_seq)}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_timeline_orders_events_newest_first(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    repo = TimelineRepository(test_db)

    binder = Binder(
        client_id=crm_client.id,
        binder_number="B-100",
        binder_type=BinderType.VAT,
        received_at=date.today() - timedelta(days=5),
        returned_at=date.today() - timedelta(days=1),
        status=BinderStatus.RETURNED,
        received_by=test_user.id,
    )
    test_db.add(binder)

    charge = Charge(
        client_id=crm_client.id,
        amount=Decimal("500.00"),
        currency="ILS",
        charge_type=ChargeType.ONE_TIME,
        status=ChargeStatus.ISSUED,
        created_at=datetime.utcnow() - timedelta(days=4),
        issued_at=datetime.utcnow() - timedelta(days=3),
    )
    test_db.add(charge)

    tax_deadline = TaxDeadline(
        client_id=crm_client.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=10),
        status=TaxDeadlineStatus.PENDING,
    )
    test_db.add(tax_deadline)

    sig = SignatureRequest(
        client_id=crm_client.id,
        created_by=test_user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Sign",
        signer_name="Signer",
        status=SignatureRequestStatus.PENDING_SIGNATURE,
        created_at=datetime.utcnow() - timedelta(days=6),
        sent_at=datetime.utcnow() - timedelta(days=5),
    )
    test_db.add(sig)

    reminder = Reminder(
        client_id=crm_client.id,
        reminder_type=ReminderType.CUSTOM,
        status=ReminderStatus.PENDING,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="Reminder",
        created_at=datetime.utcnow() - timedelta(days=7),
    )
    test_db.add(reminder)

    notification = Notification(
        client_id=crm_client.id,
        trigger=NotificationTrigger.BINDER_READY_FOR_PICKUP,
        channel=NotificationChannel.EMAIL,
        recipient="test@example.com",
        content_snapshot="Ready",
        created_at=datetime.utcnow() - timedelta(days=8),
    )
    test_db.add(notification)

    test_db.flush()
    invoice = Invoice(
        charge_id=charge.id,
        provider="dummy",
        external_invoice_id="INV-1",
        issued_at=datetime.utcnow() - timedelta(days=2),
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    test_db.add(invoice)
    test_db.commit()

    resp = client.get(
        f"/api/v1/clients/{crm_client.id}/timeline?page=1&page_size=5",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Should return newest 5 events, total includes all
    assert data["total"] >= 7
    events = data["events"]
    timestamps = [datetime.fromisoformat(e["timestamp"]) for e in events]
    assert timestamps == sorted(timestamps, reverse=True)


def test_timeline_applies_bulk_limits(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    # Create >500 notifications to hit cap
    for i in range(510):
        test_db.add(
            Notification(
                client_id=crm_client.id,
                trigger=NotificationTrigger.BINDER_READY_FOR_PICKUP,
                channel=NotificationChannel.EMAIL,
                recipient="bulk@example.com",
                content_snapshot="content",
                created_at=utcnow(),
            )
        )
    test_db.commit()

    resp = client.get(
        f"/api/v1/clients/{crm_client.id}/timeline?page=1&page_size=200",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Total capped to 500 notifications + a few other events
    assert data["total"] <= 505
    # First page returns at most 200 per query limit
    assert len(data["events"]) == 200
