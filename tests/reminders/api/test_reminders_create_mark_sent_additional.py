from datetime import date


from app.businesses.models.business import BusinessStatus
from app.reminders.models.reminder import ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from tests.helpers.identity import SeededClient, seed_business, seed_client_identity


def _client(db) -> SeededClient:
    return seed_client_identity(
        db,
        full_name="Reminder API Additional Client",
        id_number="RMA001",
    )


def _business(db, crm_client: SeededClient, user_id: int):
    business = seed_business(
        db,
        legal_entity_id=crm_client.legal_entity_id,
        business_name=f"Reminder API Biz {crm_client.id}",
        status=BusinessStatus.ACTIVE,
        opened_at=date.today(),
        created_by=user_id,
    )
    db.commit()
    db.refresh(business)
    business.client_id = crm_client.id
    return business



def test_mark_sent_endpoint_updates_pending_reminder(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client, test_user.id)
    reminder = ReminderRepository(test_db).create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="send me",
    )

    resp = client.post(f"/api/v1/reminders/{reminder.id}/mark-sent", headers=advisor_headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"




