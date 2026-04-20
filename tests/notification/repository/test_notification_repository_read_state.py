from datetime import date

from app.businesses.models.business import Business
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import IdNumberType
from app.notification.models.notification import NotificationChannel, NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository


def _business(test_db, suffix: str) -> Business:
    legal_entity = LegalEntity(
        official_name=f"Notif Read Client {suffix}",
        id_number=f"7200000{suffix}",
        id_number_type=IdNumberType.CORPORATION,
    )
    test_db.add(legal_entity)
    test_db.commit()
    test_db.refresh(legal_entity)

    client_record = ClientRecord(legal_entity_id=legal_entity.id)
    test_db.add(client_record)
    test_db.commit()
    test_db.refresh(client_record)

    business = Business(
        legal_entity_id=legal_entity.id,
        business_name=f"Notif Read Biz {suffix}",
        opened_at=date(2024, 1, 1),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def _create(repo: NotificationRepository, business_id: int, msg: str):
    business = repo.db.get(Business, business_id)
    client_record_id = (
        repo.db.query(ClientRecord.id)
        .filter(ClientRecord.legal_entity_id == business.legal_entity_id)
        .scalar()
    )
    return repo.create(
        client_record_id=client_record_id,
        business_id=business_id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="x@example.com",
        content_snapshot=msg,
    )


def test_notification_repository_mark_all_read_without_scope(test_db):
    repo = NotificationRepository(test_db)
    b1 = _business(test_db, "1")
    b2 = _business(test_db, "2")

    _create(repo, b1.id, "a")
    _create(repo, b2.id, "b")

    assert repo.count_unread() == 2
    updated_all = repo.mark_all_read()
    assert updated_all == 2
    assert repo.count_unread() == 0
