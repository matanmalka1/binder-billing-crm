from datetime import date
from decimal import Decimal

from app.businesses.models.business import Business, BusinessStatus, BusinessType
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.repositories.business_tax_profile_repository import BusinessTaxProfileRepository
from app.clients.models.client import Client


def _client(test_db, *, full_name: str, id_number: str) -> Client:
    client = Client(full_name=full_name, id_number=id_number)
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_business_repository_crud_soft_delete_and_restore(test_db):
    repo = BusinessRepository(test_db)
    client = _client(test_db, full_name="Repo Client", id_number="700001001")

    created = repo.create(
        client_id=client.id,
        business_type=BusinessType.COMPANY,
        opened_at=date(2024, 1, 1),
        business_name="Repo Biz",
        notes="n1",
        created_by=1,
    )

    assert created.id is not None
    assert repo.get_by_id(created.id).id == created.id
    assert repo.exists_for_client(client.id) is True

    updated = repo.update(created.id, notes="n2", status=BusinessStatus.FROZEN)
    assert updated.notes == "n2"
    assert updated.status == BusinessStatus.FROZEN

    assert repo.soft_delete(created.id, deleted_by=9) is True
    assert repo.get_by_id(created.id) is None
    assert repo.get_by_id_including_deleted(created.id) is not None
    assert repo.soft_delete(999999, deleted_by=9) is False

    restored = repo.restore(created.id, restored_by=11)
    assert restored is not None
    assert restored.deleted_at is None
    assert restored.status == BusinessStatus.ACTIVE
    assert restored.restored_by == 11
    assert repo.restore(created.id, restored_by=12) is None


def test_business_repository_read_filters_search_and_lists(test_db):
    repo = BusinessRepository(test_db)
    client_a = _client(test_db, full_name="Alpha Group", id_number="700001002")
    client_b = _client(test_db, full_name="Beta Group", id_number="700001003")

    a_old = repo.create(
        client_id=client_a.id,
        business_type=BusinessType.COMPANY,
        opened_at=date(2024, 1, 1),
        business_name="Alpha Trade",
    )
    a_new = repo.create(
        client_id=client_a.id,
        business_type=BusinessType.EMPLOYEE,
        opened_at=date(2025, 1, 1),
        business_name="Alpha Work",
    )
    b_one = repo.create(
        client_id=client_b.id,
        business_type=BusinessType.OSEK_PATUR,
        opened_at=date(2024, 6, 1),
        business_name="Beta Shop",
    )

    repo.update(a_new.id, status=BusinessStatus.FROZEN)
    repo.soft_delete(a_old.id, deleted_by=1)

    by_client = repo.list_by_client(client_a.id, page=1, page_size=20)
    assert a_new.id in [b.id for b in by_client]
    assert repo.count_by_client(client_a.id) == 2

    including_deleted = repo.list_by_client_including_deleted(client_a.id)
    assert a_new.id in [b.id for b in including_deleted]
    assert a_old.id in [b.id for b in including_deleted]

    frozen = repo.list(status=BusinessStatus.FROZEN.value, page=1, page_size=20)
    assert [b.id for b in frozen] == [a_new.id]
    assert repo.count(status=BusinessStatus.FROZEN.value) == 1

    by_type = repo.list(business_type=BusinessType.OSEK_PATUR.value)
    assert [b.id for b in by_type] == [b_one.id]

    search_match = repo.list(search="Alpha")
    assert a_new.id in [b.id for b in search_match]

    by_ids = repo.list_by_ids([a_new.id, b_one.id, 123456])
    assert sorted([b.id for b in by_ids]) == sorted([a_new.id, b_one.id])
    assert repo.list_by_ids([]) == []

    all_active = repo.list_all()
    assert a_new.id in [b.id for b in all_active]
    assert b_one.id in [b.id for b in all_active]


def test_business_tax_profile_repository_upsert_create_and_update(test_db):
    business_repo = BusinessRepository(test_db)
    client = _client(test_db, full_name="Tax Client", id_number="700001004")
    business = business_repo.create(
        client_id=client.id,
        business_type=BusinessType.COMPANY,
        opened_at=date(2024, 1, 1),
        business_name="Tax Biz",
    )

    repo = BusinessTaxProfileRepository(test_db)
    assert repo.get_by_business_id(business.id) is None

    created = repo.upsert(
        business.id,
        vat_type="monthly",
        accountant_name="Dana",
        advance_rate=Decimal("7.50"),
        fiscal_year_start_month=4,
    )
    assert created.business_id == business.id
    assert created.vat_type.value == "monthly"
    assert created.accountant_name == "Dana"

    updated = repo.upsert(
        business.id,
        accountant_name="Nora",
        unknown_field="ignored",
    )
    assert updated.id == created.id
    assert updated.accountant_name == "Nora"
    assert updated.updated_at is not None
