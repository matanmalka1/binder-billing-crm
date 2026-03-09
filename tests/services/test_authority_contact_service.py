from datetime import date

import pytest

from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
from app.authority_contact.repositories.authority_contact_repository import AuthorityContactRepository
from app.authority_contact.services.authority_contact_service import AuthorityContactService
from app.clients.models import Client, ClientType
from app.core.exceptions import NotFoundError


def _client(db) -> Client:
    client = Client(
        full_name="AC Service Client",
        id_number="888888888",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def test_add_contact_missing_client_raises_not_found(test_db):
    service = AuthorityContactService(test_db)

    with pytest.raises(NotFoundError) as exc_info:
        service.add_contact(
            client_id=999,
            contact_type=ContactType.VAT_BRANCH,
            name="Missing Client",
        )

    assert exc_info.value.code == "CLIENT.NOT_FOUND"


def test_update_contact_missing_raises_not_found(test_db):
    service = AuthorityContactService(test_db)

    with pytest.raises(NotFoundError) as exc_info:
        service.update_contact(999, name="Nobody")

    assert exc_info.value.code == "AUTHORITY_CONTACT.NOT_FOUND"


def test_delete_contact_missing_raises_not_found(test_db):
    service = AuthorityContactService(test_db)

    with pytest.raises(NotFoundError) as exc_info:
        service.delete_contact(999, actor_id=1)

    assert exc_info.value.code == "AUTHORITY_CONTACT.NOT_FOUND"


def test_list_contacts_filters_and_paginates(test_db):
    client = _client(test_db)
    repo = AuthorityContactRepository(test_db)
    repo.create(client_id=client.id, contact_type=ContactType.VAT_BRANCH, name="VAT 1")
    repo.create(client_id=client.id, contact_type=ContactType.ASSESSING_OFFICER, name="AO 1")
    repo.create(client_id=client.id, contact_type=ContactType.VAT_BRANCH, name="VAT 2")

    service = AuthorityContactService(test_db)
    items, total = service.list_client_contacts(
        client.id, ContactType.VAT_BRANCH, page=1, page_size=1
    )

    assert total == 2
    assert len(items) == 1
    assert items[0].contact_type == ContactType.VAT_BRANCH


def test_repository_soft_delete_marks_deleted_metadata(test_db):
    client = _client(test_db)
    repo = AuthorityContactRepository(test_db)
    contact = repo.create(client_id=client.id, contact_type=ContactType.VAT_BRANCH, name="To Delete")

    deleted = repo.delete(contact.id, deleted_by=42)

    assert deleted is True
    assert repo.get_by_id(contact.id) is None

    persisted = test_db.query(AuthorityContact).filter(AuthorityContact.id == contact.id).first()
    assert persisted.deleted_by == 42
    assert persisted.deleted_at is not None
