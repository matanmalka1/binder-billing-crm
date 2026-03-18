from app.charge.services.bulk_billing_service import BulkBillingService


class _FakeBilling:
    def __init__(self, failures=None):
        self.failures = failures or set()
        self.calls = []

    def issue_charge(self, charge_id, actor_id=None):
        self.calls.append(("issue", charge_id, actor_id, None))
        if charge_id in self.failures:
            raise RuntimeError("issue failed")

    def mark_charge_paid(self, charge_id, actor_id=None):
        self.calls.append(("mark-paid", charge_id, actor_id, None))
        if charge_id in self.failures:
            raise RuntimeError("paid failed")

    def cancel_charge(self, charge_id, actor_id=None, reason=None):
        self.calls.append(("cancel", charge_id, actor_id, reason))
        if charge_id in self.failures:
            raise RuntimeError("cancel failed")


def test_bulk_action_issue_collects_success_and_failures(monkeypatch):
    fake = _FakeBilling(failures={2})
    service = BulkBillingService(db=None)
    service.billing = fake

    succeeded, failed = service.bulk_action([1, 2, 3], action="issue", actor_id=99)

    assert succeeded == [1, 3]
    assert [f.id for f in failed] == [2]
    assert "issue failed" in failed[0].error


def test_bulk_action_mark_paid_and_cancel_paths():
    service = BulkBillingService(db=None)
    fake = _FakeBilling()
    service.billing = fake

    ok_paid, failed_paid = service.bulk_action([10], action="mark-paid", actor_id=7)
    ok_cancel, failed_cancel = service.bulk_action([11], action="cancel", actor_id=8, cancellation_reason="dup")

    assert ok_paid == [10]
    assert failed_paid == []
    assert ok_cancel == [11]
    assert failed_cancel == []
    assert ("mark-paid", 10, 7, None) in fake.calls
    assert ("cancel", 11, 8, "dup") in fake.calls
