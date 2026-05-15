from datetime import datetime, UTC
from types import SimpleNamespace

from app.notification.models.notification import (
    NotificationChannel,
    NotificationSeverity,
    NotificationStatus,
    NotificationTrigger,
)
from app.notification.services.notification_service import NotificationService


def test_list_paginated_enriches_names(test_db):
    service = NotificationService(test_db)
    n1 = SimpleNamespace(
        id=1,
        client_record_id=8,
        business_id=4,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="a@x.com",
        content_snapshot="x",
        severity=NotificationSeverity.INFO,
        status=NotificationStatus.PENDING,
        sent_at=None,
        failed_at=None,
        error_message=None,
        retry_count=0,
        triggered_by=None,
        created_at=datetime.now(UTC),
    )
    service.notification_repo = SimpleNamespace(
        list_paginated=lambda **kwargs: ([n1], 1),
    )
    service.business_repo = SimpleNamespace(
        list_by_ids=lambda ids: [SimpleNamespace(id=4, full_name="Biz 4")],
    )

    items, total = service.list_paginated(page=2, page_size=10, business_id=4)
    assert total == 1
    assert items[0].business_name == "Biz 4"
