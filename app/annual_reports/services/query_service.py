from typing import Optional

from app.annual_reports.models import AnnualReport
from .base import AnnualReportBaseService


class AnnualReportQueryService(AnnualReportBaseService):
    def get_report(self, report_id: int) -> Optional[AnnualReport]:
        return self.repo.get_by_id(report_id)

    def get_client_reports(self, client_id: int) -> list[AnnualReport]:
        return self.repo.list_by_client(client_id)

    def list_reports(
        self,
        tax_year: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AnnualReport], int]:
        if tax_year is not None:
            items = self.repo.list_by_tax_year(tax_year, page=page, page_size=page_size)
            total = self.repo.count_by_tax_year(tax_year)
        else:
            items = self.repo.list_all(page=page, page_size=page_size)
            total = self.repo.count_all()
        return items, total

    def get_season_summary(self, tax_year: int) -> dict:
        return self.repo.get_season_summary(tax_year)

    def get_overdue(self, tax_year: Optional[int] = None) -> list[AnnualReport]:
        return self.repo.list_overdue(tax_year=tax_year)

    def get_status_history(self, report_id: int) -> list:
        self._get_or_raise(report_id)
        return self.repo.get_status_history(report_id)
