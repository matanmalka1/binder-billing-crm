from datetime import date

from sqlalchemy.orm import Session

_today = date.today  # injectable for tests

from app.common.enums import EntityType, VatType
from app.clients.constants import ENTITY_TYPE_TO_REPORT_CLIENT_TYPE
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.annual_reports.services.deadlines import standard_deadline
from app.core.exceptions import NotFoundError
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService
from app.tax_deadline.services.constants import ADVANCE_PAYMENT_DUE_DAY
from app.vat_reports.services.constants import VAT_ONLINE_EXTENDED_DEADLINE_DAY as _VAT_FALLBACK_DUE_DAY

try:
    from tax_rules import get_effective_periodic_date as _get_vat_date
    _VAT_CALENDAR_COLUMN = "effective_vat_periodic_and_income_tax_advances"
    _VAT_CALENDAR_AVAILABLE = True
except ImportError:
    _VAT_CALENDAR_AVAILABLE = False


def _vat_due_date(filing_year: int, filing_month: int, calendar_period: str) -> date:
    """Return VAT due date from official calendar; fall back to fixed day-19."""
    if _VAT_CALENDAR_AVAILABLE:
        try:
            raw = _get_vat_date(filing_year, calendar_period, _VAT_CALENDAR_COLUMN)
        except KeyError:
            raw = None
        if raw:
            return date.fromisoformat(raw)
    return date(filing_year, filing_month, _VAT_FALLBACK_DUE_DAY)


class DeadlineGeneratorService:
    def __init__(self, db: Session):
        self.db = db
        self.deadline_repo = TaxDeadlineRepository(db)
        self.deadline_service = TaxDeadlineService(db)
        self.client_record_repo = ClientRecordRepository(db)

    def _resolve_legal_entity(self, client_record_id: int):
        record = self.client_record_repo.get_by_id(client_record_id)
        if not record:
            return None
        return LegalEntityRepository(self.db).get_by_id(record.legal_entity_id)

    def _resolve_vat_type(self, client_record_id: int):
        entity = self._resolve_legal_entity(client_record_id)
        return entity.vat_reporting_frequency if entity else None

    def _resolve_entity_type(self, client_record_id: int):
        entity = self._resolve_legal_entity(client_record_id)
        return entity.entity_type if entity else None

    def _resolve_client_record_id(self, client_record_id: int) -> int:
        record = self.client_record_repo.get_by_id(client_record_id)
        return record.id if record else None

    def generate_vat_deadlines(self, client_record_id: int, year: int) -> list:
        """Generate VAT filing deadlines for the year. Skips EXEMPT clients."""
        vat_type = self._resolve_vat_type(client_record_id)

        if vat_type == VatType.EXEMPT or vat_type is None:
            return []

        client_record_id = self._resolve_client_record_id(client_record_id)

        due_dates: list[tuple[date, str]] = []  # (due_date, period)
        if vat_type == VatType.MONTHLY:
            for month in range(1, 13):
                filing_month = month + 1 if month < 12 else 1
                filing_year = year if month < 12 else year + 1
                period = f"{year}-{month:02d}"
                # Calendar key = reporting period (the month being reported)
                calendar_period = f"{year}-{month:02d}"
                due_dates.append((_vat_due_date(filing_year, filing_month, calendar_period), period))
        elif vat_type == VatType.BIMONTHLY:
            # Periods: Jan-Feb, Mar-Apr, May-Jun, Jul-Aug, Sep-Oct, Nov-Dec
            for period_start in range(1, 12, 2):
                period_end = period_start + 1
                filing_month = period_start + 2 if period_start + 2 <= 12 else 1
                filing_year = year if filing_month != 1 else year + 1
                period = f"{year}-{period_start:02d}"
                # Calendar key = second month of the bimonthly period (per calendar spec)
                calendar_period = f"{year}-{period_end:02d}"
                due_dates.append((_vat_due_date(filing_year, filing_month, calendar_period), period))

        today = _today()
        created = []
        for due_date, period in due_dates:
            if due_date < today:
                continue
            if not self.deadline_repo.exists_by_record(client_record_id, DeadlineType.VAT, period=period):
                deadline = self.deadline_service.create_deadline(
                    client_record_id=client_record_id,
                    deadline_type=DeadlineType.VAT,
                    due_date=due_date,
                    period=period,
                    description=f'דוח מע"מ {year}',
                )
                created.append(deadline)
        return created

    def generate_advance_payment_deadlines(self, client_record_id: int, year: int) -> list:
        """Generate monthly advance payment deadlines (מקדמות) for the year.

        Skips employees — they have no income tax advance payment obligation.
        Osek patur clients are exempt from VAT but still liable for advance payments.
        """
        if self._resolve_entity_type(client_record_id) == EntityType.EMPLOYEE:
            return []

        client_record_id = self._resolve_client_record_id(client_record_id)
        today = _today()
        created = []
        for month in range(1, 13):
            due_date = date(year, month, ADVANCE_PAYMENT_DUE_DAY)
            if due_date < today:
                continue
            period = f"{year}-{month:02d}"
            if not self.deadline_repo.exists_by_record(client_record_id, DeadlineType.ADVANCE_PAYMENT, period=period):
                deadline = self.deadline_service.create_deadline(
                    client_record_id=client_record_id,
                    deadline_type=DeadlineType.ADVANCE_PAYMENT,
                    due_date=due_date,
                    period=period,
                    description=f"מקדמה חודש {month}/{year}",
                )
                created.append(deadline)
        return created

    def generate_annual_report_deadline(self, client_record_id: int, year: int) -> list:
        """Generate the annual report deadline using the filing profile."""
        record = self.client_record_repo.get_by_id(client_record_id)
        legal_entity = (
            LegalEntityRepository(self.db).get_by_id(record.legal_entity_id)
            if record
            else None
        )
        client_type = ENTITY_TYPE_TO_REPORT_CLIENT_TYPE.get(
            legal_entity.entity_type if legal_entity else None
        )
        due_date = standard_deadline(year, client_type=client_type).date()
        client_record_id = self._resolve_client_record_id(client_record_id)
        if self.deadline_repo.exists_by_record(
            client_record_id,
            DeadlineType.ANNUAL_REPORT,
            tax_year=year,
        ):
            return []
        deadline = self.deadline_service.create_deadline(
            client_record_id=client_record_id,
            deadline_type=DeadlineType.ANNUAL_REPORT,
            due_date=due_date,
            tax_year=year,
            description=f"דוח שנתי שנת {year}",
        )
        return [deadline]

    def generate_all(self, client_record_id: int, year: int) -> int:
        """Generate all deadlines for a client and year. Idempotent.

        Note: NATIONAL_INSURANCE (ביטוח לאומי) deadlines are not auto-generated —
        NI payment schedules require per-client calculation parameters
        not yet stored in the domain. Create manually via POST /api/v1/tax-deadlines.
        """
        record = self.client_record_repo.get_by_id(client_record_id)
        if not record:
            raise NotFoundError(f"רשומת לקוח {client_record_id} לא נמצאה", "CLIENT_RECORD.NOT_FOUND")
        created = []
        created += self.generate_vat_deadlines(client_record_id, year)
        created += self.generate_advance_payment_deadlines(client_record_id, year)
        created += self.generate_annual_report_deadline(client_record_id, year)
        return len(created)
