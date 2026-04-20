from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.correspondence.models.correspondence import CorrespondenceType
from app.correspondence.schemas.correspondence import (
    CorrespondenceCreateRequest,
    CorrespondenceListResponse,
    CorrespondenceResponse,
    CorrespondenceUpdateRequest,
)


def test_create_schema_rejects_future_occurred_at():
    with pytest.raises(ValidationError):
        CorrespondenceCreateRequest(
            correspondence_type=CorrespondenceType.CALL,
            subject="future",
            occurred_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )


def test_update_schema_allows_none_occurred_at_and_rejects_future():
    req = CorrespondenceUpdateRequest(occurred_at=None)
    assert req.occurred_at is None

    with pytest.raises(ValidationError):
        CorrespondenceUpdateRequest(
            occurred_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )


def test_list_response_build_calculates_total_pages():
    item = CorrespondenceResponse(
        id=1,
        client_id=1,
        business_id=1,
        contact_id=None,
        correspondence_type=CorrespondenceType.EMAIL,
        subject="s",
        notes=None,
        occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        created_by=1,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    resp = CorrespondenceListResponse.build(items=[item], page=1, page_size=20, total=41)
    assert resp.total_pages == 3

    empty = CorrespondenceListResponse.build(items=[], page=1, page_size=0, total=0)
    assert empty.total_pages == 0
