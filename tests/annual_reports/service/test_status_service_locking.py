"""
Tests verifying that AnnualReportStatusService transition methods use the
locked fetch path (get_by_id_for_update) and correctly enforce state guards.

Note: SQLite does not support real SELECT … FOR UPDATE blocking.
Tests verify code path (monkeypatch spy) and invalid-state handling only.
"""
from types import SimpleNamespace

import pytest

from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.annual_reports.services.annual_report_service import AnnualReportService
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import IdNumberType
from app.core.exceptions import AppError


def _stub_sig_service():
    """Return stub classes that prevent cross-domain calls in status_service."""
    class _SigSvc:
        def __init__(self, db):
            pass
        def create_request(self, **kwargs):
            return SimpleNamespace(id=1)
        def cancel_request(self, **kwargs):
            pass

    class _SigRepo:
        def __init__(self, db):
            pass
        def list_pending_by_annual_report(self, report_id):
            return []

    return _SigSvc, _SigRepo


def _create_report(db):
    client = Client(full_name="Locking AR Client", id_number="ARLOCK001")
    db.add(client)
    db.commit()
    db.refresh(client)
    legal = LegalEntity(id_number="LE-ARLOCK001", id_number_type=IdNumberType.INDIVIDUAL)
    db.add(legal)
    db.flush()
    db.add(ClientRecord(id=client.id, legal_entity_id=legal.id))
    db.flush()
    return AnnualReportService(db).create_report(
        client_id=client.id,
        tax_year=2027,
        client_type="corporation",
        created_by=1,
        created_by_name="Tester",
        deadline_type="standard",
        notes=None,
    )


# ── Code-path verification ────────────────────────────────────────────────────

def test_transition_status_uses_locked_fetch(test_db, monkeypatch):
    import app.signature_requests.services.signature_request_service as sig_svc_mod
    import app.signature_requests.repositories.signature_request_repository as sig_repo_mod
    _SigSvc, _SigRepo = _stub_sig_service()
    monkeypatch.setattr(sig_svc_mod, "SignatureRequestService", _SigSvc)
    monkeypatch.setattr(sig_repo_mod, "SignatureRequestRepository", _SigRepo)

    report = _create_report(test_db)
    svc = AnnualReportService(test_db)

    calls = []
    original = svc.repo.get_by_id_for_update
    monkeypatch.setattr(
        svc.repo, "get_by_id_for_update",
        lambda rid: calls.append(rid) or original(rid),
    )

    svc.transition_status(
        report_id=report.id,
        new_status=AnnualReportStatus.COLLECTING_DOCS.value,
        changed_by=1,
        changed_by_name="Tester",
    )
    assert report.id in calls, "transition_status must call get_by_id_for_update"


def test_update_deadline_uses_locked_fetch(test_db, monkeypatch):
    report = _create_report(test_db)
    svc = AnnualReportService(test_db)

    calls = []
    original = svc.repo.get_by_id_for_update
    monkeypatch.setattr(
        svc.repo, "get_by_id_for_update",
        lambda rid: calls.append(rid) or original(rid),
    )

    svc.update_deadline(
        report_id=report.id,
        deadline_type="extended",
        changed_by=1,
        changed_by_name="Tester",
    )
    assert report.id in calls, "update_deadline must call get_by_id_for_update"


# ── Invalid-state guard ───────────────────────────────────────────────────────

def test_transition_to_same_status_raises(test_db, monkeypatch):
    """Transitioning to the current status (or any invalid transition) raises."""
    import app.signature_requests.services.signature_request_service as sig_svc_mod
    import app.signature_requests.repositories.signature_request_repository as sig_repo_mod
    _SigSvc, _SigRepo = _stub_sig_service()
    monkeypatch.setattr(sig_svc_mod, "SignatureRequestService", _SigSvc)
    monkeypatch.setattr(sig_repo_mod, "SignatureRequestRepository", _SigRepo)

    report = _create_report(test_db)
    svc = AnnualReportService(test_db)

    # report starts at NOT_STARTED; transitioning back to NOT_STARTED is not a valid transition
    with pytest.raises(AppError) as exc:
        svc.transition_status(
            report_id=report.id,
            new_status=AnnualReportStatus.NOT_STARTED.value,
            changed_by=1,
            changed_by_name="Tester",
        )
    assert exc.value.code == "ANNUAL_REPORT.INVALID_STATUS"


def test_auto_advance_skips_non_pending_client(test_db):
    """_auto_advance_annual_report is a no-op when report status != PENDING_CLIENT."""
    from app.signature_requests.services.signature_request_service import SignatureRequestService

    report = _create_report(test_db)
    sig_request_svc = SignatureRequestService(test_db)

    # report starts at NOT_STARTED — auto-advance must be a silent no-op
    # (raises nothing, does not change report status)
    sig_request_svc._auto_advance_annual_report(report.id, None)

    updated = AnnualReportService(test_db).repo.get_by_id(report.id)
    assert updated.status == AnnualReportStatus.NOT_STARTED, (
        "status must remain NOT_STARTED — auto-advance should skip non-PENDING_CLIENT reports"
    )
