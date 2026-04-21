from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import count

from app.binders.models.binder import Binder, BinderStatus
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.invoice.models.invoice import Invoice
from app.notification.models.notification import (
    Notification,
    NotificationChannel,
    NotificationTrigger,
)
from app.reminders.models.reminder import Reminder, ReminderStatus, ReminderType
from app.signature_requests.models.signature_request import (
    SignatureRequest,
    SignatureRequestStatus,
    SignatureRequestType,
)
from app.tax_deadline.models.tax_deadline import (
    DeadlineType,
    TaxDeadline,
    TaxDeadlineStatus,
)
from app.utils.time_utils import utcnow
from app.timeline.services import timeline_service as timeline_service_module
from tests.helpers.identity import seed_business, seed_client_identity

_client_seq = count(1)


def _business(db):
    idx = next(_client_seq)
    crm_client = seed_client_identity(
        db,
        full_name=f"Timeline Client {idx}",
        id_number=f"2323232{idx:03d}",
    )
    business = seed_business(
        db,
        legal_entity_id=crm_client.legal_entity_id,
        business_name=f"Timeline Business {idx}",
        opened_at=date.today(),
    )
    db.commit()
    db.refresh(business)
    business.client_id = crm_client.id
    return business


def test_timeline_orders_events_newest_first(client, test_db, advisor_headers, test_user):
    business = _business(test_db)
    original_build_client_events = timeline_service_module.build_client_events
    timeline_service_module.build_client_events = lambda *args, **kwargs: []

    try:
        binder = Binder(
            client_record_id=business.client_id,
            binder_number="B-100",
            period_start=date.today() - timedelta(days=5),
            returned_at=date.today() - timedelta(days=1),
            status=BinderStatus.RETURNED,
            created_by=test_user.id,
        )
        test_db.add(binder)

        charge = Charge(
            client_record_id=business.client_id,
            business_id=business.id,
            amount=Decimal("500.00"),
            charge_type=ChargeType.CONSULTATION_FEE,
            status=ChargeStatus.ISSUED,
            created_at=datetime.now(UTC) - timedelta(days=4),
            issued_at=datetime.now(UTC) - timedelta(days=3),
        )
        test_db.add(charge)

        tax_deadline = TaxDeadline(
            client_record_id=business.client_id,
            deadline_type=DeadlineType.VAT,
            due_date=date.today() + timedelta(days=10),
            status=TaxDeadlineStatus.PENDING,
        )
        test_db.add(tax_deadline)

        sig = SignatureRequest(
            business_id=business.id,
            created_by=test_user.id,
            request_type=SignatureRequestType.CUSTOM,
            title="Sign",
            signer_name="Signer",
            status=SignatureRequestStatus.PENDING_SIGNATURE,
            created_at=datetime.now(UTC) - timedelta(days=6),
            sent_at=datetime.now(UTC) - timedelta(days=5),
        )
        test_db.add(sig)

        reminder = Reminder(
            client_record_id=business.client_id,
            business_id=business.id,
            reminder_type=ReminderType.CUSTOM,
            status=ReminderStatus.PENDING,
            target_date=date.today(),
            days_before=0,
            send_on=date.today(),
            message="Reminder",
            created_at=datetime.now(UTC) - timedelta(days=7),
        )
        test_db.add(reminder)

        notification = Notification(
            client_record_id=business.client_id,
            business_id=business.id,
            trigger=NotificationTrigger.BINDER_READY_FOR_PICKUP,
            channel=NotificationChannel.EMAIL,
            recipient="test@example.com",
            content_snapshot="Ready",
            created_at=datetime.now(UTC) - timedelta(days=8),
        )
        test_db.add(notification)

        test_db.flush()
        invoice = Invoice(
            charge_id=charge.id,
            provider="dummy",
            external_invoice_id="INV-1",
            issued_at=datetime.now(UTC) - timedelta(days=2),
            created_at=datetime.now(UTC) - timedelta(days=2),
        )
        test_db.add(invoice)
        test_db.commit()

        resp = client.get(
            f"/api/v1/clients/{business.client_id}/timeline?page=1&page_size=5",
            headers=advisor_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 7
        events = data["events"]
        timestamps = [datetime.fromisoformat(e["timestamp"]) for e in events]
        assert timestamps == sorted(timestamps, reverse=True)
    finally:
        timeline_service_module.build_client_events = original_build_client_events


def test_timeline_applies_bulk_limits(client, test_db, advisor_headers):
    business = _business(test_db)
    original_build_client_events = timeline_service_module.build_client_events
    timeline_service_module.build_client_events = lambda *args, **kwargs: []
    for _ in range(510):
        test_db.add(
            Notification(
                client_record_id=business.client_id,
                business_id=business.id,
                trigger=NotificationTrigger.BINDER_READY_FOR_PICKUP,
                channel=NotificationChannel.EMAIL,
                recipient="bulk@example.com",
                content_snapshot="content",
                created_at=utcnow(),
            )
        )
    test_db.commit()

    try:
        resp = client.get(
            f"/api/v1/clients/{business.client_id}/timeline?page=1&page_size=200",
            headers=advisor_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] <= 505
        assert len(data["events"]) == 200
    finally:
        timeline_service_module.build_client_events = original_build_client_events
