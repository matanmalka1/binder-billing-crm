from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from random import Random

from app.annual_reports.services.constants import VALID_TRANSITIONS
from app.annual_reports.services.deadlines import extended_deadline, standard_deadline
from app.annual_reports.models.annual_report_annex_data import AnnualReportAnnexData
from app.annual_reports.models.annual_report_expense_line import (
    AnnualReportExpenseLine,
    ExpenseCategoryType,
    default_recognition_rate,
)
from app.annual_reports.models.annual_report_schedule_entry import AnnualReportScheduleEntry
from app.annual_reports.models.annual_report_status_history import AnnualReportStatusHistory
from app.annual_reports.models.annual_report_detail import AnnualReportDetail
from app.annual_reports.models.annual_report_income_line import AnnualReportIncomeLine, IncomeSourceType
from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportSchedule,
    AnnualReportStatus,
    ClientTypeForReport,
    DeadlineType,
)
from app.annual_reports.models.annual_report_model import AnnualReport
from app.businesses.models.business import BusinessType
from app.users.models.user import UserRole


SEEDABLE_STATUSES = [
    AnnualReportStatus.NOT_STARTED,
    AnnualReportStatus.COLLECTING_DOCS,
    AnnualReportStatus.DOCS_COMPLETE,
    AnnualReportStatus.IN_PREPARATION,
    AnnualReportStatus.PENDING_CLIENT,
    AnnualReportStatus.AMENDED,
    AnnualReportStatus.SUBMITTED,
    AnnualReportStatus.ACCEPTED,
    AnnualReportStatus.ASSESSMENT_ISSUED,
    AnnualReportStatus.OBJECTION_FILED,
    AnnualReportStatus.CLOSED,
]


def _status_path_to(target: AnnualReportStatus) -> list[AnnualReportStatus]:
    if target == AnnualReportStatus.AMENDED:
        # AMENDED can exist as operational override; no canonical forward path exists
        # in VALID_TRANSITIONS from NOT_STARTED to AMENDED.
        return [AnnualReportStatus.AMENDED]

    if target == AnnualReportStatus.NOT_STARTED:
        return [AnnualReportStatus.NOT_STARTED]

    frontier: list[list[AnnualReportStatus]] = [[AnnualReportStatus.NOT_STARTED]]
    while frontier:
        path = frontier.pop(0)
        current = path[-1]
        for nxt in VALID_TRANSITIONS.get(current, set()):
            if nxt in path:
                continue
            new_path = [*path, nxt]
            if nxt == target:
                return new_path
            frontier.append(new_path)

    raise RuntimeError(f"Cannot build legal annual-report status path to {target.value}")


def create_annual_reports(db, rng: Random, cfg, businesses, users) -> list[AnnualReport]:
    reports: list[AnnualReport] = []
    current_year = datetime.now(UTC).year
    available_years = list(range(current_year - 3, current_year + 1))
    advisors = [u.id for u in users if u.role == UserRole.ADVISOR]
    fallback_user_id = users[0].id if users else None
    status_cycle = list(SEEDABLE_STATUSES)
    status_cycle_idx = 0
    for business in businesses:
        years = rng.sample(
            available_years,
            k=min(cfg.annual_reports_per_client, len(available_years)),
        )
        for year in years:
            if business.business_type == BusinessType.COMPANY:
                client_type_for_report = ClientTypeForReport.CORPORATION
                form_type = AnnualReportForm.FORM_6111
            elif business.business_type in (BusinessType.OSEK_PATUR, BusinessType.OSEK_MURSHE):
                client_type_for_report = ClientTypeForReport.SELF_EMPLOYED
                form_type = AnnualReportForm.FORM_1215
            else:
                client_type_for_report = ClientTypeForReport.INDIVIDUAL
                form_type = AnnualReportForm.FORM_1301

            if status_cycle_idx < len(status_cycle):
                status = status_cycle[status_cycle_idx]
                status_cycle_idx += 1
            else:
                status = rng.choice(SEEDABLE_STATUSES)
            deadline_type = rng.choice(list(DeadlineType))
            custom_deadline_note = None
            if deadline_type == DeadlineType.STANDARD:
                filing_deadline = standard_deadline(year)
            elif deadline_type == DeadlineType.EXTENDED:
                filing_deadline = extended_deadline(year)
            else:
                filing_deadline = None
                custom_deadline_note = "מועד מותאם אישית בסביבת דמו"
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
                business_id=business.id,
                tax_year=year,
                client_type=client_type_for_report,
                form_type=form_type,
                status=status,
                deadline_type=deadline_type,
                filing_deadline=filing_deadline,
                custom_deadline_note=custom_deadline_note,
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
                notes=rng.choice(["", "דורש בדיקה", "ממתין לחתימת לקוח"]),
                created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 400)),
                updated_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 60)),
                created_by=rng.choice(advisors) if advisors else fallback_user_id,
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
                    "ממתין לאישור לקוח",
                    "לעדכן נתוני שכר מתוקנים",
                    'לבדוק שוב את קלטי המע"מ',
                ]
            ),
        )
        db.add(detail)
    db.flush()


def create_annual_report_schedule_entries(db, rng: Random, reports) -> None:
    for report in reports:
        for schedule in list(AnnualReportSchedule):
            is_required = rng.random() < 0.4
            is_complete = is_required and rng.random() < 0.5
            entry = AnnualReportScheduleEntry(
                annual_report_id=report.id,
                schedule=schedule,
                is_required=is_required,
                is_complete=is_complete,
                notes="נוצר אוטומטית" if is_required else None,
                created_at=report.created_at,
                completed_at=(report.created_at + timedelta(days=rng.randint(5, 60))) if is_complete else None,
            )
            db.add(entry)
    db.flush()


