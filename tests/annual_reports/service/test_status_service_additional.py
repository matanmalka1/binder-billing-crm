from datetime import date, datetime
from types import SimpleNamespace

import pytest

from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.annual_reports.services.annual_report_service import AnnualReportService
from app.businesses.models.business import Business, BusinessStatus
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import IdNumberType
from app.core.exceptions import AppError


def _create_report(db):
    crm_client = Client(
        full_name="AR Status Additional",
        id_number="ARSTAT001",

    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    legal = LegalEntity(id_number="LE-ARSTAT001", id_number_type=IdNumberType.INDIVIDUAL, official_name="Test Entity")
    db.add(legal)
    db.flush()
    db.add(ClientRecord(id=crm_client.id, legal_entity_id=legal.id))
    db.flush()
    db.add(
        Business(
            client_id=crm_client.id,
            legal_entity_id=legal.id,
            business_name=crm_client.full_name,
            status=BusinessStatus.ACTIVE,
            opened_at=date.today(),
        )
    )
    db.flush()

    report = AnnualReportService(db).create_report(
        client_record_id=crm_client.id,
        tax_year=2026,
        client_type="corporation",
        created_by=1,
        created_by_name="Tester",
        deadline_type="standard",
        notes=None,
    )
    return report


def test_transition_submitted_requires_readiness(test_db, monkeypatch):
    report = _create_report(test_db)
    svc = AnnualReportService(test_db)

    # move to pending_client so submitted transition is valid
    class _SigSvc:
        def __init__(self, db):
            self.db = db

        def create_request(self, **kwargs):
            return SimpleNamespace(id=1)

        def cancel_request(self, **kwargs):
            return None

    class _SigRepo:
        def __init__(self, db):
            self.db = db

        def list_pending_by_annual_report(self, report_id):
            return []

    import app.signature_requests.services.signature_request_service as sig_service_mod
    import app.signature_requests.repositories.signature_request_repository as sig_repo_mod

    monkeypatch.setattr(sig_service_mod, "SignatureRequestService", _SigSvc)
    monkeypatch.setattr(sig_repo_mod, "SignatureRequestRepository", _SigRepo)

    svc.transition_status(report.id, "collecting_docs", 1, "A")
    svc.transition_status(report.id, "docs_complete", 1, "A")
    svc.transition_status(report.id, "in_preparation", 1, "A")
    svc.transition_status(report.id, "pending_client", 1, "A")

    class _FinSvc:
        def __init__(self, db):
            self.db = db

        def get_readiness_check(self, report_id):
            return SimpleNamespace(is_ready=False, issues=["missing docs", "no totals"])

    import app.annual_reports.services.financial_service as fin_mod

    monkeypatch.setattr(fin_mod, "AnnualReportFinancialService", _FinSvc)

    with pytest.raises(AppError) as exc:
        svc.transition_status(report.id, "submitted", 1, "A")

    assert exc.value.code == "ANNUAL_REPORT.INVALID_STATUS"


def test_pending_client_transition_calls_signature_hooks(test_db, monkeypatch):
    report = _create_report(test_db)
    svc = AnnualReportService(test_db)

    svc.transition_status(report.id, "collecting_docs", 1, "A")
    svc.transition_status(report.id, "docs_complete", 1, "A")

    called = {"created": 0, "canceled": 0}

    class _SigSvc:
        def __init__(self, db):
            self.db = db

        def create_request(self, **kwargs):
            called["created"] += 1
            return SimpleNamespace(id=1)

        def cancel_request(self, **kwargs):
            called["canceled"] += 1

    class _SigRepo:
        def __init__(self, db):
            self.db = db

        def list_pending_by_annual_report(self, report_id):
            return [SimpleNamespace(id=10)]

    import app.signature_requests.services.signature_request_service as sig_service_mod
    import app.signature_requests.repositories.signature_request_repository as sig_repo_mod

    monkeypatch.setattr(sig_service_mod, "SignatureRequestService", _SigSvc)
    monkeypatch.setattr(sig_repo_mod, "SignatureRequestRepository", _SigRepo)

    svc.transition_status(report.id, "in_preparation", 1, "A")
    result = svc.transition_status(report.id, "pending_client", 1, "A")

    assert result.status == AnnualReportStatus.PENDING_CLIENT.value
    assert called["created"] == 1
    assert called["canceled"] >= 1


def test_transition_rejects_unknown_status(test_db):
    report = _create_report(test_db)
    svc = AnnualReportService(test_db)

    with pytest.raises(AppError) as exc:
        svc.transition_status(report.id, "not-a-status", 1, "A")
    assert exc.value.code == "ANNUAL_REPORT.INVALID_STATUS"


def test_transition_from_pending_client_cancels_requests(test_db, monkeypatch):
    report = _create_report(test_db)
    svc = AnnualReportService(test_db)

    class _SigSvc:
        def __init__(self, db):
            self.db = db

        def create_request(self, **kwargs):
            return SimpleNamespace(id=1)

        def cancel_request(self, **kwargs):
            return None

    class _SigRepo:
        def __init__(self, db):
            self.db = db

        def list_pending_by_annual_report(self, report_id):
            return [SimpleNamespace(id=9)]

    import app.signature_requests.services.signature_request_service as sig_service_mod
    import app.signature_requests.repositories.signature_request_repository as sig_repo_mod
    import app.annual_reports.services.financial_service as fin_mod

    monkeypatch.setattr(sig_service_mod, "SignatureRequestService", _SigSvc)
    monkeypatch.setattr(sig_repo_mod, "SignatureRequestRepository", _SigRepo)
    monkeypatch.setattr(
        fin_mod,
        "AnnualReportFinancialService",
        lambda db: SimpleNamespace(
            get_readiness_check=lambda _rid: SimpleNamespace(is_ready=True, issues=[]),
        ),
    )

    svc.transition_status(report.id, "collecting_docs", 1, "A")
    svc.transition_status(report.id, "docs_complete", 1, "A")
    svc.transition_status(report.id, "in_preparation", 1, "A")
    svc.transition_status(report.id, "pending_client", 1, "A")
    submitted_at = datetime(2026, 1, 10, 12, 0, 0)
    moved = svc.transition_status(
        report.id,
        "submitted",
        1,
        "A",
        submitted_at=submitted_at,
        ita_reference="ITA-123",
    )
    assert moved.status == AnnualReportStatus.SUBMITTED.value
    assert moved.ita_reference == "ITA-123"


def test_update_deadline_invalid_and_custom_paths(test_db):
    report = _create_report(test_db)
    svc = AnnualReportService(test_db)

    with pytest.raises(AppError) as exc:
        svc.update_deadline(report.id, "bad", 1, "A")
    assert exc.value.code == "ANNUAL_REPORT.INVALID_TYPE"

    updated = svc.update_deadline(
        report.id,
        "custom",
        1,
        "A",
        custom_deadline_note="manual date handled externally",
    )
    assert updated.deadline_type == "custom"

    std = svc.update_deadline(report.id, "standard", 1, "A")
    assert std.deadline_type == "standard"


def test_transition_assessment_issued_sets_financial_fields(test_db):
    report = _create_report(test_db)
    svc = AnnualReportService(test_db)
    svc.repo.update(report.id, status=AnnualReportStatus.SUBMITTED)

    updated = svc.transition_status(
        report.id,
        "assessment_issued",
        1,
        "A",
        assessment_amount=111.0,
        refund_due=22.0,
        tax_due=33.0,
    )
    assert updated.status == AnnualReportStatus.ASSESSMENT_ISSUED.value
    assert float(updated.assessment_amount) == 111.0
