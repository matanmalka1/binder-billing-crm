"""Layer 2 integrity constraint tests.

Step 1: Unique constraints reject duplicates at DB level.
Step 2: Generator deduplicates by (client_record_id, deadline_type, period/None).
"""

from datetime import date
from itertools import count

import pytest
from sqlalchemy.exc import IntegrityError

from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import EntityType, IdNumberType, VatType
from app.annual_reports.models.annual_report_model import AnnualReport
from app.annual_reports.models.annual_report_enums import (
    AnnualReportStatus, ClientAnnualFilingType, FilingDeadlineType, PrimaryAnnualReportForm,
)
from app.tax_deadline.models.tax_deadline import TaxDeadline, DeadlineType, TaxDeadlineStatus
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.businesses.models.business import Business
from app.tax_deadline.services.deadline_generator import DeadlineGeneratorService

_seq = count(1)


def _user(db) -> User:
    u = User(
        full_name="Test User",
        email=f"u{next(_seq)}@test.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _setup_client(db, vat_type=VatType.MONTHLY) -> tuple:
    """Create Client + LegalEntity + ClientRecord + Business. Returns (client, client_record)."""
    idx = next(_seq)
    le = LegalEntity(
        id_number=f"LE{idx:06d}",
        id_number_type=IdNumberType.CORPORATION,
        entity_type=EntityType.COMPANY_LTD,
        vat_reporting_frequency=vat_type,
    )
    db.add(le)
    db.flush()

    client = Client(
        full_name=f"Layer2 Client {idx}",
        id_number=f"LE{idx:06d}",
        vat_reporting_frequency=vat_type,
        entity_type=EntityType.COMPANY_LTD,
    )
    db.add(client)
    db.flush()

    cr = ClientRecord(id=client.id, legal_entity_id=le.id)
    db.add(cr)

    user = _user(db)
    biz = Business(client_id=client.id, business_name=client.full_name, opened_at=date(2026, 1, 1))
    db.add(biz)
    db.commit()
    db.refresh(client)
    db.refresh(cr)
    return client, cr


# ── Step 1: Unique constraint enforcement ─────────────────────────────────────

def test_annual_report_unique_client_record_tax_year(test_db):
    """DB rejects duplicate (client_record_id, tax_year) for non-deleted annual reports."""
    client, cr = _setup_client(test_db)

    def _report():
        return AnnualReport(
            client_id=client.id,
            client_record_id=cr.id,
            tax_year=2025,
            client_type=ClientAnnualFilingType.INDIVIDUAL,
            form_type=PrimaryAnnualReportForm.FORM_1301,
            status=AnnualReportStatus.NOT_STARTED,
            deadline_type=FilingDeadlineType.STANDARD,
        )

    test_db.add(_report())
    test_db.flush()

    test_db.add(_report())
    with pytest.raises(IntegrityError):
        test_db.flush()


def test_vat_work_item_unique_client_record_period(test_db):
    """DB rejects duplicate (client_record_id, period) for non-deleted VAT work items."""
    client, cr = _setup_client(test_db)
    user = _user(test_db)

    def _item():
        return VatWorkItem(
            client_id=client.id,
            client_record_id=cr.id,
            created_by=user.id,
            period="2025-01",
            period_type=VatType.MONTHLY,
            status=VatWorkItemStatus.MATERIAL_RECEIVED,
        )

    test_db.add(_item())
    test_db.flush()

    test_db.add(_item())
    with pytest.raises(IntegrityError):
        test_db.flush()


def test_tax_deadline_exists_by_record_detects_duplicate_period(test_db):
    """exists_by_record returns True when same (client_record_id, deadline_type, period) exists."""
    from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository

    client, cr = _setup_client(test_db)
    repo = TaxDeadlineRepository(test_db)

    test_db.add(TaxDeadline(
        client_id=client.id,
        client_record_id=cr.id,
        deadline_type=DeadlineType.VAT,
        period="2025-01",
        due_date=date(2025, 2, 15),
        status=TaxDeadlineStatus.PENDING,
    ))
    test_db.flush()

    assert repo.exists_by_record(cr.id, DeadlineType.VAT, period="2025-01") is True
    assert repo.exists_by_record(cr.id, DeadlineType.VAT, period="2025-02") is False


def test_tax_deadline_exists_by_record_detects_duplicate_annual(test_db):
    """exists_by_record returns True when same (client_record_id, annual_report, period=None) exists."""
    from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository

    client, cr = _setup_client(test_db)
    repo = TaxDeadlineRepository(test_db)

    test_db.add(TaxDeadline(
        client_id=client.id,
        client_record_id=cr.id,
        deadline_type=DeadlineType.ANNUAL_REPORT,
        period=None,
        due_date=date(2025, 4, 30),
        status=TaxDeadlineStatus.PENDING,
    ))
    test_db.flush()

    assert repo.exists_by_record(cr.id, DeadlineType.ANNUAL_REPORT) is True
    assert repo.exists_by_record(cr.id, DeadlineType.VAT) is False


# ── Step 2: Generator deduplication by domain identity ────────────────────────

def test_generator_vat_dedup_by_client_record_period(test_db):
    """Generator skips VAT deadline if same (client_record_id, period) exists, even different due_date."""
    client, cr = _setup_client(test_db, vat_type=VatType.MONTHLY)

    # Pre-insert a VAT deadline for 2026-05 with a different due_date
    existing = TaxDeadline(
        client_id=client.id,
        client_record_id=cr.id,
        deadline_type=DeadlineType.VAT,
        period="2026-05",
        due_date=date(2026, 6, 1),  # different from standard day
        status=TaxDeadlineStatus.PENDING,
    )
    test_db.add(existing)
    test_db.commit()

    service = DeadlineGeneratorService(test_db)
    created = service.generate_vat_deadlines(client.id, 2026)

    periods_created = {d.period for d in created}
    assert "2026-05" not in periods_created, "Generator must skip period already covered by client_record"


def test_generator_annual_dedup_by_client_record(test_db):
    """Generator skips annual report deadline if one already exists for client_record."""
    client, cr = _setup_client(test_db)

    existing = TaxDeadline(
        client_id=client.id,
        client_record_id=cr.id,
        deadline_type=DeadlineType.ANNUAL_REPORT,
        period=None,
        due_date=date(2027, 4, 30),
        status=TaxDeadlineStatus.PENDING,
    )
    test_db.add(existing)
    test_db.commit()

    service = DeadlineGeneratorService(test_db)
    result = service.generate_annual_report_deadline(client.id, 2026)

    assert result == [], "Generator must skip annual when client_record already has one"