def create_annual_report_income_lines(db, rng: Random, reports) -> None:
    for report in reports:
        source_candidates = [IncomeSourceType.SALARY]
        if report.client_type in (ClientTypeForReport.SELF_EMPLOYED, ClientTypeForReport.CORPORATION):
            source_candidates.extend(
                [IncomeSourceType.BUSINESS, IncomeSourceType.INTEREST, IncomeSourceType.DIVIDENDS]
            )
        if report.has_rental_income:
            source_candidates.append(IncomeSourceType.RENTAL)
        if report.has_capital_gains:
            source_candidates.append(IncomeSourceType.CAPITAL_GAINS)
        if report.has_foreign_income:
            source_candidates.append(IncomeSourceType.FOREIGN)

        unique_sources = list(dict.fromkeys(source_candidates))
        line_count = min(len(unique_sources), rng.randint(1, 3))
        chosen_sources = rng.sample(unique_sources, k=line_count)

        for source_type in chosen_sources:
            line = AnnualReportIncomeLine(
                annual_report_id=report.id,
                source_type=source_type,
                amount=Decimal(str(round(rng.uniform(2_500, 120_000), 2))),
                description=rng.choice(
                    [None, "שורה שנוצרה אוטומטית", "נדרש אימות מסמכים תומכים"]
                ),
                created_at=report.created_at,
            )
            db.add(line)
    db.flush()


def create_annual_report_expense_lines(db, rng: Random, reports) -> None:
    base_categories = [
        ExpenseCategoryType.PROFESSIONAL_SERVICES,
        ExpenseCategoryType.BANK_FEES,
        ExpenseCategoryType.INSURANCE,
    ]
    for report in reports:
        category_candidates = list(base_categories)
        if report.client_type in (ClientTypeForReport.SELF_EMPLOYED, ClientTypeForReport.CORPORATION):
            category_candidates.extend(
                [
                    ExpenseCategoryType.OFFICE_RENT,
                    ExpenseCategoryType.COMMUNICATION,
                    ExpenseCategoryType.VEHICLE,
                    ExpenseCategoryType.MARKETING,
                ]
            )
        if report.has_depreciation:
            category_candidates.append(ExpenseCategoryType.DEPRECIATION)
        unique_categories = list(dict.fromkeys(category_candidates))
        line_count = min(len(unique_categories), rng.randint(1, 4))
        chosen_categories = rng.sample(unique_categories, k=line_count)

        for category in chosen_categories:
            expense_line = AnnualReportExpenseLine(
                annual_report_id=report.id,
                category=category,
                amount=Decimal(str(round(rng.uniform(200, 40_000), 2))),
                recognition_rate=default_recognition_rate(category),
                supporting_document_ref=None,
                supporting_document_id=None,
                description=rng.choice(
                    [None, "הוצאה מוכרת", "לבדוק התאמה לחשבונית"]
                ),
                created_at=report.created_at,
            )
            db.add(expense_line)
    db.flush()


def create_annual_report_annex_data(db, rng: Random, reports) -> None:
    for report in reports:
        applicable_schedules: list[AnnualReportSchedule] = []
        if report.has_rental_income:
            applicable_schedules.append(AnnualReportSchedule.SCHEDULE_B)
        if report.has_capital_gains:
            applicable_schedules.append(AnnualReportSchedule.SCHEDULE_BET)
        if report.has_foreign_income:
            applicable_schedules.append(AnnualReportSchedule.SCHEDULE_GIMMEL)
        if report.has_depreciation:
            applicable_schedules.append(AnnualReportSchedule.SCHEDULE_DALET)
        if report.has_exempt_rental:
            applicable_schedules.append(AnnualReportSchedule.SCHEDULE_HEH)

        if not applicable_schedules:
            applicable_schedules = [rng.choice(list(AnnualReportSchedule))]

        for line_number, schedule in enumerate(applicable_schedules, start=1):
            annex_line = AnnualReportAnnexData(
                annual_report_id=report.id,
                schedule=schedule,
                line_number=line_number,
                data={
                    "amount": float(round(rng.uniform(500, 90_000), 2)),
                    "description": rng.choice(
                        [
                            "נתון שנוצר אוטומטית לצורך סביבת דמו",
                            "ערך להשלמה בבדיקת רו\"ח",
                        ]
                    ),
                },
                notes=rng.choice([None, "נדרש מסמך תומך"]),
                created_at=report.created_at,
            )
            db.add(annex_line)
    db.flush()


def create_annual_report_status_history(db, rng: Random, reports, users) -> None:
    user_lookup = {u.id: u for u in users}
    fallback_user = users[0] if users else None
    for report in reports:
        history_statuses = _status_path_to(report.status)
        previous = None
        occurred_at = report.created_at
        for status in history_statuses:
            actor_id = report.created_by or report.assigned_to or (fallback_user.id if fallback_user else None)
            actor_name = (
                user_lookup.get(actor_id).full_name
                if actor_id in user_lookup
                else "זורע נתונים"
            )
            occurred_at += timedelta(hours=rng.randint(1, 72))
            entry = AnnualReportStatusHistory(
                annual_report_id=report.id,
                from_status=previous,
                to_status=status,
                changed_by=actor_id,
                changed_by_name=actor_name,
                note="היסטוריית סטטוסים שנוצרה אוטומטית",
                occurred_at=occurred_at,
            )
            db.add(entry)
            previous = status
    db.flush()
