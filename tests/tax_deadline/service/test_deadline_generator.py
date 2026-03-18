from datetime import date
from itertools import count

from app.clients.models import Client, ClientType
from app.clients.models.client_tax_profile import ClientTaxProfile, VatType
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.services.deadline_generator import DeadlineGeneratorService


_client_seq = count(1)


def _client(db, suffix: str = "") -> Client:
    idx = next(_client_seq)
    crm_client = Client(
        full_name=f"Deadline Generator Client {idx}",
        id_number=f"TDG{idx:06d}{suffix}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def _set_vat_profile(db, client_id: int, vat_type: VatType) -> None:
    profile = ClientTaxProfile(client_id=client_id, vat_type=vat_type)
    db.add(profile)
    db.commit()


def test_generate_vat_deadlines_monthly_creates_12_and_is_idempotent(test_db):
    crm_client = _client(test_db)
    _set_vat_profile(test_db, crm_client.id, VatType.MONTHLY)

    service = DeadlineGeneratorService(test_db)

    first = service.generate_vat_deadlines(crm_client.id, 2026)
    second = service.generate_vat_deadlines(crm_client.id, 2026)

    assert len(first) == 12
    assert len(second) == 0
    assert {d.deadline_type for d in first} == {DeadlineType.VAT}


def test_generate_vat_deadlines_bimonthly_creates_6(test_db):
    crm_client = _client(test_db, "B")
    _set_vat_profile(test_db, crm_client.id, VatType.BIMONTHLY)

    created = DeadlineGeneratorService(test_db).generate_vat_deadlines(crm_client.id, 2026)

    assert len(created) == 6
    assert all(d.deadline_type == DeadlineType.VAT for d in created)


def test_generate_vat_deadlines_exempt_or_missing_profile_creates_none(test_db):
    exempt_client = _client(test_db, "E")
    _set_vat_profile(test_db, exempt_client.id, VatType.EXEMPT)

    no_profile_client = _client(test_db, "N")

    service = DeadlineGeneratorService(test_db)
    assert service.generate_vat_deadlines(exempt_client.id, 2026) == []
    assert service.generate_vat_deadlines(no_profile_client.id, 2026) == []


def test_generate_advance_and_annual_and_generate_all(test_db):
    crm_client = _client(test_db, "ALL")
    _set_vat_profile(test_db, crm_client.id, VatType.MONTHLY)

    service = DeadlineGeneratorService(test_db)

    advance_created = service.generate_advance_payment_deadlines(crm_client.id, 2026)
    annual_created = service.generate_annual_report_deadline(crm_client.id, 2026)
    annual_second = service.generate_annual_report_deadline(crm_client.id, 2026)

    assert len(advance_created) == 12
    assert len(annual_created) == 1
    assert annual_second == []

    total_created = service.generate_all(crm_client.id, 2027)
    assert total_created == 25  # 12 VAT + 12 advance + 1 annual
