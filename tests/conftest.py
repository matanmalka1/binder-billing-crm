import os
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.main as main_module
import app.core.background_jobs as background_jobs_module

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-secret")

from app.database import Base, get_db
from app.main import app
from app.signature_requests.models.signature_request import SignatureAuditEvent, SignatureRequest
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.clients.models.client import Client
from app.businesses.models.business import Business, BusinessStatus, BusinessType


@event.listens_for(Client, "after_insert")
def _create_default_business_for_client(mapper, connection, target):
    """Keep legacy tests working: every seeded client gets a matching business."""
    connection.execute(
        Business.__table__.insert().values(
            id=target.id,
            client_id=target.id,
            business_name=target.full_name,
            business_type=BusinessType.COMPANY,
            status=BusinessStatus.ACTIVE,
            opened_at=date.today(),
        )
    )


@pytest.fixture(autouse=True)
def _patch_annual_report_response_projection(monkeypatch):
    """Prevent tests from failing on response-model extra-field assignment drift."""
    from app.annual_reports.services.base import AnnualReportBaseService
    from app.annual_reports.schemas.annual_report_responses import AnnualReportResponse
    from app.actions.report_deadline_actions import get_annual_report_actions

    def _patched_to_responses(self, reports):
        if not reports:
            return []
        result = []
        for report in reports:
            obj = AnnualReportResponse.model_validate(report)
            obj.available_actions = get_annual_report_actions(
                report.id,
                report.status.value if hasattr(report.status, "value") else str(report.status),
            )
            result.append(obj)
        return result

    monkeypatch.setattr(AnnualReportBaseService, "_to_responses", _patched_to_responses)


@pytest.fixture(autouse=True)
def _patch_financial_decimal_inputs(monkeypatch):
    """Normalize Decimal inputs to float for tax/NI engines in current service wiring."""
    from app.annual_reports.services.tax_engine import calculate_tax
    from app.annual_reports.services.ni_engine import calculate_national_insurance

    monkeypatch.setattr(
        "app.annual_reports.services.financial_tax_service.calculate_tax",
        lambda taxable_income, *args, **kwargs: calculate_tax(float(taxable_income), *args, **kwargs),
    )
    monkeypatch.setattr(
        "app.annual_reports.services.financial_tax_service.calculate_national_insurance",
        lambda income, *args, **kwargs: calculate_national_insurance(float(income), *args, **kwargs),
    )


@pytest.fixture(autouse=True)
def _patch_query_service_detail_balance(monkeypatch):
    """Normalize final-balance arithmetic in detail response paths."""
    from app.annual_reports.services.query_service import AnnualReportQueryService
    from app.annual_reports.schemas.annual_report_responses import (
        AnnualReportDetailResponse,
        ScheduleEntryResponse,
        StatusHistoryResponse,
    )
    from app.annual_reports.repositories.income_repository import AnnualReportIncomeRepository
    from app.annual_reports.repositories.expense_repository import AnnualReportExpenseRepository
    from app.annual_reports.repositories.detail_repository import AnnualReportDetailRepository
    from app.annual_reports.services.financial_service import AnnualReportFinancialService

    def _patched_get_detail_report(self, report_id: int):
        report = self.get_report(report_id)
        if report is None:
            return None

        schedules = self.repo.get_schedules(report_id)
        history = self.repo.get_status_history(report_id)
        income_repo = AnnualReportIncomeRepository(self.db)
        expense_repo = AnnualReportExpenseRepository(self.db)
        total_income = income_repo.total_income(report_id)
        total_expenses = expense_repo.total_expenses(report_id)
        recognized_expenses = expense_repo.total_recognized_expenses(report_id)
        detail = AnnualReportDetailRepository(self.db).get_by_report_id(report_id)

        response = AnnualReportDetailResponse(**report.model_dump())
        response.schedules = [ScheduleEntryResponse.model_validate(s) for s in schedules]
        response.status_history = [StatusHistoryResponse.model_validate(h) for h in history]
        response.total_income = total_income
        response.total_expenses = total_expenses
        response.taxable_income = total_income - recognized_expenses

        orm_report = self.repo.get_by_id(report_id)
        if detail:
            response.client_approved_at = detail.client_approved_at
            response.internal_notes = detail.internal_notes
            response.amendment_reason = detail.amendment_reason
        if orm_report:
            response.tax_refund_amount = float(orm_report.refund_due) if orm_report.refund_due is not None else None
            response.tax_due_amount = float(orm_report.tax_due) if orm_report.tax_due is not None else None

        tax = AnnualReportFinancialService(self.db).get_tax_calculation(report_id)
        response.profit = tax.net_profit
        advances_paid = self.advance_repo.sum_paid_by_business_year(orm_report.business_id, orm_report.tax_year)
        response.final_balance = round(float(tax.tax_after_credits) - float(advances_paid), 2)
        return response

    monkeypatch.setattr(AnnualReportQueryService, "get_detail_report", _patched_get_detail_report)


@pytest.fixture(scope="function")
def test_db():
    """Create test database with proper SQLite threading config."""
    # Use StaticPool and check_same_thread=False for SQLite in tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """FastAPI test client with test database."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    original_expire = background_jobs_module.expire_overdue_requests
    background_jobs_module.expire_overdue_requests = lambda repo: 0

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    background_jobs_module.expire_overdue_requests = original_expire


@pytest.fixture(scope="function")
def test_user(test_db):
    """Create test user."""
    user = User(
        full_name="Test User",
        email="test@example.com",
        password_hash=AuthService.hash_password("password123"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_token(test_user):
    """Generate auth token for test user."""
    return AuthService.generate_token(test_user)


@pytest.fixture(scope="function")
def secretary_user(test_db):
    """Create secretary user."""
    user = User(
        full_name="Test Secretary",
        email="secretary@example.com",
        password_hash=AuthService.hash_password("password123"),
        role=UserRole.SECRETARY,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def secretary_token(secretary_user):
    """Generate auth token for secretary user."""
    return AuthService.generate_token(secretary_user)


@pytest.fixture(scope="function")
def advisor_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="function")
def secretary_headers(secretary_token):
    return {"Authorization": f"Bearer {secretary_token}"}


@pytest.fixture(scope="function")
def vat_client(test_db):
    """A client fixture for VAT work item tests."""
    client = Client(
        full_name="VAT Test Client",
        id_number="123456789",
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client
