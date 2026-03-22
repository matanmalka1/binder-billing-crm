import pytest
from pydantic import ValidationError

from app.clients.models.client import Client
from app.clients.schemas.client import ClientCreateRequest


def test_client_model_repr_contains_identity_fields():
    client = Client(id=5, full_name="Repr Name", id_number="123456789")
    rendered = repr(client)
    assert "id=5" in rendered
    assert "Repr Name" in rendered
    assert "123456789" in rendered


def test_client_create_request_rejects_non_digits():
    with pytest.raises(ValidationError):
        ClientCreateRequest(full_name="Bad", id_number="12A456789")


def test_client_create_request_rejects_invalid_length():
    with pytest.raises(ValidationError):
        ClientCreateRequest(full_name="Bad", id_number="12345")
