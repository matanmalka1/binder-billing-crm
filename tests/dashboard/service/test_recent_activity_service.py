from datetime import UTC, datetime
from types import SimpleNamespace

from app.audit.constants import (
    ACTION_CREATED,
    ACTION_STATUS_CHANGED,
    ENTITY_ANNUAL_REPORT,
    ENTITY_CHARGE,
    ENTITY_CLIENT,
)
from app.binders.models.binder import BinderStatus
from app.dashboard.services.recent_activity_service import RecentActivityService


class _BatchOnlyRepo:
    def __init__(self, rows):
        self.rows = rows
        self.requested_ids = None

    def get_by_ids(self, ids):
        self.requested_ids = set(ids)
        return {entity_id: self.rows[entity_id] for entity_id in ids if entity_id in self.rows}

    def get_by_id(self, _entity_id):
        raise AssertionError("recent activity must batch-load related entities")


def test_recent_activity_batches_related_entity_lookups(monkeypatch):
    now = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)
    service = RecentActivityService(object())
    service.charge_repo = _BatchOnlyRepo({10: SimpleNamespace(client_record_id=101)})
    service.report_repo = _BatchOnlyRepo({20: SimpleNamespace(client_record_id=102)})
    service.binder_repo = _BatchOnlyRepo({30: SimpleNamespace(client_record_id=103)})
    service.repo = SimpleNamespace(
        list_recent=lambda _limit: [
            SimpleNamespace(
                id=1,
                entity_type=ENTITY_CLIENT,
                entity_id=100,
                action=ACTION_CREATED,
                note=None,
                performed_at=now,
            ),
            SimpleNamespace(
                id=2,
                entity_type=ENTITY_CHARGE,
                entity_id=10,
                action=ACTION_CREATED,
                note=None,
                performed_at=now,
            ),
            SimpleNamespace(
                id=3,
                entity_type=ENTITY_ANNUAL_REPORT,
                entity_id=20,
                action=ACTION_STATUS_CHANGED,
                note=None,
                performed_at=now,
            ),
        ]
    )
    service.binder_status_log_repo = SimpleNamespace(
        list_recent=lambda _limit: [
            SimpleNamespace(
                id=4,
                binder_id=30,
                new_status=BinderStatus.READY_FOR_PICKUP.value,
                changed_at=now,
            )
        ]
    )
    monkeypatch.setattr(
        "app.dashboard.services.recent_activity_service.get_full_records_bulk",
        lambda _db, ids: {client_id: {"full_name": f"לקוח {client_id}"} for client_id in ids},
    )

    items = service.build()

    assert len(items) == 4
    assert service.charge_repo.requested_ids == {10}
    assert service.report_repo.requested_ids == {20}
    assert service.binder_repo.requested_ids == {30}
