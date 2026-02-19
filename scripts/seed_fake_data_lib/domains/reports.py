from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from random import Random

from app.annual_reports.models.annual_report_detail import AnnualReportDetail
from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportStatus,
    ClientTypeForReport,
    DeadlineType,
)
from app.annual_reports.models.annual_report_model import AnnualReport
from app.clients.models.client import ClientType
from app.users.models.user import UserRole


def create_annual_reports(db, rng: Random, cfg, clients, users) -> list[AnnualReport]:
    reports: list[AnnualReport] = []
    current_year = datetime.now(UTC).year
    available_years = list(range(current_year - 3, current_year + 1))
    advisors = [u.id for u in users if u.role == UserRole.ADVISOR]
    for client in clients:
        years = rng.sample(
            available_years,
            k=min(cfg.annual_reports_per_client, len(available_years)),
        )
        for year in years:
            if client.client_type == ClientType.COMPANY:
                client_type_for_report = ClientTypeForReport.CORPORATION
                form_type = AnnualReportForm.FORM_6111
            elif client.client_type in (ClientType.OSEK_PATUR, ClientType.OSEK_MURSHE):
                client_type_for_report = ClientTypeForReport.SELF_EMPLOYED
                form_type = AnnualReportForm.FORM_1215
            else:
                client_type_for_report = ClientTypeForReport.INDIVIDUAL
                form_type = AnnualReportForm.FORM_1301

            status = rng.choice(list(AnnualReportStatus))
            filing_deadline = datetime(
                year,
                rng.randint(5, 12),
                rng.randint(1, 28),
                tzinfo=UTC,
            )
            submitted_at = (
                datetime.now(UTC) - timedelta(days=rng.randint(1, 120))
                if status
                in (
                    AnnualReportStatus.SUBMITTED,
                    AnnualReportStatus.ACCEPTED,
                    AnnualReportStatus.ASSESSMENT_ISSUED,
                    AnnualReportStatus.CLOSED,
                )
                else None
            )

            report = AnnualReport(
                client_id=client.id,
                tax_year=year,
                client_type=client_type_for_report,
                form_type=form_type,
                status=status,
                deadline_type=rng.choice(list(DeadlineType)),
                filing_deadline=filing_deadline,
                custom_deadline_note=None,
                submitted_at=submitted_at,
                ita_reference=None,
                assessment_amount=None,
                refund_due=None,
                tax_due=None,
                has_rental_income=rng.random() < 0.3,
                has_capital_gains=rng.random() < 0.25,
                has_foreign_income=rng.random() < 0.2,
                has_depreciation=rng.random() < 0.2,
                has_exempt_rental=rng.random() < 0.15,
                notes=rng.choice(["", "Needs review", "Client signature pending"]),
                created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 400)),
                updated_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 60)),
                created_by=rng.choice(advisors) if advisors else None,
                assigned_to=rng.choice(advisors) if advisors else None,
            )
            db.add(report)
            reports.append(report)
    db.flush()
    return reports


def create_annual_report_details(db, rng: Random, reports) -> None:
    for report in reports:
        if rng.random() > 0.6:
            continue

        tax_refund_amount = None
        tax_due_amount = None
        if rng.random() < 0.5:
            tax_refund_amount = Decimal(str(round(rng.uniform(500, 5000), 2)))
        else:
            tax_due_amount = Decimal(str(round(rng.uniform(500, 7500), 2)))

        detail = AnnualReportDetail(
            report_id=report.id,
            tax_refund_amount=tax_refund_amount,
            tax_due_amount=tax_due_amount,
            client_approved_at=(
                datetime.now(UTC) - timedelta(days=rng.randint(1, 120))
                if rng.random() < 0.5
                else None
            ),
            internal_notes=rng.choice(
                [
                    None,
                    "Pending client confirmation",
                    "Include revised payroll figures",
                    "Double-check VAT inputs",
                ]
            ),
        )
        db.add(detail)
    db.flush()
