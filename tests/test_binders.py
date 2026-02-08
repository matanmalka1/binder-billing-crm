from datetime import date
from app.models import Client, ClientType


def test_binder_status_change_creates_log(client, auth_token, test_db, test_user):
    """Test that binder status changes create audit logs."""
    # Create client
    test_client = Client(
        full_name="Test Client",
        id_number="111222333",
        client_type=ClientType.OSEK_MURSHE,
        opened_at=date.today()
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)
    
    # Receive binder
    response = client.post(
        "/api/v1/binders/receive",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "client_id": test_client.id,
            "binder_number": "BND-2026-001",
            "received_at": "2026-02-08",
            "received_by": test_user.id,
            "notes": "Test binder"
        }
    )
    
    assert response.status_code == 201
    binder_data = response.json()
    binder_id = binder_data["id"]
    
    # Verify status log was created
    from app.repositories import BinderStatusLogRepository
    log_repo = BinderStatusLogRepository(test_db)
    logs = log_repo.list_by_binder(binder_id)
    
    assert len(logs) == 1
    assert logs[0].old_status == "null"
    assert logs[0].new_status == "in_office"
    assert logs[0].changed_by == test_user.id


def test_binder_return_creates_log(client, auth_token, test_db, test_user):
    """Test that returning binder creates status log."""
    # Create client
    test_client = Client(
        full_name="Test Client",
        id_number="444555666",
        client_type=ClientType.COMPANY,
        opened_at=date.today()
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)
    
    # Receive binder
    receive_response = client.post(
        "/api/v1/binders/receive",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "client_id": test_client.id,
            "binder_number": "BND-2026-002",
            "received_at": "2026-02-08",
            "received_by": test_user.id
        }
    )
    binder_id = receive_response.json()["id"]
    
    # Mark binder as ready (via service since endpoint not exposed)
    from app.services import BinderService
    binder_service = BinderService(test_db)
    binder_service.mark_ready_for_pickup(binder_id, test_user.id)
    
    # Return binder
    return_response = client.post(
        f"/api/v1/binders/{binder_id}/return",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "pickup_person_name": "Avi Cohen",
            "returned_by": test_user.id
        }
    )
    
    assert return_response.status_code == 200
    
    # Verify logs
    from app.repositories import BinderStatusLogRepository
    log_repo = BinderStatusLogRepository(test_db)
    logs = log_repo.list_by_binder(binder_id)
    
    # Should have: intake, mark ready, return
    assert len(logs) >= 3
    assert logs[-1].new_status == "returned"