from datetime import date
from unittest.mock import patch

from sqlalchemy import text

from app.advance_payments.models.advance_payment import AdvancePayment
from app.clients.services.client_creation_service import ClientCreationService
from app.clients.services.client_onboarding_orchestrator import ClientOnboardingOrchestrator
from app.common.enums import EntityType, IdNumberType, VatType
from app.core.exceptions import ConflictError
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.vat_reports.models.vat_work_item import VatWorkItem
from tests.helpers.identity import seed_client_identity


def _create_vat_client(test_db, id_number: str):
    return ClientCreationService(test_db).create_client(
        full_name="VAT Onboarding Client",
        id_number=id_number,
        id_number_type=IdNumberType.INDIVIDUAL,
        entity_type=EntityType.OSEK_MURSHE,
        vat_reporting_frequency=VatType.MONTHLY,
        advance_rate="5.0",
        actor_id=1,
        reference_date=date(2026, 4, 30),
    )


def test_onboarding_creates_vat_work_items_and_advance_payments(test_db):
    client_record = _create_vat_client(test_db, "123456780")
    deadlines = test_db.query(TaxDeadline).filter(TaxDeadline.client_record_id == client_record.id).all()
    vat_deadlines = [d for d in deadlines if d.deadline_type.value == "vat"]
    advance_deadlines = [d for d in deadlines if d.deadline_type.value == "advance_payment"]
    vat_items = test_db.query(VatWorkItem).filter(VatWorkItem.client_record_id == client_record.id).all()
    payments = test_db.query(AdvancePayment).filter(AdvancePayment.client_record_id == client_record.id).all()

    assert len(vat_deadlines) == len(vat_items) == 9
    assert {i.period for i in vat_items} == {d.period for d in vat_deadlines}
    assert all(d.vat_work_item_id is not None for d in vat_deadlines)
    assert {i.id for i in vat_items} == {d.vat_work_item_id for d in vat_deadlines}
    assert len(advance_deadlines) == len(payments) == 9
    assert {p.period for p in payments} == {d.period for d in advance_deadlines}
    assert all(d.advance_payment_id is not None for d in advance_deadlines)


def test_onboarding_retry_does_not_duplicate_vat_work_items(test_db):
    client_record = _create_vat_client(test_db, "123456781")
    ClientOnboardingOrchestrator(test_db).run(
        client_record.id,
        actor_id=1,
        entity_type=EntityType.OSEK_MURSHE,
        reference_date=date(2026, 4, 30),
    )

    count = test_db.query(VatWorkItem).filter(VatWorkItem.client_record_id == client_record.id).count()
    assert count == 9
    payment_count = test_db.query(AdvancePayment).filter(AdvancePayment.client_record_id == client_record.id).count()
    assert payment_count == 9


def test_onboarding_does_not_create_empty_setup_placeholders(test_db):
    _create_vat_client(test_db, "123456782")

    assert test_db.execute(text("select count(*) from authority_contacts")).scalar() == 0
    assert test_db.execute(text("select count(*) from permanent_documents")).scalar() == 0
    assert test_db.execute(text("select count(*) from entity_notes")).scalar() == 0


def test_onboarding_does_not_create_advance_payments_without_deadlines(test_db, monkeypatch):
    seeded = seed_client_identity(
        test_db,
        full_name="No Advance Deadline Client",
        id_number="123456783",
        entity_type=EntityType.OSEK_MURSHE,
        vat_reporting_frequency=VatType.MONTHLY,
        office_client_number=100,
    )
    TaxDeadlineRepository(test_db).create(
        client_record_id=seeded.id,
        deadline_type=DeadlineType.VAT,
        due_date=date(2026, 5, 15),
        period="2026-04",
    )
    monkeypatch.setattr(
        "app.clients.services.client_onboarding_orchestrator.generate_client_obligations",
        lambda *args, **kwargs: 0,
    )

    ClientOnboardingOrchestrator(test_db).run(
        seeded.id,
        actor_id=1,
        entity_type=EntityType.OSEK_MURSHE,
        reference_date=date(2026, 4, 30),
    )

    assert test_db.query(VatWorkItem).filter(VatWorkItem.client_record_id == seeded.id).count() == 1
    assert test_db.query(AdvancePayment).filter(AdvancePayment.client_record_id == seeded.id).count() == 0


def test_sync_advance_payments_conflict_error_falls_back_to_existing(test_db):
    seeded = seed_client_identity(
        test_db,
        full_name="Conflict Fallback Client",
        id_number="123456784",
        entity_type=EntityType.OSEK_MURSHE,
        vat_reporting_frequency=VatType.MONTHLY,
        office_client_number=200,
    )
    existing_payment = AdvancePayment(
        client_record_id=seeded.id,
        period="2026-05",
        period_months_count=1,
        due_date=date(2026, 5, 15),
    )
    test_db.add(existing_payment)

    deadline = TaxDeadlineRepository(test_db).create(
        client_record_id=seeded.id,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
        due_date=date(2026, 5, 15),
        period="2026-05",
    )
    test_db.flush()

    orchestrator = ClientOnboardingOrchestrator(test_db)
    with patch.object(
        orchestrator.advance_repo,
        "get_by_period",
        side_effect=[None, existing_payment],
    ), patch.object(
        orchestrator.advance_repo,
        "create",
        side_effect=ConflictError("dup", "ADVANCE_PAYMENT.CONFLICT"),
    ):
        orchestrator._sync_advance_payments(seeded.id)

    test_db.refresh(deadline)
    assert deadline.advance_payment_id == existing_payment.id


def test_sync_vat_work_items_links_existing_when_actor_none(test_db):
    client_record = _create_vat_client(test_db, "123456785")
    deadlines = (
        test_db.query(TaxDeadline)
        .filter(
            TaxDeadline.client_record_id == client_record.id,
            TaxDeadline.deadline_type == DeadlineType.VAT,
        )
        .all()
    )
    assert deadlines, "precondition: VAT deadlines must exist"

    vat_item_count_before = test_db.query(VatWorkItem).filter(
        VatWorkItem.client_record_id == client_record.id
    ).count()

    for d in deadlines:
        d.vat_work_item_id = None
    test_db.flush()

    orchestrator = ClientOnboardingOrchestrator(test_db)
    created = orchestrator._sync_vat_work_items(client_record.id, actor_id=None)

    assert created == 0
    vat_item_count_after = test_db.query(VatWorkItem).filter(
        VatWorkItem.client_record_id == client_record.id
    ).count()
    assert vat_item_count_after == vat_item_count_before

    test_db.expire_all()
    reloaded = (
        test_db.query(TaxDeadline)
        .filter(
            TaxDeadline.client_record_id == client_record.id,
            TaxDeadline.deadline_type == DeadlineType.VAT,
        )
        .all()
    )
    assert all(d.vat_work_item_id is not None for d in reloaded)
