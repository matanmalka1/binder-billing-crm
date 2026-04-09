from datetime import date

from sqlalchemy.orm import Session

from app.common.enums import VatType
from app.clients.repositories.client_repository import ClientRepository
from app.core.exceptions import NotFoundError
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService
from app.tax_deadline.services.constants import (
    VAT_FILING_DUE_DAY,
    ADVANCE_PAYMENT_DUE_DAY,
    ANNUAL_REPORT_DUE_MONTH,
    ANNUAL_REPORT_DUE_DAY,
)


class DeadlineGeneratorService:
    def __init__(self, db: Session):
        self.db = db
        self.deadline_repo = TaxDeadlineRepository(db)
        self.deadline_service = TaxDeadlineService(db)
        self.client_repo = ClientRepository(db)

    def _resolve_vat_type(self, client_id: int):
        client = self.client_repo.get_by_id(client_id)
        return client.vat_reporting_frequency if client else None

    def generate_vat_deadlines(self, client_id: int, year: int) -> list:
        """Generate VAT filing deadlines for the year. Skips EXEMPT clients."""
        vat_type = self._resolve_vat_type(client_id)

        if vat_type == VatType.EXEMPT or vat_type is None:
            return []

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

        created = []
        for due_date, period in due_dates:
            if not self.deadline_repo.exists(client_id, DeadlineType.VAT, due_date):
                deadline = self.deadline_service.create_deadline(
                    client_id=client_id,
                    deadline_type=DeadlineType.VAT,
                    due_date=due_date,
                    period=period,
                    description=f'דוח מע"מ {year}',
                )
                created.append(deadline)
        return created

    def generate_advance_payment_deadlines(self, client_id: int, year: int) -> list:
        """Generate monthly advance payment deadlines (מקדמות) for the year.

        Skips clients exempt from VAT — they are not liable for advance payments.
        """
        if self._resolve_vat_type(client_id) == VatType.EXEMPT:
            return []

        created = []
        for month in range(1, 13):
            due_date = date(year, month, ADVANCE_PAYMENT_DUE_DAY)
            period = f"{year}-{month:02d}"
            if not self.deadline_repo.exists(client_id, DeadlineType.ADVANCE_PAYMENT, due_date):
                deadline = self.deadline_service.create_deadline(
                    client_id=client_id,
                    deadline_type=DeadlineType.ADVANCE_PAYMENT,
                    due_date=due_date,
                    period=period,
                    description=f"מקדמה חודש {month}/{year}",
                )
                created.append(deadline)
        return created

    def generate_annual_report_deadline(self, client_id: int, year: int) -> list:
        """Generate the annual report deadline (April 30 of year+1)."""
        due_date = date(year + 1, ANNUAL_REPORT_DUE_MONTH, ANNUAL_REPORT_DUE_DAY)
        if self.deadline_repo.exists(client_id, DeadlineType.ANNUAL_REPORT, due_date):
            return []
        deadline = self.deadline_service.create_deadline(
            client_id=client_id,
            deadline_type=DeadlineType.ANNUAL_REPORT,
            due_date=due_date,
            description=f"דוח שנתי שנת {year}",
        )
        return [deadline]

    def generate_all(self, client_id: int, year: int) -> int:
        """Generate all deadlines for a client and year. Idempotent.

        Note: NATIONAL_INSURANCE (ביטוח לאומי) deadlines are not auto-generated —
        NI payment schedules require per-client calculation parameters
        not yet stored in the domain. Create manually via POST /api/v1/tax-deadlines.
        """
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        created = []
        created += self.generate_vat_deadlines(client_id, year)
        created += self.generate_advance_payment_deadlines(client_id, year)
        created += self.generate_annual_report_deadline(client_id, year)
        return len(created)
