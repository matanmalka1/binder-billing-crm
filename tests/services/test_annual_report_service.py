from datetime import date
import itertools

import pytest

from app.models import Client, ClientType, ReportStage
from app.services.annual_report_service import AnnualReportService


_client_counter = itertools.count(1)


def _create_client(test_db) -> Client:
    # Ensure unique id_number to satisfy UNIQUE constraint in tests
    suffix = next(_client_counter)
    client = Client(
        full_name="Test Tax Client",
        id_number=f"1234567{suffix:02d}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_create_annual_report(test_db):
    """Test creating annual report."""
    client = _create_client(test_db)
    service = AnnualReportService(test_db)

    report = service.create_report(
        client_id=client.id,
        tax_year=2025,
        form_type="106",
        due_date=date(2026, 4, 30),
    )

    assert report.client_id == client.id
    assert report.tax_year == 2025
    assert report.stage == ReportStage.MATERIAL_COLLECTION
    assert report.status == "not_started"


def test_duplicate_report_raises_error(test_db):
    """Test that duplicate reports are rejected."""
    client = _create_client(test_db)
    service = AnnualReportService(test_db)

    service.create_report(client_id=client.id, tax_year=2025)

    with pytest.raises(ValueError, match="already exists"):
        service.create_report(client_id=client.id, tax_year=2025)


def test_stage_transition_sequential(test_db):
    """Test that stage transitions must be sequential."""
    client = _create_client(test_db)
    service = AnnualReportService(test_db)

    report = service.create_report(client_id=client.id, tax_year=2025)

    # Valid transition
    updated = service.transition_stage(report.id, ReportStage.IN_PROGRESS)
    assert updated.stage == ReportStage.IN_PROGRESS
    assert updated.status == "in_progress"

    # Valid: one step back
    updated = service.transition_stage(report.id, ReportStage.MATERIAL_COLLECTION)
    assert updated.stage == ReportStage.MATERIAL_COLLECTION
    assert updated.status == "not_started"

    # Invalid: skip stage
    with pytest.raises(ValueError, match="Cannot skip stages"):
        service.transition_stage(report.id, ReportStage.TRANSMITTED)

    # Invalid: skip backwards more than one step
    service.transition_stage(report.id, ReportStage.IN_PROGRESS)
    service.transition_stage(report.id, ReportStage.FINAL_REVIEW)
    with pytest.raises(ValueError, match="Cannot skip stages"):
        service.transition_stage(report.id, ReportStage.MATERIAL_COLLECTION)


def test_submit_requires_transmitted_stage(test_db):
    """Test that submission requires TRANSMITTED stage."""
    from datetime import datetime

    client = _create_client(test_db)
    service = AnnualReportService(test_db)

    report = service.create_report(client_id=client.id, tax_year=2025)

    with pytest.raises(ValueError, match="TRANSMITTED stage"):
        service.mark_submitted(report.id, datetime.now())

    # Transition to transmitted
    service.transition_stage(report.id, ReportStage.IN_PROGRESS)
    service.transition_stage(report.id, ReportStage.FINAL_REVIEW)
    service.transition_stage(report.id, ReportStage.CLIENT_SIGNATURE)
    service.transition_stage(report.id, ReportStage.TRANSMITTED)

    # Now submission should work
    submitted = service.mark_submitted(report.id, datetime.now())
    assert submitted.status == "completed"
    assert submitted.submitted_at is not None


def test_get_reports_by_stage(test_db):
    """Test filtering reports by stage."""
    client1 = _create_client(test_db)
    client2 = _create_client(test_db)
    service = AnnualReportService(test_db)

    report1 = service.create_report(client_id=client1.id, tax_year=2025)
    report2 = service.create_report(client_id=client2.id, tax_year=2025)

    service.transition_stage(report1.id, ReportStage.IN_PROGRESS)

    material = service.get_reports_by_stage(ReportStage.MATERIAL_COLLECTION)
    in_progress = service.get_reports_by_stage(ReportStage.IN_PROGRESS)

    assert len(material) == 1
    assert material[0].id == report2.id

    assert len(in_progress) == 1
    assert in_progress[0].id == report1.id
