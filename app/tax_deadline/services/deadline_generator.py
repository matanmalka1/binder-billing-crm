from datetime import date

from sqlalchemy.orm import Session

_today = date.today  # injectable for tests

from app.common.enums import VatType
from app.clients.constants import ENTITY_TYPE_TO_REPORT_CLIENT_TYPE
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.annual_reports.services.deadlines import standard_deadline
from app.core.exceptions import NotFoundError
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService
from app.tax_deadline.services.constants import VAT_FILING_DUE_DAY, ADVANCE_PAYMENT_DUE_DAY


class DeadlineGeneratorService:
    def __init__(self, db: Session):
        self.db = db
        self.deadline_repo = TaxDeadlineRepository(db)
        self.deadline_service = TaxDeadlineService(db)
        self.client_record_repo = ClientRecordRepository(db)

    def _resolve_vat_type(self, client_record_id: int):
        record = self.client_record_repo.get_by_id(client_record_id)
        if not record:
            return None
        legal_entity = LegalEntityRepository(self.db).get_by_id(record.legal_entity_id)
        return legal_entity.vat_reporting_frequency if legal_entity else None

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
                due_dates.append((date(filing_year, filing_month, VAT_FILING_DUE_DAY), period))
        elif vat_type == VatType.BIMONTHLY:
            # Periods: Jan-Feb, Mar-Apr, May-Jun, Jul-Aug, Sep-Oct, Nov-Dec
            for period_start in range(1, 12, 2):
                filing_month = period_start + 2 if period_start + 2 <= 12 else 1
                filing_year = year if filing_month != 1 else year + 1
                period = f"{year}-{period_start:02d}"
                due_dates.append((date(filing_year, filing_month, VAT_FILING_DUE_DAY), period))

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

        Skips clients exempt from VAT — they are not liable for advance payments.
        """
        if self._resolve_vat_type(client_record_id) == VatType.EXEMPT:
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
