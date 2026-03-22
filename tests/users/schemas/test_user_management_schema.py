import pytest
from pydantic import ValidationError

from app.users.schemas.user_management import UserUpdateRequest


def test_user_update_request_requires_at_least_one_field():
    with pytest.raises(ValidationError):
        UserUpdateRequest()


def test_user_update_request_accepts_single_field():
    parsed = UserUpdateRequest(full_name="Renamed")
    assert parsed.full_name == "Renamed"
