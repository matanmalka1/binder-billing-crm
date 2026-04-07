from types import SimpleNamespace

from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.signature_requests.services.signature_request_service import SignatureRequestService


def test_service_sign_request_triggers_auto_advance_and_audit(monkeypatch, test_db):
    service = SignatureRequestService(test_db)
    signed_req = SimpleNamespace(id=1, signer_name="Client", status="signed")

    captured = {"audit_called": False, "advanced_id": None}

    monkeypatch.setattr(
        "app.signature_requests.services.signer_actions.sign_request",
        lambda repo, **kwargs: (signed_req, 88, "now"),
    )
    monkeypatch.setattr(
        service.repo,
        "append_audit_event",
        lambda **kwargs: captured.__setitem__("audit_called", kwargs["event_type"] == "annual_report_signed"),
    )
    monkeypatch.setattr(
        service,
        "_auto_advance_annual_report",
        lambda annual_report_id, now: captured.__setitem__("advanced_id", annual_report_id),
    )

    out = service.sign_request(token="abc")

    assert out is signed_req
    assert captured["audit_called"] is True
    assert captured["advanced_id"] == 88


def test_service_sign_request_without_annual_report_skips_auto_advance(monkeypatch, test_db):
    service = SignatureRequestService(test_db)
    signed_req = SimpleNamespace(id=2, signer_name="Client", status="signed")

    captured = {"audit_calls": 0, "advanced_calls": 0}

    monkeypatch.setattr(
        "app.signature_requests.services.signer_actions.sign_request",
        lambda repo, **kwargs: (signed_req, None, None),
    )
    monkeypatch.setattr(
        service.repo,
        "append_audit_event",
        lambda **kwargs: captured.__setitem__("audit_calls", captured["audit_calls"] + 1),
    )
    monkeypatch.setattr(
        service,
        "_auto_advance_annual_report",
        lambda annual_report_id, now: captured.__setitem__("advanced_calls", captured["advanced_calls"] + 1),
    )

    out = service.sign_request(token="abc")

    assert out is signed_req
    assert captured["audit_calls"] == 0
    assert captured["advanced_calls"] == 0


def test_auto_advance_noop_when_report_not_pending_client(monkeypatch, test_db):
    class _Svc:
        def __init__(self, db):
            self.db = db
            self.repo = SimpleNamespace(get_by_id=lambda _id: SimpleNamespace(status=AnnualReportStatus.SUBMITTED))

        def transition_status(self, **kwargs):  # pragma: no cover - should not execute
            raise AssertionError("transition_status should not be called")

    class _DetailRepo:
        def __init__(self, db):
            self.db = db

        def upsert(self, *_args, **_kwargs):  # pragma: no cover - should not execute
            raise AssertionError("upsert should not be called")

    import app.annual_reports.services.annual_report_service as svc_mod

    monkeypatch.setattr(svc_mod, "AnnualReportService", _Svc)
    monkeypatch.setattr(
        "app.annual_reports.repositories.detail_repository.AnnualReportDetailRepository",
        _DetailRepo,
    )

    SignatureRequestService(test_db)._auto_advance_annual_report(annual_report_id=10, now=object())


def test_auto_advance_transitions_and_sets_client_approved_at(monkeypatch, test_db):
    calls = {"transition": None, "upsert": None}

    class _Svc:
        def __init__(self, db):
            self.db = db
            self.repo = SimpleNamespace(get_by_id=lambda _id: SimpleNamespace(status=AnnualReportStatus.PENDING_CLIENT))

        def transition_status(self, **kwargs):
            calls["transition"] = kwargs

    class _DetailRepo:
        def __init__(self, db):
            self.db = db

        def upsert(self, annual_report_id, **kwargs):
            calls["upsert"] = (annual_report_id, kwargs)

    import app.annual_reports.services.annual_report_service as svc_mod

    monkeypatch.setattr(svc_mod, "AnnualReportService", _Svc)
    monkeypatch.setattr(
        "app.annual_reports.repositories.detail_repository.AnnualReportDetailRepository",
        _DetailRepo,
    )

    now_obj = object()
    SignatureRequestService(test_db)._auto_advance_annual_report(annual_report_id=10, now=now_obj)

    assert calls["transition"] is not None
    assert calls["transition"]["new_status"] == AnnualReportStatus.SUBMITTED.value
    assert calls["upsert"] == (10, {"client_approved_at": now_obj})


def test_auto_advance_swallows_internal_exceptions(monkeypatch, test_db):
    class _Svc:
        def __init__(self, db):
            raise RuntimeError("boom")

    import app.annual_reports.services.annual_report_service as svc_mod

    monkeypatch.setattr(svc_mod, "AnnualReportService", _Svc)
    SignatureRequestService(test_db)._auto_advance_annual_report(annual_report_id=10, now=object())
