from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from random import Random
from typing import Any, Iterable

from sqlalchemy import delete

from app.annual_reports.models.annual_report_annex_data import AnnualReportAnnexData
from app.annual_reports.models.annual_report_credit_point_reason import (
    AnnualReportCreditPoint,
    CreditPointReason,
)
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
    FilingDeadlineType as DeadlineType,
    ExtensionReason,
    SubmissionMethod,
)
from app.annual_reports.models.annual_report_model import AnnualReport
from app.common.enums import EntityType
from app.users.models.user import UserRole

from ._business_groups import group_businesses_by_client


def standard_deadline(tax_year: int) -> datetime:
    return datetime(tax_year + 1, 4, 30, 23, 59, 59)


def extended_deadline(tax_year: int) -> datetime:
    return datetime(tax_year + 2, 1, 31, 23, 59, 59)


VALID_TRANSITIONS: dict[AnnualReportStatus, set[AnnualReportStatus]] = {
    AnnualReportStatus.NOT_STARTED: {AnnualReportStatus.COLLECTING_DOCS},
    AnnualReportStatus.COLLECTING_DOCS: {
        AnnualReportStatus.DOCS_COMPLETE,
        AnnualReportStatus.NOT_STARTED,
    },
    AnnualReportStatus.DOCS_COMPLETE: {
        AnnualReportStatus.IN_PREPARATION,
        AnnualReportStatus.COLLECTING_DOCS,
    },
    AnnualReportStatus.IN_PREPARATION: {
        AnnualReportStatus.PENDING_CLIENT,
        AnnualReportStatus.DOCS_COMPLETE,
    },
    AnnualReportStatus.PENDING_CLIENT: {
        AnnualReportStatus.IN_PREPARATION,
        AnnualReportStatus.SUBMITTED,
    },
    AnnualReportStatus.SUBMITTED: {
        AnnualReportStatus.ACCEPTED,
        AnnualReportStatus.ASSESSMENT_ISSUED,
    },
    AnnualReportStatus.AMENDED: {
        AnnualReportStatus.IN_PREPARATION,
        AnnualReportStatus.SUBMITTED,
    },
    AnnualReportStatus.ACCEPTED: {AnnualReportStatus.CLOSED},
    AnnualReportStatus.ASSESSMENT_ISSUED: {
        AnnualReportStatus.OBJECTION_FILED,
        AnnualReportStatus.CLOSED,
        AnnualReportStatus.PENDING_CLIENT,
        AnnualReportStatus.IN_PREPARATION,
        AnnualReportStatus.DOCS_COMPLETE,
    },
    AnnualReportStatus.OBJECTION_FILED: {
        AnnualReportStatus.CLOSED,
        AnnualReportStatus.DOCS_COMPLETE,
    },
    AnnualReportStatus.CLOSED: set(),
}


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

COUNTRIES = ["ארצות הברית", "בריטניה", "גרמניה", "צרפת", "קפריסין", "פורטוגל"]
PROPERTY_CITIES = ["תל אביב", "ירושלים", "חיפה", "נתניה", "הרצליה"]
SECURITIES = ["מניית בנק לאומי", "מדד S&P 500", "קרן סל ת\"א 125", "אג\"ח ממשלתי"]


def _random_decimal(rng: Random, minimum: float, maximum: float) -> Decimal:
    return Decimal(str(round(rng.uniform(minimum, maximum), 2)))


