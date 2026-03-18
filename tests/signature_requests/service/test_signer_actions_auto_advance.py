from types import SimpleNamespace

from app.signature_requests.services import signer_actions
from app.signature_requests.models.signature_request import SignatureRequestStatus


class _Repo:
    def __init__(self):
        self.db = object()
        self.events = []

    def update(self, req_id, **fields):
        req = SimpleNamespace(id=req_id, signer_name="Client", annual_report_id=88, **fields)
        return req

    def append_audit_event(self, **kwargs):
        self.events.append(kwargs)


def test_sign_request_triggers_annual_report_auto_advance(monkeypatch):
    req = SimpleNamespace(id=1, signer_name="Client", annual_report_id=88)
    repo = _Repo()

    monkeypatch.setattr(signer_actions, "get_by_token_or_raise", lambda repo, token: req)
    monkeypatch.setattr(signer_actions, "assert_signable", lambda repo, req: None)

    called = {"annual_report_id": None}
    monkeypatch.setattr(
        signer_actions,
        "_auto_advance_annual_report",
        lambda db, annual_report_id, now: called.__setitem__("annual_report_id", annual_report_id),
    )

    signed = signer_actions.sign_request(repo, token="abc")

    assert signed.status == SignatureRequestStatus.SIGNED
    assert called["annual_report_id"] == 88
    event_types = [e["event_type"] for e in repo.events]
    assert "signed" in event_types
    assert "annual_report_signed" in event_types


def test_sign_request_without_annual_report_does_not_auto_advance(monkeypatch):
    req = SimpleNamespace(id=2, signer_name="Client", annual_report_id=None)
    repo = _Repo()
    repo.update = lambda req_id, **fields: SimpleNamespace(  # type: ignore[method-assign]
        id=req_id, signer_name="Client", annual_report_id=None, **fields
    )

    monkeypatch.setattr(signer_actions, "get_by_token_or_raise", lambda repo, token: req)
    monkeypatch.setattr(signer_actions, "assert_signable", lambda repo, req: None)

    called = {"count": 0}
    monkeypatch.setattr(
        signer_actions,
        "_auto_advance_annual_report",
        lambda db, annual_report_id, now: called.__setitem__("count", called["count"] + 1),
    )

    signed = signer_actions.sign_request(repo, token="abc")

    assert signed.status == SignatureRequestStatus.SIGNED
    assert called["count"] == 0
    assert "annual_report_signed" not in [e["event_type"] for e in repo.events]


def test_auto_advance_noop_when_report_not_pending_client(monkeypatch):
    class _Svc:
        def __init__(self, db):
            self.db = db
            self.repo = SimpleNamespace(get_by_id=lambda _id: SimpleNamespace(status="submitted"))

        def transition_status(self, **kwargs):  # pragma: no cover - should not execute
            raise AssertionError("transition_status should not be called")

    class _DetailRepo:
        def __init__(self, db):
            self.db = db

        def upsert(self, *_args, **_kwargs):  # pragma: no cover - should not execute
            raise AssertionError("upsert should not be called")

    import app.annual_reports.services.annual_report_service as svc_mod
    import app.annual_reports.repositories as repos_mod

    monkeypatch.setattr(svc_mod, "AnnualReportService", _Svc)
    monkeypatch.setattr(repos_mod, "AnnualReportDetailRepository", _DetailRepo)

    signer_actions._auto_advance_annual_report(object(), annual_report_id=10, now=object())


def test_auto_advance_swallows_internal_exceptions(monkeypatch):
    class _Svc:
        def __init__(self, db):
            raise RuntimeError("boom")

    import app.annual_reports.services.annual_report_service as svc_mod

    monkeypatch.setattr(svc_mod, "AnnualReportService", _Svc)
    signer_actions._auto_advance_annual_report(object(), annual_report_id=10, now=object())
