from datetime import date, datetime

import pytest

from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
from app.businesses.models.business import Business, BusinessStatus, EntityType
from app.clients.models.client import Client
from app.core.exceptions import ForbiddenError, NotFoundError
from app.correspondence.models.correspondence import CorrespondenceType
from app.correspondence.services.correspondence_service import CorrespondenceService


def _business(db, id_number: str) -> Business:
    client = Client(
        full_name=f"Correspondence Service {id_number}",
        id_number=id_number,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name=f"Business {id_number}",
        entity_type=EntityType.COMPANY_LTD,
        opened_at=date.today(),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def _contact(db, business_id: int, name: str) -> AuthorityContact:
    contact = AuthorityContact(
        business_id=business_id,
        contact_type=ContactType.ASSESSING_OFFICER,
        name=name,
        phone="0501111111",
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def test_update_entry_forbidden_when_contact_belongs_to_other_business(test_db, test_user):
    b1 = _business(test_db, "700000001")
    b2 = _business(test_db, "700000002")
    foreign_contact = _contact(test_db, b2.id, "Foreign Contact")

    service = CorrespondenceService(test_db)
    entry = service.add_entry(
        business_id=b1.id,
        correspondence_type=CorrespondenceType.EMAIL,
        subject="Original",
        occurred_at=datetime(2026, 1, 1, 9, 0, 0),
        created_by=test_user.id,
    )

    with pytest.raises(ForbiddenError) as exc_info:
        service.update_entry(entry.id, b1.id, contact_id=foreign_contact.id)

    assert exc_info.value.code == "CORRESPONDENCE.FORBIDDEN_CONTACT"


def test_update_entry_raises_not_found_when_repo_update_returns_none(test_db, test_user, monkeypatch):
    b1 = _business(test_db, "700000003")
    service = CorrespondenceService(test_db)
    entry = service.add_entry(
        business_id=b1.id,
        correspondence_type=CorrespondenceType.CALL,
        subject="Will vanish",
        occurred_at=datetime(2026, 1, 2, 9, 0, 0),
        created_by=test_user.id,
    )

    monkeypatch.setattr(service.repo, "update", lambda *_args, **_kwargs: None)

    with pytest.raises(NotFoundError) as exc_info:
        service.update_entry(entry.id, b1.id, subject="x")

    assert exc_info.value.code == "CORRESPONDENCE.NOT_FOUND"


def test_delete_entry_raises_not_found_when_business_mismatch(test_db, test_user):
    b1 = _business(test_db, "700000004")
    b2 = _business(test_db, "700000005")
    service = CorrespondenceService(test_db)
    entry = service.add_entry(
        business_id=b1.id,
        correspondence_type=CorrespondenceType.MEETING,
        subject="Delete mismatch",
        occurred_at=datetime(2026, 1, 3, 9, 0, 0),
        created_by=test_user.id,
    )

    with pytest.raises(NotFoundError) as exc_info:
        service.delete_entry(entry.id, b2.id, actor_id=test_user.id)

    assert exc_info.value.code == "CORRESPONDENCE.NOT_FOUND"


def test_add_entry_raises_not_found_for_missing_business(test_db, test_user):
    service = CorrespondenceService(test_db)

    with pytest.raises(NotFoundError) as exc_info:
        service.add_entry(
            business_id=999999,
            correspondence_type=CorrespondenceType.EMAIL,
            subject="Missing business",
            occurred_at=datetime(2026, 1, 4, 9, 0, 0),
            created_by=test_user.id,
        )

    assert exc_info.value.code == "BUSINESS.NOT_FOUND"


def test_add_entry_rejected_for_closed_business(test_db, test_user):
    business = _business(test_db, "700000006")
    business.status = BusinessStatus.CLOSED
    test_db.commit()

    service = CorrespondenceService(test_db)

    with pytest.raises(ForbiddenError) as exc_info:
        service.add_entry(
            business_id=business.id,
            correspondence_type=CorrespondenceType.EMAIL,
            subject="No create",
            occurred_at=datetime(2026, 1, 5, 9, 0, 0),
            created_by=test_user.id,
        )

    assert exc_info.value.code == "BUSINESS.CLOSED"


def test_get_entry_not_found_for_mismatch_business(test_db, test_user):
    b1 = _business(test_db, "700000007")
    b2 = _business(test_db, "700000008")
    service = CorrespondenceService(test_db)

    entry = service.add_entry(
        business_id=b1.id,
        correspondence_type=CorrespondenceType.LETTER,
        subject="Owned by b1",
        occurred_at=datetime(2026, 1, 6, 9, 0, 0),
        created_by=test_user.id,
    )

    with pytest.raises(NotFoundError) as exc_info:
        service.get_entry(entry.id, b2.id)

    assert exc_info.value.code == "CORRESPONDENCE.NOT_FOUND"
