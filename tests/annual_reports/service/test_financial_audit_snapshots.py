import json
from decimal import Decimal
from itertools import count

from app.annual_reports.services.annual_report_service import AnnualReportService
from app.annual_reports.services.financial_service import AnnualReportFinancialService
from app.audit.constants import ACTION_EXPENSE_DELETED, ACTION_INCOME_DELETED, ENTITY_ANNUAL_REPORT
from app.audit.models.entity_audit_log import EntityAuditLog
from tests.helpers.identity import seed_client_identity


_seq = count(1)


def _create_report(db, user):
    idx = next(_seq)
    client = seed_client_identity(db, full_name=f"Audit Financial {idx}", id_number=f"AF{idx:07d}")
    return AnnualReportService(db).create_report(
        client_record_id=client.id,
        tax_year=2026,
        client_type="corporation",
        created_by=user.id,
        created_by_name=user.full_name,
    )


def test_income_delete_stores_old_value_snapshot(test_db, test_user):
    report = _create_report(test_db, test_user)
    service = AnnualReportFinancialService(test_db)
    line = service.add_income(
        report.id,
        "salary",
        Decimal("123.45"),
        description="Payroll",
        actor_id=test_user.id,
    )

    service.delete_income(report.id, line.id, actor_id=test_user.id)

    entry = (
        test_db.query(EntityAuditLog)
        .filter(EntityAuditLog.entity_type == ENTITY_ANNUAL_REPORT)
        .filter(EntityAuditLog.entity_id == report.id)
        .filter(EntityAuditLog.action == ACTION_INCOME_DELETED)
        .one()
    )
    assert json.loads(entry.old_value) == {
        "line_id": line.id,
        "source_type": "salary",
        "amount": "123.45",
        "description": "Payroll",
    }


def test_expense_delete_stores_old_value_snapshot(test_db, test_user):
    report = _create_report(test_db, test_user)
    service = AnnualReportFinancialService(test_db)
    line = service.add_expense(
        report.id,
        "office_rent",
        Decimal("456.78"),
        description="Rent",
        actor_id=test_user.id,
    )

    service.delete_expense(report.id, line.id, actor_id=test_user.id)

    entry = (
        test_db.query(EntityAuditLog)
        .filter(EntityAuditLog.entity_type == ENTITY_ANNUAL_REPORT)
        .filter(EntityAuditLog.entity_id == report.id)
        .filter(EntityAuditLog.action == ACTION_EXPENSE_DELETED)
        .one()
    )
    assert json.loads(entry.old_value) == {
        "line_id": line.id,
        "category": "office_rent",
        "amount": "456.78",
        "description": "Rent",
    }
