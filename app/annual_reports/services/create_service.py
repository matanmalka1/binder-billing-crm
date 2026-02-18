from typing import Optional

from app.annual_reports.models import (
    AnnualReport,
    AnnualReportStatus,
    ClientTypeForReport,
    DeadlineType,
)
from app.clients.repositories.client_repository import ClientRepository
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
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        try:
            ct = ClientTypeForReport(client_type)
        except ValueError:
            valid = [e.value for e in ClientTypeForReport]
            raise ValueError(f"Invalid client_type '{client_type}'. Valid: {valid}")

        try:
            dt = DeadlineType(deadline_type)
        except ValueError:
            valid = [e.value for e in DeadlineType]
            raise ValueError(f"Invalid deadline_type '{deadline_type}'. Valid: {valid}")

        existing = self.repo.get_by_client_year(client_id, tax_year)
        if existing:
            raise ValueError(
                f"Annual report for client {client_id} tax year {tax_year} already exists "
                f"(id={existing.id}, status={existing.status.value})"
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
                f"Report created. Form: {form_type.value}, Deadline: "
                f"{filing_deadline.strftime('%d/%m/%Y') if filing_deadline else 'TBD'}"
            ),
        )

        return report
