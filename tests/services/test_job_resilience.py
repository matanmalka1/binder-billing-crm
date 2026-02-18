"""Tests for background job resilience (Sprint 5)."""
from datetime import date, timedelta
from unittest.mock import patch

from app.binders.models.binder import Binder, BinderStatus
from app.clients.models.client import Client, ClientType
from app.binders.services.daily_sla_job_service import DailySLAJobService


def test_job_completes_despite_individual_errors(test_db, test_user):
    """Test that job continues processing even if some binders fail."""
    # Create multiple clients and binders
    clients = []
    binders = []
    
    for i in range(3):
        client = Client(
            full_name=f"Test Client {i}",
            id_number=f"11111111{i}",
            client_type=ClientType.COMPANY,
            phone="0501234567",
            opened_at=date.today(),
        )
        test_db.add(client)
        test_db.commit()
        test_db.refresh(client)
        clients.append(client)
        
        binder = Binder(
            client_id=client.id,
            binder_number=f"BND-ERR-{i}",
            received_at=date.today() - timedelta(days=100),
            expected_return_at=date.today() - timedelta(days=10),
            status=BinderStatus.IN_OFFICE,
            received_by=test_user.id,
        )
        test_db.add(binder)
        test_db.commit()
        binders.append(binder)
    
    service = DailySLAJobService(test_db)
    
    # Mock notification service to fail for middle binder
    with patch.object(
        service.notification_service,
        'notify_overdue',
        side_effect=[None, Exception("Notification failed"), None]
    ):
        result = service.run(reference_date=date.today())
    
    # Job should complete with errors reported
    assert result["status"] == "completed_with_errors"
    assert result["errors"] > 0
    assert result["binders_scanned"] == 3


def test_job_reports_error_count(test_db, test_user):
    """Test that job reports number of errors encountered."""
    client = Client(
        full_name="Error Test Client",
        id_number="222222220",
        client_type=ClientType.COMPANY,
        phone="0501234567",
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    
    binder = Binder(
        client_id=client.id,
        binder_number="BND-ERR-COUNT",
        received_at=date.today() - timedelta(days=100),
        expected_return_at=date.today() - timedelta(days=10),
        status=BinderStatus.IN_OFFICE,
        received_by=test_user.id,
    )
    test_db.add(binder)
    test_db.commit()
    
    service = DailySLAJobService(test_db)
    
    # Mock to cause error
    with patch.object(
        service.notification_service,
        'notify_overdue',
        side_effect=Exception("Test error")
    ):
        result = service.run(reference_date=date.today())
    
    assert "errors" in result
    assert result["errors"] >= 1


def test_job_is_idempotent_after_errors(test_db, test_user):
    """Test that job can be safely retried after errors."""
    client = Client(
        full_name="Retry Test Client",
        id_number="333333330",
        client_type=ClientType.COMPANY,
        phone="0501234567",
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    
    binder = Binder(
        client_id=client.id,
        binder_number="BND-RETRY",
        received_at=date.today() - timedelta(days=100),
        expected_return_at=date.today() - timedelta(days=10),
        status=BinderStatus.IN_OFFICE,
        received_by=test_user.id,
    )
    test_db.add(binder)
    test_db.commit()
    
    service = DailySLAJobService(test_db)
    
    # First run with error
    with patch.object(
        service.notification_service,
        'notify_overdue',
        side_effect=Exception("First run error")
    ):
        result1 = service.run(reference_date=date.today())
    
    assert result1["status"] == "completed_with_errors"
    
    # Second run should succeed (notification already sent or will be sent)
    result2 = service.run(reference_date=date.today())
    
    # Should not create duplicate notifications
    assert result2["binders_scanned"] == 1
