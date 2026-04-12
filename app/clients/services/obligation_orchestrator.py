import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_enums import ClientTypeForReport
from app.annual_reports.services.annual_report_service import AnnualReportService
from app.common.enums import EntityType
from app.core.exceptions import ConflictError
from app.tax_deadline.services.deadline_generator import DeadlineGeneratorService

_log = logging.getLogger(__name__)
_Q4_START_MONTH = 10  # אוקטובר — מרבעון ד׳ מייצרים גם שנה הבאה

_ENTITY_TYPE_TO_REPORT_CLIENT_TYPE: dict[Optional[EntityType], ClientTypeForReport] = {
    EntityType.OSEK_PATUR: ClientTypeForReport.SELF_EMPLOYED,
    EntityType.OSEK_MURSHE: ClientTypeForReport.SELF_EMPLOYED,
    EntityType.COMPANY_LTD: ClientTypeForReport.CORPORATION,
    EntityType.EMPLOYEE: ClientTypeForReport.INDIVIDUAL,
    None: ClientTypeForReport.INDIVIDUAL,
}

# שדות בפרופיל הלקוח שמשפיעים על סוג/היקף החובות שנוצרות.
# שינוי בכל אחד מהם מפעיל regeneration.
_OBLIGATION_FIELDS = frozenset({
    "entity_type",
    "vat_reporting_frequency",
})


def _years_to_generate(reference_date: Optional[date] = None) -> list[int]:
    today = reference_date or date.today()
    years = [today.year]
    if today.month >= _Q4_START_MONTH:
        years.append(today.year + 1)
    return years


def _derive_client_type(entity_type: Optional[EntityType]) -> ClientTypeForReport:
    return _ENTITY_TYPE_TO_REPORT_CLIENT_TYPE.get(entity_type, ClientTypeForReport.INDIVIDUAL)


def generate_client_obligations(
    db: Session,
    client_id: int,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
    entity_type: Optional[EntityType] = None,
    reference_date: Optional[date] = None,
    best_effort: bool = False,
) -> int:
    """
    יצירת מועדי מס ודוחות שנתיים ללקוח לשנה הנוכחית (ולשנה הבאה ברבעון הרביעי).
    פעולה אידמפוטנטית — מועדים ודוחות קיימים מדולגים.
    מחזירה את מספר הישויות שנוצרו.

    best_effort=False (ברירת מחדל — לשימוש בזרימות עדכון):
        שגיאות נרשמות בלוג, מבוצע rollback לניקוי ה-session, והפונקציה מחזירה.
        מתאים לזרימות שבהן הישות כבר בוצעה commit ואין טעם להכשיל את הקריאה.

    best_effort=True — לשימוש בזרימות יצירה:
        שגיאות מועלות מיד לאחר rollback.
        הישות עצמה כבר committed (מגבלת ארכיטקטורת ה-repo), אך הכשל גלוי למשתמש
        ומאפשר ריצה חוזרת של POST /tax-deadlines/generate ו-POST /annual-reports לתיקון.
    """
    years = _years_to_generate(reference_date)
    total = 0

    deadline_generator = DeadlineGeneratorService(db)
    for year in years:
        try:
            total += deadline_generator.generate_all(client_id, year)
        except Exception:
            db.rollback()
            _log.exception("שגיאה ביצירת מועדי מס ללקוח %s שנה %s", client_id, year)
            if not best_effort:
                raise

    report_service = AnnualReportService(db)
    client_type = _derive_client_type(entity_type).value
    _actor_name = actor_name or ""
    for year in years:
        try:
            report_service.create_report(
                client_id=client_id,
                tax_year=year,
                client_type=client_type,
                created_by=actor_id,
                created_by_name=_actor_name,
            )
            total += 1
        except ConflictError:
            pass  # דוח קיים — מדלגים
        except Exception:
            db.rollback()
            _log.exception("שגיאה ביצירת דוח שנתי ללקוח %s שנה %s", client_id, year)
            if not best_effort:
                raise

    return total


def obligation_fields_changed(fields: dict) -> bool:
    """Return True if any key in fields affects obligation generation."""
    return bool(_OBLIGATION_FIELDS.intersection(fields))