def _as_plain_decimal(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def _property_address(rng: Random) -> str:
    return f"{rng.choice(['הרצל', 'ביאליק', 'ויצמן', 'דיזנגוף'])} {rng.randint(1, 120)}, {rng.choice(PROPERTY_CITIES)}"


def _build_annex_payload(
    rng: Random,
    report: AnnualReport,
    schedule: AnnualReportSchedule,
) -> dict[str, Any]:
    if schedule == AnnualReportSchedule.SCHEDULE_A:
        gross_income = _random_decimal(rng, 80_000, 520_000)
        cost_of_goods = _random_decimal(rng, 10_000, float(gross_income * Decimal("0.65")))
        gross_profit = gross_income - cost_of_goods
        operating_expenses = _random_decimal(rng, 15_000, float(gross_profit * Decimal("0.85")))
        return {
            "gross_income": _as_plain_decimal(gross_income),
            "cost_of_goods": _as_plain_decimal(cost_of_goods),
            "gross_profit": _as_plain_decimal(gross_profit),
            "operating_expenses": _as_plain_decimal(operating_expenses),
            "net_income": _as_plain_decimal(gross_profit - operating_expenses),
        }
    if schedule == AnnualReportSchedule.SCHEDULE_B:
        rental_income = _random_decimal(rng, 24_000, 96_000)
        maintenance = _random_decimal(rng, 1_500, 12_000)
        depreciation = _random_decimal(rng, 0, 8_000)
        return {
            "property_address": _property_address(rng),
            "rental_income": _as_plain_decimal(rental_income),
            "depreciation_claimed": _as_plain_decimal(depreciation),
            "maintenance_expenses": _as_plain_decimal(maintenance),
            "net_rental_income": _as_plain_decimal(rental_income - maintenance - depreciation),
        }
    if schedule == AnnualReportSchedule.FORM_1399:
        purchase_price = _random_decimal(rng, 25_000, 220_000)
        sale_price = purchase_price + _random_decimal(rng, 5_000, 90_000)
        return {
            "asset_description": rng.choice(["מכירת דירה להשקעה", "מכירת ציוד עסקי", "מכירת זכות במקרקעין"]),
            "purchase_date": f"{report.tax_year - rng.randint(1, 6)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            "sale_date": f"{report.tax_year}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            "purchase_price": _as_plain_decimal(purchase_price),
            "sale_price": _as_plain_decimal(sale_price),
            "capital_gain": _as_plain_decimal(sale_price - purchase_price),
            "tax_rate": _as_plain_decimal(_random_decimal(rng, 20, 30)),
        }
    if schedule == AnnualReportSchedule.SCHEDULE_DALET:
        gross_income = _random_decimal(rng, 8_000, 85_000)
        foreign_tax = _random_decimal(rng, 0, float(gross_income * Decimal("0.22")))
        return {
            "country": rng.choice(COUNTRIES),
            "income_type": rng.choice(["משכורת", "דיבידנד", "ריבית", "שכירות"]),
            "gross_income": _as_plain_decimal(gross_income),
            "foreign_tax_paid": _as_plain_decimal(foreign_tax),
            "net_income": _as_plain_decimal(gross_income - foreign_tax),
        }
    if schedule == AnnualReportSchedule.FORM_1342:
        asset_cost = _random_decimal(rng, 6_000, 80_000)
        annual_dep = _random_decimal(rng, 1_000, float(asset_cost * Decimal("0.25")))
        accumulated = annual_dep + _random_decimal(rng, 500, float(asset_cost * Decimal("0.35")))
        return {
            "asset_description": rng.choice(["מחשב נייד", "ריהוט משרדי", "מערכת מיזוג", "מכונת ייצור"]),
            "asset_cost": _as_plain_decimal(asset_cost),
            "depreciation_rate": _as_plain_decimal(_random_decimal(rng, 7, 20)),
            "accumulated_depreciation": _as_plain_decimal(accumulated),
            "annual_depreciation": _as_plain_decimal(annual_dep),
            "book_value": _as_plain_decimal(max(asset_cost - accumulated, Decimal("0.00"))),
        }
    if schedule == AnnualReportSchedule.SCHEDULE_GIMMEL:
        purchase_price = _random_decimal(rng, 8_000, 70_000)
        sale_price = purchase_price + rng.choice([
            _random_decimal(rng, 1_500, 20_000),
            -_random_decimal(rng, 500, 12_000),
        ])
        return {
            "security_name": rng.choice(SECURITIES),
            "quantity": _as_plain_decimal(_random_decimal(rng, 10, 600)),
            "purchase_price": _as_plain_decimal(purchase_price),
            "sale_price": _as_plain_decimal(sale_price),
            "gain_loss": _as_plain_decimal(sale_price - purchase_price),
        }
    if schedule == AnnualReportSchedule.FORM_150:
        gross_amount = _random_decimal(rng, 6_000, 60_000)
        withholding = _random_decimal(rng, 0, float(gross_amount * Decimal("0.25")))
        return {
            "country": rng.choice(COUNTRIES),
            "income_description": rng.choice(["הכנסות ייעוץ", "דיבידנד מחברה זרה", "תמלוגים", "ריבית מפיקדון"]),
            "gross_amount": _as_plain_decimal(gross_amount),
            "withholding_tax": _as_plain_decimal(withholding),
            "treaty_rate": _as_plain_decimal(_random_decimal(rng, 5, 25)),
        }
    if schedule == AnnualReportSchedule.FORM_1343:
        return {
            "bank_name": rng.choice(["בנק הפועלים", "בנק לאומי", "מזרחי טפחות", "IBI Trade"]),
            "account_number": f"{rng.randint(10000, 99999)}-{rng.randint(1000000, 9999999)}",
            "interest_income": _as_plain_decimal(_random_decimal(rng, 300, 8_000)),
            "dividend_income": _as_plain_decimal(_random_decimal(rng, 0, 12_000)),
            "withholding_tax": _as_plain_decimal(_random_decimal(rng, 0, 2_500)),
        }
    return {}


def _annex_schedules_for_report(report: AnnualReport, rng: Random) -> list[AnnualReportSchedule]:
    schedules: list[AnnualReportSchedule] = []
    if report.client_type in (ClientTypeForReport.SELF_EMPLOYED, ClientTypeForReport.CORPORATION):
        schedules.append(AnnualReportSchedule.SCHEDULE_A)
    if report.has_rental_income:
        schedules.append(AnnualReportSchedule.SCHEDULE_B)
    if report.has_capital_gains:
        schedules.extend([AnnualReportSchedule.FORM_1399, AnnualReportSchedule.SCHEDULE_GIMMEL])
    if report.has_foreign_income:
        schedules.extend([AnnualReportSchedule.SCHEDULE_DALET, AnnualReportSchedule.FORM_150])
    if report.has_depreciation:
        schedules.append(AnnualReportSchedule.FORM_1342)
    if rng.random() < 0.35:
        schedules.append(AnnualReportSchedule.FORM_1343)
    if not schedules:
        schedules = [rng.choice(list(AnnualReportSchedule))]
    return list(dict.fromkeys(schedules))


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
    available_years = list(range(current_year - 4, current_year))
    advisors = [u.id for u in users if u.role == UserRole.ADVISOR]
    fallback_user_id = users[0].id if users else None
    status_cycle = list(SEEDABLE_STATUSES)
    status_cycle_idx = 0
    for client_businesses in group_businesses_by_client(businesses).values():
        years = rng.sample(
            available_years,
            k=min(cfg.annual_reports_per_client, len(available_years)),
        )
        for year in years:
            business = rng.choice(client_businesses)
            if business.client.entity_type == EntityType.COMPANY_LTD:
                client_type_for_report = ClientTypeForReport.CORPORATION
                form_type = AnnualReportForm.FORM_1214
            elif business.client.entity_type in (EntityType.OSEK_PATUR, EntityType.OSEK_MURSHE):
                client_type_for_report = ClientTypeForReport.SELF_EMPLOYED
                form_type = AnnualReportForm.FORM_1301
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
            submission_method = (
                rng.choice(list(SubmissionMethod))
                if status
                in (
                    AnnualReportStatus.SUBMITTED,
                    AnnualReportStatus.ACCEPTED,
                    AnnualReportStatus.ASSESSMENT_ISSUED,
                    AnnualReportStatus.OBJECTION_FILED,
                    AnnualReportStatus.CLOSED,
                )
                else None
            )
            extension_reason = (
                rng.choice(list(ExtensionReason))
                if deadline_type == DeadlineType.EXTENDED
                else None
            )
            created_at = datetime.now(UTC) - timedelta(days=rng.randint(0, 400))
            updated_at = created_at + timedelta(days=rng.randint(0, 60))
            now = datetime.now(UTC)
            if updated_at > now:
                updated_at = now
            submitted_at = None
            if status in (
                AnnualReportStatus.SUBMITTED,
                AnnualReportStatus.ACCEPTED,
                AnnualReportStatus.ASSESSMENT_ISSUED,
                AnnualReportStatus.OBJECTION_FILED,
                AnnualReportStatus.CLOSED,
            ):
                submitted_at = created_at + timedelta(days=rng.randint(1, 180))
                if submitted_at > now:
                    submitted_at = now
                if updated_at < submitted_at:
                    updated_at = submitted_at

            report = AnnualReport(
                client_id=business.client_id,
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
                submission_method=submission_method,
                extension_reason=extension_reason,
                notes=rng.choice(["", "דורש בדיקה", "ממתין לחתימת לקוח"]),
                created_at=created_at,
                updated_at=updated_at,
                created_by=rng.choice(advisors) if advisors else fallback_user_id,
                assigned_to=rng.choice(advisors) if advisors else None,
            )
            db.add(report)
            reports.append(report)
    db.flush()
    return reports


def create_annual_report_details(db, rng: Random, reports) -> None:
    for report in reports:
        client_approved_at = None
        if report.status in (
            AnnualReportStatus.SUBMITTED,
            AnnualReportStatus.ASSESSMENT_ISSUED,
            AnnualReportStatus.ACCEPTED,
            AnnualReportStatus.OBJECTION_FILED,
            AnnualReportStatus.CLOSED,
        ):
            approval_upper_bound = report.submitted_at or report.updated_at or datetime.now(UTC)
            candidate = report.created_at + timedelta(days=rng.randint(7, 45))
            client_approved_at = min(candidate, approval_upper_bound)

        detail = AnnualReportDetail(
            report_id=report.id,
            pension_contribution=_random_decimal(rng, 0, 15_000),
            donation_amount=_random_decimal(rng, 0, 6_000),
            other_credits=_random_decimal(rng, 0, 3_500),
            client_approved_at=client_approved_at,
            internal_notes=rng.choice(
                [
                    None,
                    "ממתין לאישור לקוח",
                    "לעדכן נתוני שכר מתוקנים",
                    'לבדוק שוב את קלטי המע"מ',
                    "לצרף אישורי תרומות ומסמכי בנק",
                ]
            ),
            amendment_reason=(
                rng.choice(["תיקון לפי מסמכים מעודכנים", "תיקון בעקבות שומת מס"])
                if report.status == AnnualReportStatus.AMENDED
                else None
            ),
            created_at=report.created_at,
        )
        db.add(detail)
    db.flush()


def create_annual_report_schedule_entries(db, rng: Random, reports, users=None) -> None:
    advisors = [u.id for u in users] if users else []
    fallback_user_id = users[0].id if users else None

    for report in reports:
        for schedule in list(AnnualReportSchedule):
            is_required = rng.random() < 0.4
            is_complete = is_required and rng.random() < 0.5
            completed_at = None
            completed_by = None
            if is_complete:
                completed_at = report.created_at + timedelta(days=rng.randint(5, 60))
                completed_by = rng.choice(advisors) if advisors else fallback_user_id
            entry = AnnualReportScheduleEntry(
                annual_report_id=report.id,
                schedule=schedule,
                is_required=is_required,
                is_complete=is_complete,
                notes="נוצר אוטומטית" if is_required else None,
                created_at=report.created_at,
                completed_at=completed_at,
                completed_by=completed_by,
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


def create_annual_report_expense_lines(
    db,
    rng: Random,
    reports,
    seeded_documents: Iterable | None = None,
    replace_existing: bool = False,
) -> None:
    if replace_existing:
        db.execute(delete(AnnualReportExpenseLine))
        db.flush()

    base_categories = [
        ExpenseCategoryType.PROFESSIONAL_SERVICES,
        ExpenseCategoryType.BANK_FEES,
        ExpenseCategoryType.INSURANCE,
    ]
    documents_by_client_id: dict[int, list] = {}
    if seeded_documents:
        for document in seeded_documents:
            documents_by_client_id.setdefault(document.client_id, []).append(document)

    for report in reports:
        category_candidates = list(base_categories)
        if report.client_type in (ClientTypeForReport.SELF_EMPLOYED, ClientTypeForReport.CORPORATION):
            category_candidates.extend(
                [
                    ExpenseCategoryType.OFFICE_RENT,
                    ExpenseCategoryType.COMMUNICATION,
                    ExpenseCategoryType.VEHICLE,
                    ExpenseCategoryType.MARKETING,
                    ExpenseCategoryType.TRAVEL,
                    ExpenseCategoryType.TRAINING,
                ]
            )
        if report.has_depreciation:
            category_candidates.append(ExpenseCategoryType.DEPRECIATION)
        if rng.random() < 0.45:
            category_candidates.append(ExpenseCategoryType.OTHER)
        unique_categories = list(dict.fromkeys(category_candidates))
        line_count = min(len(unique_categories), rng.randint(1, 4))
        chosen_categories = rng.sample(unique_categories, k=line_count)

        for category in chosen_categories:
            linked_document = None
            client_docs = documents_by_client_id.get(report.client_id, [])
            if client_docs and rng.random() < 0.7:
                linked_document = rng.choice(client_docs)
            expense_line = AnnualReportExpenseLine(
                annual_report_id=report.id,
                category=category,
                amount=_random_decimal(rng, 200, 40_000),
                recognition_rate=default_recognition_rate(category),
                external_document_reference=(
                    (linked_document.original_filename or linked_document.storage_key.split("/")[-1])
                    if linked_document
                    else (f"EXP-{report.tax_year}-{rng.randint(1000, 9999)}" if rng.random() < 0.35 else None)
                ),
                supporting_document_id=linked_document.id if linked_document else None,
                description=rng.choice(
                    [None, "הוצאה מוכרת", "לבדוק התאמה לחשבונית", "מסמך תומך קיים בתיק הלקוח"]
                ),
                created_at=report.created_at,
            )
            db.add(expense_line)
    db.flush()


def create_annual_report_annex_data(db, rng: Random, reports) -> None:
    for report in reports:
        schedule_entries = {
            entry.schedule: entry
            for entry in db.query(AnnualReportScheduleEntry)
            .filter(AnnualReportScheduleEntry.annual_report_id == report.id)
            .all()
        }
        applicable_schedules = _annex_schedules_for_report(report, rng)
        for line_number, schedule in enumerate(applicable_schedules, start=1):
            schedule_entry = schedule_entries.get(schedule)
            if schedule_entry is None:
                continue
            annex_line = AnnualReportAnnexData(
                schedule_entry_id=schedule_entry.id,
                line_number=line_number,
                data=_build_annex_payload(rng, report, schedule),
                notes=rng.choice([None, "אומת מול טפסי 867", "נדרש מסמך תומך", "נבדק מול הנהלת חשבונות"]),
                created_at=report.created_at,
            )
            db.add(annex_line)
    db.flush()


def create_annual_report_status_history(db, rng: Random, reports, users) -> None:
    fallback_user = users[0] if users else None
    users_by_id = {user.id: user for user in users}
    for report in reports:
        history_statuses = _status_path_to(report.status)
        previous = None
        occurred_at = report.created_at
        for status in history_statuses:
            actor_id = report.created_by or report.assigned_to or (fallback_user.id if fallback_user else None)
            if actor_id is None and fallback_user:
                actor_id = fallback_user.id
            occurred_at += timedelta(hours=rng.randint(1, 72))
            actor = users_by_id.get(actor_id)
            entry = AnnualReportStatusHistory(
                annual_report_id=report.id,
                from_status=previous,
                to_status=status,
                changed_by=actor_id,
                changed_by_name=actor.full_name if actor else None,
                note=rng.choice(
                    [
                        "היסטוריית סטטוסים שנוצרה אוטומטית",
                        "עודכן לאחר בדיקת מסמכים",
                        "הועבר לשלב הבא בתהליך",
                    ]
                ),
                occurred_at=occurred_at,
            )
            db.add(entry)
            previous = status
    db.flush()


def create_annual_report_credit_points(db, rng: Random, reports) -> None:
    for report in reports:
        reason_candidates = list(CreditPointReason)
        rng.shuffle(reason_candidates)
        selected = reason_candidates[: rng.randint(1, min(3, len(reason_candidates)))]
        for reason in selected:
            points = Decimal("2.25") if reason == CreditPointReason.RESIDENT else Decimal(str(rng.choice([0.5, 1.0, 1.5, 2.0])))
            db.add(
                AnnualReportCreditPoint(
                    annual_report_id=report.id,
                    reason=reason,
                    points=points,
                    notes=rng.choice([None, "נקודת זיכוי לפי נתוני לקוח"]),
                )
            )
    db.flush()
