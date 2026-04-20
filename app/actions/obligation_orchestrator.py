import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_enums import ClientTypeForReport
from app.annual_reports.services.annual_report_service import AnnualReportService
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.services.client_record_link_service import ClientRecordLinkService
from app.common.enums import EntityType
from app.core.exceptions import ConflictError, NotFoundError
from app.clients.constants import (
    CLIENT_OBLIGATION_NEXT_YEAR_START_MONTH,
    CLIENT_OBLIGATION_TRIGGER_FIELDS,
    ENTITY_TYPE_TO_REPORT_CLIENT_TYPE,
)
from app.tax_deadline.services.deadline_generator import DeadlineGeneratorService

_log = logging.getLogger(__name__)


def _years_to_generate(reference_date: Optional[date] = None) -> list[int]:
    today = reference_date or date.today()
    years = [today.year]
    if today.month >= CLIENT_OBLIGATION_NEXT_YEAR_START_MONTH:
        years.append(today.year + 1)
    return years


def _derive_client_type(entity_type: Optional[EntityType]) -> ClientTypeForReport:
    return ENTITY_TYPE_TO_REPORT_CLIENT_TYPE.get(entity_type, ClientTypeForReport.INDIVIDUAL)


def _resolve_client_record_id(db: Session, client_or_record_id: int) -> int | None:
    record = ClientRecordRepository(db).get_by_id(client_or_record_id)
    if record:
        return record.id
    linked = ClientRecordLinkService(db).get_client_record_by_client_id(client_or_record_id)
    return linked.id if linked else None


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

    best_effort=False (ברירת מחדל — לשימוש בזרימות יצירה):
        שגיאות מועלות מיד לאחר rollback של ה-savepoint.
        הכשל מתגלגל למעלה, get_db() מבצע rollback לטרנזקציה הראשית — אין נתונים עצומים.

    best_effort=True — לשימוש בזרימות עדכון:
        שגיאות נרשמות בלוג, ה-savepoint מבוצע rollback, והפונקציה מחזירה.
        הטרנזקציה הראשית נשמרת — הישות המעדכנת כבר flushed ותבוצע commit בסיום הבקשה.
    """
    years = _years_to_generate(reference_date)
    total = 0
    client_record_id = _resolve_client_record_id(db, client_id)
    if client_record_id is None:
        if best_effort:
            return total
        raise NotFoundError(
            f"רשומת לקוח עבור מזהה {client_id} לא נמצאה",
            "CLIENT_RECORD.NOT_FOUND",
        )

    deadline_generator = DeadlineGeneratorService(db)
    for year in years:
        sp = db.begin_nested()  # SAVEPOINT — חוסם rollback של הטרנזקציה הראשית
        try:
            total += deadline_generator.generate_all(client_record_id, year)
            sp.commit()  # RELEASE SAVEPOINT
        except Exception:
            sp.rollback()  # ROLLBACK TO SAVEPOINT בלבד
            _log.exception("שגיאה ביצירת מועדי מס ללקוח %s שנה %s", client_id, year)
            if not best_effort:
                raise

    report_service = AnnualReportService(db)
    client_type = _derive_client_type(entity_type).value
    _actor_name = actor_name or ""
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
            total += 1
            sp.commit()  # RELEASE SAVEPOINT
        except ConflictError:
            sp.rollback()  # דוח קיים — מדלגים; חייבים לסיים את ה-savepoint
        except Exception:
            sp.rollback()  # ROLLBACK TO SAVEPOINT בלבד
            _log.exception("שגיאה ביצירת דוח שנתי ללקוח %s שנה %s", client_id, year)
            if not best_effort:
                raise

    return total


def obligation_fields_changed(fields: dict) -> bool:
    """Return True if any key in fields affects obligation generation."""
    return bool(CLIENT_OBLIGATION_TRIGGER_FIELDS.intersection(fields))
