from typing import Optional

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.annual_reports.models import (
    AnnualReport,
    AnnualReportStatus,
    ClientTypeForReport,
    DeadlineType,
)
from app.clients.repositories.client_repository import ClientRepository
from app.clients.services.client_lookup import get_client_or_raise
from app.users.repositories.user_repository import UserRepository
from app.utils.time import utcnow
from .constants import FORM_MAP
from .deadlines import extended_deadline, standard_deadline
from .base import AnnualReportBaseService


class AnnualReportCreateService(AnnualReportBaseService):
    client_repo: ClientRepository

    def create_report(
        self,
        client_id: int,
        tax_year: int,
        client_type: str,
        created_by: int,
        created_by_name: str,
        deadline_type: str = "standard",
        assigned_to: Optional[int] = None,
        notes: Optional[str] = None,
        # Income flags for schedule auto-generation
        has_rental_income: bool = False,
        has_capital_gains: bool = False,
        has_foreign_income: bool = False,
        has_depreciation: bool = False,
        has_exempt_rental: bool = False,
    ) -> AnnualReport:
        """Create an annual report and initial schedules/history."""
        get_client_or_raise(self.client_repo, client_id)

        try:
            ct = ClientTypeForReport(client_type)
        except ValueError:
            valid = [e.value for e in ClientTypeForReport]
            raise AppError(
                f"סוג לקוח לא חוקי '{client_type}'. חוקיים: {valid}",
                "ANNUAL_REPORT.INVALID_TYPE",
            )

        try:
            dt = DeadlineType(deadline_type)
        except ValueError:
            valid = [e.value for e in DeadlineType]
            raise AppError(
                f"סוג מועד אחרון לא חוקי '{deadline_type}'. חוקיים: {valid}",
                "ANNUAL_REPORT.INVALID_TYPE",
            )

        if assigned_to is not None:
            user_repo = UserRepository(self.db)
            if not user_repo.get_by_id(assigned_to):
                raise NotFoundError(f"משתמש מוקצה {assigned_to} לא נמצא", "ANNUAL_REPORT.NOT_FOUND")

        existing = self.repo.get_by_client_year(client_id, tax_year)
        if existing:
            raise ConflictError(
                f"דוח שנתי ללקוח {client_id} לשנת מס {tax_year} כבר קיים "
                f"(id={existing.id}, status={existing.status.value})",
                "ANNUAL_REPORT.CONFLICT",
            )

        form_type = FORM_MAP[ct]
        if dt == DeadlineType.STANDARD:
            filing_deadline = standard_deadline(tax_year)
        elif dt == DeadlineType.EXTENDED:
            filing_deadline = extended_deadline(tax_year)
        else:
            filing_deadline = None  # custom — caller can set note

        report = self.repo.create(
            client_id=client_id,
            tax_year=tax_year,
            client_type=ct,
            form_type=form_type,
            created_by=created_by,
            assigned_to=assigned_to,
            status=AnnualReportStatus.NOT_STARTED,
            deadline_type=dt,
            filing_deadline=filing_deadline,
            notes=notes,
            has_rental_income=has_rental_income,
            has_capital_gains=has_capital_gains,
            has_foreign_income=has_foreign_income,
            has_depreciation=has_depreciation,
            has_exempt_rental=has_exempt_rental,
        )

        # Auto-generate required schedules
        self._generate_schedules(report)

        self.repo.append_status_history(
            annual_report_id=report.id,
            from_status=None,
            to_status=AnnualReportStatus.NOT_STARTED,
            changed_by=created_by,
            changed_by_name=created_by_name,
            note=(
                f"הדוח נוצר. טופס: {form_type.value}, מועד אחרון: "
                f"{filing_deadline.strftime('%d/%m/%Y') if filing_deadline else 'TBD'}"
            ),
        )

        return report
