import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_enums import ClientTypeForReport
from app.annual_reports.services.annual_report_service import AnnualReportService
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.common.enums import EntityType
from app.core.exceptions import ConflictError, NotFoundError
from app.clients.constants import (
    CLIENT_OBLIGATION_NEXT_YEAR_START_MONTH,
    CLIENT_OBLIGATION_TRIGGER_FIELDS,
    ENTITY_TYPE_TO_REPORT_CLIENT_TYPE,
)
from app.tax_deadline.services.deadline_generator import DeadlineGeneratorService

_log = logging.getLogger(__name__)


@dataclass(slots=True)
class ObligationResult:
    deadlines_created: int = 0
    reports_created: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total_created(self) -> int:
        return self.deadlines_created + self.reports_created


def _years_to_generate(reference_date: Optional[date] = None) -> list[int]:
    if not 2 <= CLIENT_OBLIGATION_NEXT_YEAR_START_MONTH <= 12:
        raise ValueError("CLIENT_OBLIGATION_NEXT_YEAR_START_MONTH must be between 2 and 12")
    today = reference_date or date.today()
    years = [today.year]
    if today.month >= CLIENT_OBLIGATION_NEXT_YEAR_START_MONTH:
        years.append(today.year + 1)
    return years


def _derive_client_type(entity_type: Optional[EntityType]) -> ClientTypeForReport:
    if entity_type is None or entity_type not in ENTITY_TYPE_TO_REPORT_CLIENT_TYPE:
        raise ValueError("סוג ישות לא נתמך ליצירת דוח שנתי")
    return ENTITY_TYPE_TO_REPORT_CLIENT_TYPE[entity_type]


def generate_client_obligations(
    db: Session,
    client_record_id: int,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
    entity_type: Optional[EntityType] = None,
    reference_date: Optional[date] = None,
    best_effort: bool = False,
) -> int:
    return generate_client_obligations_result(
        db=db,
        client_record_id=client_record_id,
        actor_id=actor_id,
        actor_name=actor_name,
        entity_type=entity_type,
        reference_date=reference_date,
        best_effort=best_effort,
    ).total_created


def generate_client_obligations_result(
    db: Session,
    client_record_id: int,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
    entity_type: Optional[EntityType] = None,
    reference_date: Optional[date] = None,
    best_effort: bool = False,
) -> ObligationResult:
    """
    יצירת מועדי מס ודוחות שנתיים ללקוח לשנה הנוכחית (ולשנה הבאה ברבעון הרביעי).
    פעולה אידמפוטנטית — מועדים ודוחות קיימים מדולגים.
    מחזירה פירוט יצירה לפי מועדים/דוחות ורשימת שגיאות.

    best_effort=False (ברירת מחדל — לשימוש בזרימות יצירה):
        שגיאות מועלות מיד לאחר rollback של ה-savepoint.
        הכשל מתגלגל למעלה, get_db() מבצע rollback לטרנזקציה הראשית — אין נתונים עצומים.

    best_effort=True — לשימוש בזרימות עדכון:
        שגיאות נרשמות בלוג, ה-savepoint מבוצע rollback, והפונקציה מחזירה.
        הטרנזקציה הראשית נשמרת — הישות המעדכנת כבר flushed ותבוצע commit בסיום הבקשה.

    חשוב: ב-best_effort=True זהו partial-success design מכוון.
    מועדי המס והדוחות השנתיים נוצרים בשני שלבים נפרדים, וכל שנה נשמרת ב-savepoint עצמאי.
    לכן ייתכן מצב שבו חלק מהמועדים נוצרו בלי דוח שנתי תואם, או להפך, אם שלב אחר נכשל.
    """
    years = _years_to_generate(reference_date)
    result = ObligationResult()
    if not ClientRecordRepository(db).get_by_id(client_record_id):
        if best_effort:
            return result
        raise NotFoundError(
            f"רשומת לקוח עבור מזהה {client_record_id} לא נמצאה",
            "CLIENT_RECORD.NOT_FOUND",
        )

    client_type = _derive_client_type(entity_type).value
    deadline_generator = DeadlineGeneratorService(db)
    # Intentional partial-success boundary: deadline generation is isolated per year.
    for year in years:
        sp = db.begin_nested()  # SAVEPOINT — חוסם rollback של הטרנזקציה הראשית
        try:
            result.deadlines_created += deadline_generator.generate_all(client_record_id, year)
            sp.commit()  # RELEASE SAVEPOINT
        except Exception:
            sp.rollback()  # ROLLBACK TO SAVEPOINT בלבד
            _log.exception("שגיאה ביצירת מועדי מס ללקוח %s שנה %s", client_record_id, year)
            if not best_effort:
                raise
            result.errors.append(f"deadline_generation_failed:{year}")

    report_service = AnnualReportService(db)
    _actor_name = actor_name or ""
    # Intentional partial-success boundary: annual reports are isolated from deadline savepoints.
    for year in years:
        sp = db.begin_nested()  # SAVEPOINT
        try:
            report_service.create_report(
                client_record_id=client_record_id,
                tax_year=year,
                client_type=client_type,
                created_by=actor_id,
                created_by_name=_actor_name,
            )
            result.reports_created += 1
            sp.commit()  # RELEASE SAVEPOINT
        except ConflictError:
            sp.rollback()  # דוח קיים — מדלגים; חייבים לסיים את ה-savepoint
        except Exception:
            sp.rollback()  # ROLLBACK TO SAVEPOINT בלבד
            _log.exception("שגיאה ביצירת דוח שנתי ללקוח %s שנה %s", client_record_id, year)
            if not best_effort:
                raise
            result.errors.append(f"annual_report_creation_failed:{year}")

    return result


def obligation_fields_changed(fields: dict) -> bool:
    """Return True if any key in fields affects obligation generation."""
    return bool(CLIENT_OBLIGATION_TRIGGER_FIELDS.intersection(fields))
