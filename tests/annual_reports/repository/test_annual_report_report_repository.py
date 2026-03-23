from datetime import date, datetime, timedelta
from itertools import count

from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportStatus,
    ClientTypeForReport,
    DeadlineType,
)
from app.annual_reports.repositories.report_repository import AnnualReportReportRepository
from app.clients.models import Client
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


_client_seq = count(1)


def _user(test_db) -> User:
    user = User(
        full_name="Annual Report Repo User",
        email="annual.report.repo@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _client(test_db) -> Client:
    idx = next(_client_seq)
    client = Client(
        full_name=f"Annual Report Repo Client {idx}",
        id_number=f"ARR{idx:03d}",

    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def _report(
    repo: AnnualReportReportRepository,
    *,
    business_id: int,
    created_by: int,
    tax_year: int,
    status: AnnualReportStatus,
    deadline: datetime,
):
    return repo.create(
        business_id=business_id,
        created_by=created_by,
        tax_year=tax_year,
        client_type=ClientTypeForReport.CORPORATION,
        form_type=AnnualReportForm.FORM_6111,
        status=status,
        deadline_type=DeadlineType.STANDARD,
        filing_deadline=deadline,
        notes="repo test",
    )


def test_report_repository_status_listings_and_soft_delete(test_db):
    user = _user(test_db)
    client_a = _client(test_db)
    client_b = _client(test_db)
    repo = AnnualReportReportRepository(test_db)
    base = datetime(2026, 1, 1, 12, 0, 0)

    not_started = _report(
        repo,
        business_id=client_a.id,
        created_by=user.id,
        tax_year=2026,
        status=AnnualReportStatus.NOT_STARTED,
        deadline=base + timedelta(days=30),
    )
    submitted_a = _report(
        repo,
        business_id=client_b.id,
        created_by=user.id,
        tax_year=2025,
        status=AnnualReportStatus.SUBMITTED,
        deadline=base + timedelta(days=10),
    )
    submitted_b = _report(
        repo,
        business_id=client_a.id,
        created_by=user.id,
        tax_year=2024,
        status=AnnualReportStatus.SUBMITTED,
        deadline=base + timedelta(days=20),
    )

    submitted = repo.list_by_status(AnnualReportStatus.SUBMITTED, page=1, page_size=20)
    assert [r.id for r in submitted] == [submitted_a.id, submitted_b.id]
    assert repo.count_by_status(AnnualReportStatus.SUBMITTED) == 2
    assert repo.count_by_status(AnnualReportStatus.SUBMITTED, tax_year=2025) == 1

    all_reports = repo.list_all(page=1, page_size=20, sort_by="tax_year", order="desc")
    assert [r.id for r in all_reports] == [not_started.id, submitted_a.id, submitted_b.id]
    assert repo.count_all() == 3

    with_businesses = repo.list_all_with_businesses()
    assert len(with_businesses) == 3
    assert {r.business_id for r in with_businesses} == {client_a.id, client_b.id}

    assert repo.soft_delete(submitted_a.id, deleted_by=user.id) is True
    assert repo.count_all() == 2
    assert repo.count_by_status(AnnualReportStatus.SUBMITTED) == 1
    assert repo.get_by_id(submitted_a.id) is None
    assert repo.soft_delete(999999, deleted_by=user.id) is False
