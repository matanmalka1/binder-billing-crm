import pytest
from pydantic import ValidationError

from app.common.enums import IdNumberType
from app.clients.schemas.client import ClientCreateRequest


def test_client_create_request_rejects_non_digits():
    with pytest.raises(ValidationError):
        ClientCreateRequest(full_name="Bad", id_number="12A456789")


def test_client_create_request_rejects_invalid_length():
    with pytest.raises(ValidationError):
        ClientCreateRequest(full_name="Bad", id_number="12345")


def test_client_create_request_allows_passport_format():
    req = ClientCreateRequest(
        full_name="Foreign Client",
        id_number="1234567",
        id_number_type=IdNumberType.PASSPORT,
    )

    assert req.id_number == "1234567"


def test_client_create_request_allows_other_identifier_format():
    req = ClientCreateRequest(
        full_name="Misc Client",
        id_number="EXT-55-AB",
        id_number_type=IdNumberType.OTHER,
    )

    assert req.id_number == "EXT-55-AB"
