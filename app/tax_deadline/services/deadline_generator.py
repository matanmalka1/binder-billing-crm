from datetime import date

from sqlalchemy.orm import Session

from app.businesses.models.business_tax_profile import VatType
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.repositories.business_tax_profile_repository import BusinessTaxProfileRepository
from app.businesses.services.business_lookup import get_business_or_raise
from app.core.exceptions import NotFoundError
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService


# Israeli VAT filing due dates: monthly = 19th of following month,
# bimonthly = 19th of the month after each 2-month period.
_VAT_MONTHLY_DUE_DAY = 19
_ADVANCE_PAYMENT_DUE_DAY = 15
_ANNUAL_REPORT_DUE_MONTH = 4  # April 30 for the prior year
_ANNUAL_REPORT_DUE_DAY = 30


class DeadlineGeneratorService:
    def __init__(self, db: Session):
        self.db = db
        self.deadline_repo = TaxDeadlineRepository(db)
        self.deadline_service = TaxDeadlineService(db)
        self.profile_repo = BusinessTaxProfileRepository(db)
        self.business_repo = BusinessRepository(db)

    def generate_vat_deadlines(self, business_id: int, year: int) -> list:
        get_business_or_raise(self.db, business_id)
        profile = self.profile_repo.get_by_business_id(business_id)
        vat_type = profile.vat_type if profile else None

        if vat_type == VatType.EXEMPT or vat_type is None:
            return []

        due_dates: list[date] = []
        if vat_type == VatType.MONTHLY:
            for month in range(1, 13):
                filing_month = month + 1 if month < 12 else 1
                filing_year = year if month < 12 else year + 1
                due_dates.append(date(filing_year, filing_month, _VAT_MONTHLY_DUE_DAY))
        elif vat_type == VatType.BIMONTHLY:
            # Periods: Jan-Feb, Mar-Apr, May-Jun, Jul-Aug, Sep-Oct, Nov-Dec
            for period_start in range(1, 12, 2):
                filing_month = period_start + 2 if period_start + 2 <= 12 else 1
                filing_year = year if filing_month != 1 else year + 1
                due_dates.append(date(filing_year, filing_month, _VAT_MONTHLY_DUE_DAY))

        created = []
        for due_date in due_dates:
            if not self.deadline_repo.exists(business_id, DeadlineType.VAT, due_date):
                deadline = self.deadline_service.create_deadline(
                    business_id=business_id,
                    deadline_type=DeadlineType.VAT,
                    due_date=due_date,
                    description=f"דוח מע\"מ {year}",
                )
                created.append(deadline)
        return created

    def generate_advance_payment_deadlines(self, business_id: int, year: int) -> list:
        get_business_or_raise(self.db, business_id)
        created = []
        for month in range(1, 13):
            due_date = date(year, month, _ADVANCE_PAYMENT_DUE_DAY)
            if not self.deadline_repo.exists(business_id, DeadlineType.ADVANCE_PAYMENT, due_date):
                deadline = self.deadline_service.create_deadline(
                    business_id=business_id,
                    deadline_type=DeadlineType.ADVANCE_PAYMENT,
                    due_date=due_date,
                    description=f"מקדמה חודש {month}/{year}",
                )
                created.append(deadline)
        return created

    def generate_annual_report_deadline(self, business_id: int, year: int) -> list:
        get_business_or_raise(self.db, business_id)
        due_date = date(year + 1, _ANNUAL_REPORT_DUE_MONTH, _ANNUAL_REPORT_DUE_DAY)
        if self.deadline_repo.exists(business_id, DeadlineType.ANNUAL_REPORT, due_date):
            return []
        deadline = self.deadline_service.create_deadline(
            business_id=business_id,
            deadline_type=DeadlineType.ANNUAL_REPORT,
            due_date=due_date,
            description=f"דוח שנתי שנת {year}",
        )
        return [deadline]

    def generate_all(self, business_id: int, year: int) -> int:
        created = []
        created += self.generate_vat_deadlines(business_id, year)
        created += self.generate_advance_payment_deadlines(business_id, year)
        created += self.generate_annual_report_deadline(business_id, year)
        return len(created)
