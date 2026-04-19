"""
Wave 1 migration tests: client_record_id on 5 primary entities.

Tests per entity (W1–W5):
  1. New repo method returns correct results when client_record_id is set
  2. Service resolves client_record_id from client_id correctly
  3. Fallback works when no ClientRecord exists
  4. Legacy rows become visible through the new read path after backfill
"""
import pytest
from datetime import date
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity  # noqa: F401
from app.clients.models.person import Person  # noqa: F401
from app.clients.models.person_legal_entity_link import PersonLegalEntityLink  # noqa: F401
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.businesses.models.business import Business, BusinessStatus


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _make_client(db, id_number="C001", vat_type=None):
    from app.common.enums import VatType
    client = Client(
        full_name="Test Client",
        id_number=id_number,
        vat_reporting_frequency=vat_type or VatType.MONTHLY,
    )
    db.add(client)
    db.flush()
    return client


def _make_client_record(db, client_id):
    from app.clients.models.legal_entity import LegalEntity
    from app.common.enums import IdNumberType
    legal = LegalEntity(id_number=f"LE-{client_id}", id_number_type=IdNumberType.INDIVIDUAL)
    db.add(legal)
    db.flush()
    # Use client_id as pk to match ClientRecordRepository.get_by_client_id assumption
    record = ClientRecord(id=client_id, legal_entity_id=legal.id)
    db.add(record)
    db.flush()
    return record


