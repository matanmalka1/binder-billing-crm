from datetime import date
from itertools import count

import pytest

from app.clients.models.client import Client, ClientStatus, ClientType
from app.clients.services.client_service import ClientService
from app.core.exceptions import ForbiddenError
from app.users.models.user import UserRole


_client_seq = count(1)


def _client(db, name: str = "Client") -> Client:
    idx = next(_client_seq)
    crm_client = Client(
        full_name=f"{name} {idx}",
        id_number=f"CSM{idx:06d}",
        client_type=ClientType.COMPANY,
        status=ClientStatus.ACTIVE,
        opened_at=date.today(),
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def test_get_update_delete_client_and_closed_at_behavior(test_db):
    crm_client = _client(test_db)
    service = ClientService(test_db)

    assert service.get_client(crm_client.id).id == crm_client.id

    updated = service.update_client(crm_client.id, UserRole.ADVISOR, status=ClientStatus.CLOSED)
    assert updated.status == ClientStatus.CLOSED
    assert updated.closed_at is not None

    assert service.delete_client(crm_client.id, actor_id=1) is True
    assert service.delete_client(999999, actor_id=1) is False


def test_update_client_forbidden_for_secretary_freeze_or_close(test_db):
    crm_client = _client(test_db)
    service = ClientService(test_db)

    with pytest.raises(ForbiddenError):
        service.update_client(crm_client.id, UserRole.SECRETARY, status=ClientStatus.FROZEN)


def test_bulk_update_status_mixed_results(test_db):
    existing = _client(test_db)
    service = ClientService(test_db)

    succeeded, failed = service.bulk_update_status(
        client_ids=[existing.id, 999999],
        action="freeze",
        actor_id=1,
        actor_role=UserRole.ADVISOR,
    )

    assert succeeded == [existing.id]
    assert [f.id for f in failed] == [999999]
