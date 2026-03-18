from datetime import date, datetime

import pytest

from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
from app.clients.models import Client, ClientType
from app.core.exceptions import ForbiddenError, NotFoundError
from app.correspondence.models.correspondence import CorrespondenceType
from app.correspondence.services.correspondence_service import CorrespondenceService


def _client(db, id_number: str) -> Client:
    client = Client(
        full_name=f"Correspondence Service {id_number}",
        id_number=id_number,
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _contact(db, client_id: int, name: str) -> AuthorityContact:
    contact = AuthorityContact(
        client_id=client_id,
        contact_type=ContactType.ASSESSING_OFFICER,
        name=name,
        phone="0501111111",
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def test_update_entry_forbidden_when_contact_belongs_to_other_client(test_db, test_user):
    c1 = _client(test_db, "CRS001")
    c2 = _client(test_db, "CRS002")
    foreign_contact = _contact(test_db, c2.id, "Foreign Contact")

    service = CorrespondenceService(test_db)
    entry = service.add_entry(
        client_id=c1.id,
        correspondence_type=CorrespondenceType.EMAIL,
        subject="Original",
        occurred_at=datetime(2026, 1, 1, 9, 0, 0),
        created_by=test_user.id,
    )

    with pytest.raises(ForbiddenError) as exc_info:
        service.update_entry(entry.id, c1.id, contact_id=foreign_contact.id)

    assert exc_info.value.code == "CORRESPONDENCE.FORBIDDEN_CONTACT"


def test_update_entry_raises_not_found_when_repo_update_returns_none(test_db, test_user, monkeypatch):
    c1 = _client(test_db, "CRS003")
    service = CorrespondenceService(test_db)
    entry = service.add_entry(
        client_id=c1.id,
        correspondence_type=CorrespondenceType.CALL,
        subject="Will vanish",
        occurred_at=datetime(2026, 1, 2, 9, 0, 0),
        created_by=test_user.id,
    )

    monkeypatch.setattr(service.repo, "update", lambda *_args, **_kwargs: None)

    with pytest.raises(NotFoundError) as exc_info:
        service.update_entry(entry.id, c1.id, subject="x")

    assert exc_info.value.code == "CORRESPONDENCE.NOT_FOUND"


def test_delete_entry_raises_not_found_when_client_mismatch(test_db, test_user):
    c1 = _client(test_db, "CRS004")
    c2 = _client(test_db, "CRS005")
    service = CorrespondenceService(test_db)
    entry = service.add_entry(
        client_id=c1.id,
        correspondence_type=CorrespondenceType.MEETING,
        subject="Delete mismatch",
        occurred_at=datetime(2026, 1, 3, 9, 0, 0),
        created_by=test_user.id,
    )

    with pytest.raises(NotFoundError) as exc_info:
        service.delete_entry(entry.id, c2.id, actor_id=test_user.id)

    assert exc_info.value.code == "CORRESPONDENCE.NOT_FOUND"