def _make_user(db):
    user = User(
        full_name="Tester",
        email="t@t.com",
        password_hash=AuthService.hash_password("x"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _apply_wave1_backfill(db):
    db.execute(sa.text("UPDATE annual_reports SET client_record_id = client_id WHERE client_record_id IS NULL"))
    db.execute(sa.text("UPDATE vat_work_items SET client_record_id = client_id WHERE client_record_id IS NULL"))
    db.execute(sa.text("UPDATE tax_deadlines SET client_record_id = client_id WHERE client_record_id IS NULL"))
    db.execute(sa.text("UPDATE binders SET client_record_id = client_id WHERE client_record_id IS NULL"))
    db.execute(sa.text("UPDATE advance_payments SET client_record_id = client_id WHERE client_record_id IS NULL"))
    db.execute(sa.text("UPDATE businesses SET legal_entity_id = client_id WHERE legal_entity_id IS NULL"))
    db.flush()


# ── W1: AnnualReport ──────────────────────────────────────────────────────────

class TestW1AnnualReport:
    def test_repo_list_by_client_record(self, db):
        from app.annual_reports.repositories.report_repository import AnnualReportReportRepository
        from app.annual_reports.models.annual_report_enums import (
            ClientAnnualFilingType, PrimaryAnnualReportForm, AnnualReportStatus, FilingDeadlineType,
        )
        from app.annual_reports.models.annual_report_model import AnnualReport

        client = _make_client(db)
        record = _make_client_record(db, client.id)
        user = _make_user(db)

        report = AnnualReport(
            client_id=client.id,
            client_record_id=record.id,
            tax_year=2024,
            client_type=ClientAnnualFilingType.INDIVIDUAL,
            form_type=PrimaryAnnualReportForm("1301"),
            status=AnnualReportStatus.NOT_STARTED,
            deadline_type=FilingDeadlineType.STANDARD,
            created_by=user.id,
        )
        db.add(report)
        db.flush()

        repo = AnnualReportReportRepository(db)
        results = repo.list_by_client_record(record.id)
        assert len(results) == 1
        assert results[0].client_record_id == record.id

    def test_service_resolves_client_record_id_on_create(self, db):
        from app.annual_reports.services.annual_report_service import AnnualReportService

        client = _make_client(db)
        record = _make_client_record(db, client.id)
        user = _make_user(db)

        service = AnnualReportService(db)
        report = service.create_report(
            client_id=client.id,
            tax_year=2023,
            client_type="individual",
            created_by=user.id,
            created_by_name=user.full_name,
        )
        assert report.client_record_id == record.id

    def test_backfilled_legacy_row_is_visible_via_client_record_query(self, db):
        from app.annual_reports.repositories.report_repository import AnnualReportReportRepository
        from app.annual_reports.services.annual_report_service import AnnualReportService
        from app.annual_reports.models.annual_report_enums import (
            AnnualReportStatus, ClientAnnualFilingType, FilingDeadlineType, PrimaryAnnualReportForm,
        )
        from app.annual_reports.models.annual_report_model import AnnualReport

        client = _make_client(db, id_number="C101")
        _make_client_record(db, client.id)
        user = _make_user(db)
        db.add(AnnualReport(
            client_id=client.id,
            tax_year=2024,
            client_type=ClientAnnualFilingType.INDIVIDUAL,
            form_type=PrimaryAnnualReportForm("1301"),
            status=AnnualReportStatus.NOT_STARTED,
            deadline_type=FilingDeadlineType.STANDARD,
            created_by=user.id,
        ))
        db.flush()

        _apply_wave1_backfill(db)

        reports, total = AnnualReportService(db).get_client_reports(client.id)
        assert total == 1
        assert reports[0].client_id == client.id
        assert AnnualReportReportRepository(db).get_by_client_record_year(client.id, 2024) is not None


# ── W2: VatWorkItem ───────────────────────────────────────────────────────────

class TestW2VatWorkItem:
    def test_repo_list_by_client_record(self, db):
        from app.vat_reports.repositories.vat_work_item_query_repository import VatWorkItemQueryRepository
        from app.vat_reports.models.vat_work_item import VatWorkItem
        from app.vat_reports.models.vat_enums import VatWorkItemStatus
        from app.common.enums import VatType

        client = _make_client(db)
        record = _make_client_record(db, client.id)
        user = _make_user(db)

        item = VatWorkItem(
            client_id=client.id,
            client_record_id=record.id,
            period="2024-01",
            period_type=VatType.MONTHLY,
            created_by=user.id,
            status=VatWorkItemStatus.MATERIAL_RECEIVED,
        )
        db.add(item)
        db.flush()

        repo = VatWorkItemQueryRepository(db)
        results = repo.list_by_client_record(record.id)
        assert len(results) == 1
        assert results[0].client_record_id == record.id

    def test_service_sets_client_record_id_on_create(self, db):
        from app.vat_reports.services.intake import create_work_item
        from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
        from app.clients.repositories.client_repository import ClientRepository

        client = _make_client(db)
        record = _make_client_record(db, client.id)
        business = Business(
            client_id=client.id, business_name="Biz", status=BusinessStatus.ACTIVE,
            opened_at=date.today(),
        )
        db.add(business)
        db.flush()
        user = _make_user(db)

        item = create_work_item(
            VatWorkItemRepository(db),
            ClientRepository(db),
            client_id=client.id,
            period="2024-03",
            created_by=user.id,
        )
        assert item.client_record_id == record.id

    def test_backfilled_legacy_row_is_visible_via_client_record_query(self, db):
        from app.common.enums import VatType
        from app.vat_reports.models.vat_enums import VatWorkItemStatus
        from app.vat_reports.models.vat_work_item import VatWorkItem
        from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
        from app.vat_reports.services.vat_report_queries import list_client_work_items

        client = _make_client(db, id_number="C102")
        _make_client_record(db, client.id)
        user = _make_user(db)
        db.add(VatWorkItem(
            client_id=client.id,
            period="2024-08",
            period_type=VatType.MONTHLY,
            created_by=user.id,
            status=VatWorkItemStatus.MATERIAL_RECEIVED,
        ))
        db.flush()

        _apply_wave1_backfill(db)

        items = list_client_work_items(VatWorkItemRepository(db), client.id)
        assert len(items) == 1
        assert items[0].client_record_id == client.id


# ── W3: TaxDeadline ───────────────────────────────────────────────────────────

class TestW3TaxDeadline:
    def test_repo_list_by_client_record(self, db):
        from app.tax_deadline.repositories.tax_deadline_query_repository import TaxDeadlineQueryRepository
        from app.tax_deadline.models.tax_deadline import TaxDeadline, DeadlineType, TaxDeadlineStatus

        client = _make_client(db)
        record = _make_client_record(db, client.id)

        deadline = TaxDeadline(
            client_id=client.id,
            client_record_id=record.id,
            deadline_type=DeadlineType.VAT,
            due_date=date(2024, 2, 15),
            status=TaxDeadlineStatus.PENDING,
        )
        db.add(deadline)
        db.flush()

        repo = TaxDeadlineQueryRepository(db)
        results = repo.list_by_client_record(record.id)
        assert len(results) == 1
        assert results[0].client_record_id == record.id

    def test_service_sets_client_record_id_on_create(self, db):
        from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService
        from app.tax_deadline.models.tax_deadline import DeadlineType

        client = _make_client(db)
        record = _make_client_record(db, client.id)

        service = TaxDeadlineService(db)
        deadline = service.create_deadline(
            client_id=client.id,
            deadline_type=DeadlineType.VAT,
            due_date=date(2024, 3, 15),
        )
        assert deadline.client_record_id == record.id

    def test_backfilled_legacy_row_is_visible_via_client_record_query(self, db):
        from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus
        from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService

        client = _make_client(db, id_number="C103")
        _make_client_record(db, client.id)
        db.add(TaxDeadline(
            client_id=client.id,
            deadline_type=DeadlineType.VAT,
            due_date=date(2024, 9, 15),
            status=TaxDeadlineStatus.PENDING,
        ))
        db.flush()

        _apply_wave1_backfill(db)

        deadlines = TaxDeadlineService(db).get_client_deadlines(client.id)
        assert len(deadlines) == 1
        assert deadlines[0].client_record_id == client.id


# ── W4: Binder ────────────────────────────────────────────────────────────────

class TestW4Binder:
    def test_repo_list_by_client_record(self, db):
        from app.binders.repositories.binder_repository import BinderRepository
        from app.binders.models.binder import Binder, BinderStatus

        client = _make_client(db)
        record = _make_client_record(db, client.id)
        user = _make_user(db)

        binder = Binder(
            client_id=client.id,
            client_record_id=record.id,
            binder_number="1/1",
            status=BinderStatus.IN_OFFICE,
            created_by=user.id,
        )
        db.add(binder)
        db.flush()

        repo = BinderRepository(db)
        results = repo.list_by_client_record(record.id)
        assert len(results) == 1
        assert results[0].client_record_id == record.id

    def test_intake_sets_client_record_id_on_create(self, db):
        from app.binders.services.binder_intake_service import BinderIntakeService

        client = _make_client(db)
        record = _make_client_record(db, client.id)
        user = _make_user(db)
        client.office_client_number = 99
        db.flush()

        business = Business(
            client_id=client.id, business_name="B", status=BusinessStatus.ACTIVE,
            opened_at=date.today(),
        )
        db.add(business)
        db.flush()

        service = BinderIntakeService(db)
        binder, _, _ = service.receive(
            client_id=client.id,
            received_at=date.today(),
            received_by=user.id,
        )
        assert binder.client_record_id == record.id

    def test_backfilled_legacy_row_is_visible_via_client_record_query(self, db):
        from app.binders.models.binder import Binder, BinderStatus
        from app.binders.services.binder_operations_service import BinderOperationsService

        client = _make_client(db, id_number="C104")
        _make_client_record(db, client.id)
        user = _make_user(db)
        db.add(Binder(
            client_id=client.id,
            binder_number="99/1",
            status=BinderStatus.IN_OFFICE,
            created_by=user.id,
        ))
        db.flush()

        _apply_wave1_backfill(db)

        items, total = BinderOperationsService(db).get_client_binders(client.id)
        assert total == 1
        assert items[0].client_record_id == client.id


# ── W5: AdvancePayment ────────────────────────────────────────────────────────

class TestW5AdvancePayment:
    def test_repo_list_by_client_record_year(self, db):
        from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
        from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus

        client = _make_client(db)
        record = _make_client_record(db, client.id)

        payment = AdvancePayment(
            client_id=client.id,
            client_record_id=record.id,
            period="2024-01",
            period_months_count=1,
            due_date=date(2024, 1, 15),
            paid_amount=0,
            status=AdvancePaymentStatus.PENDING,
        )
        db.add(payment)
        db.flush()

        repo = AdvancePaymentRepository(db)
        items, total = repo.list_by_client_record_year(record.id, 2024)
        assert total == 1
        assert items[0].client_record_id == record.id

    def test_service_sets_client_record_id_on_create(self, db):
        from app.advance_payments.services.advance_payment_service import AdvancePaymentService

        client = _make_client(db)
        record = _make_client_record(db, client.id)

        service = AdvancePaymentService(db)
        payment = service.create_payment_for_client(
            client_id=client.id,
            period="2024-06",
            period_months_count=1,
            due_date=date(2024, 6, 15),
            expected_amount=1000,
        )
        assert payment.client_record_id == record.id

    def test_fallback_when_no_client_record(self, db):
        from app.advance_payments.services.advance_payment_service import AdvancePaymentService

        client = _make_client(db, id_number="C006")

        service = AdvancePaymentService(db)
        payment = service.create_payment_for_client(
            client_id=client.id,
            period="2024-07",
            period_months_count=1,
            due_date=date(2024, 7, 15),
            expected_amount=500,
        )
        assert payment.client_record_id is None
        assert payment.client_id == client.id

    def test_backfilled_legacy_row_is_visible_via_client_record_query(self, db):
        from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
        from app.advance_payments.services.advance_payment_service import AdvancePaymentService

        client = _make_client(db, id_number="C105")
        _make_client_record(db, client.id)
        db.add(AdvancePayment(
            client_id=client.id,
            period="2024-10",
            period_months_count=1,
            due_date=date(2024, 10, 15),
            paid_amount=0,
            status=AdvancePaymentStatus.PENDING,
        ))
        db.flush()

        _apply_wave1_backfill(db)

        items, total = AdvancePaymentService(db).list_payments_for_client(client.id, year=2024)
        assert total == 1
        assert items[0].client_record_id == client.id
