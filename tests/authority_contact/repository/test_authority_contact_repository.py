from datetime import date

from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
from app.authority_contact.repositories.authority_contact_repository import AuthorityContactRepository
from app.businesses.models.business import Business, BusinessType
from app.clients.models.client import Client
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def test_authority_contact_repository_crud_flow(test_db):
    repo = AuthorityContactRepository(test_db)

    user = User(
        full_name="Advisor",
        email="advisor@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    client = Client(
        full_name="Client A",
        id_number="AC001",
    )
    test_db.add_all([user, client])
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name="Business A",
        business_type=BusinessType.COMPANY,
        opened_at=date(2024, 1, 1),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)

    contact_a = repo.create(
        business_id=business.id,
        contact_type=ContactType.ASSESSING_OFFICER,
        name="Officer One",
        phone="111",
    )
    contact_b = repo.create(
        business_id=business.id,
        contact_type=ContactType.VAT_BRANCH,
        name="Officer Two",
        phone="222",
    )

    contacts = repo.list_by_business(business_id=business.id, page=1, page_size=10)
    assert [c.id for c in contacts] == [contact_b.id, contact_a.id]
    assert repo.count_by_business(business_id=business.id) == 2
    assert repo.count_by_business(business_id=business.id, contact_type=ContactType.VAT_BRANCH) == 1

    updated = repo.update(contact_a.id, phone="999")
    assert updated.phone == "999"
    assert updated.updated_at is not None

    deleted = repo.delete(contact_a.id, deleted_by=user.id)
    assert deleted is True
    assert contact_a.deleted_at is not None
    assert contact_a.deleted_by == user.id
    assert repo.get_by_id(contact_a.id) is None
    assert repo.count_by_business(business_id=business.id) == 1
