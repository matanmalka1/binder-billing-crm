from datetime import date
from decimal import Decimal
from itertools import count

from app.binders.models.binder import Binder, BinderStatus
from app.businesses.models.business import BusinessStatus
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.models.reminder import ReminderStatus, ReminderType
from tests.helpers.identity import SeededClient, seed_business, seed_client_identity


_client_seq = count(1)


def _client(db) -> SeededClient:
    return seed_client_identity(
        db,
        full_name="Reminder Client",
        id_number=f"22222222{next(_client_seq)}",
    )


def _business(db, crm_client: SeededClient, user_id: int):
    business = seed_business(
        db,
        legal_entity_id=crm_client.legal_entity_id,
        business_name=f"Reminder Biz {crm_client.id}",
        status=BusinessStatus.ACTIVE,
        opened_at=date.today(),
        created_by=user_id,
    )
    db.commit()
    db.refresh(business)
    business.client_id = crm_client.id
    return business


def _binder(db, client_id: int, user_id: int) -> Binder:
    binder = Binder(
        client_record_id=client_id,
        binder_number="B-1",
        period_start=date.today(),
        status=BinderStatus.IN_OFFICE,
        created_by=user_id,
    )
    db.add(binder)
    db.commit()
    db.refresh(binder)
    return binder


def _charge(db, business) -> Charge:
    charge = Charge(
        client_record_id=business.client_id,
        business_id=business.id,
        amount=Decimal("100.00"),
        charge_type=ChargeType.OTHER,
        status=ChargeStatus.ISSUED,
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge



def test_create_custom_missing_message_returns_422(client, advisor_headers):
    resp = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": 1,
            "reminder_type": "custom",
            "target_date": date.today().isoformat(),
            "days_before": 1,
        },
    )

    assert resp.status_code == 422
    assert any("message" in err["msg"] for err in resp.json()["detail"])


def test_cancel_reminder_marks_status_and_canceled_at(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client, test_user.id)
    repo = ReminderRepository(test_db)
    reminder = repo.create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="Ping",
    )

    resp = client.post(f"/api/v1/reminders/{reminder.id}/cancel", headers=advisor_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "canceled"
    assert body["canceled_at"] is not None

    updated = repo.get_by_id(reminder.id)
    assert updated.status == ReminderStatus.CANCELED

