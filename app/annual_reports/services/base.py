from typing import Any

from app.annual_reports.models import AnnualReport
from app.annual_reports.schemas.annual_report import AnnualReportResponse


class AnnualReportBaseService:
    """Shared helpers for annual report service mixins."""

    repo: Any  # set by concrete service
    client_repo: Any  # set by concrete service

    def _get_or_raise(self, report_id: int) -> AnnualReport:
        report = self.repo.get_by_id(report_id)
        if not report:
            raise ValueError(f"דוח שנתי {report_id} לא נמצא")
        return report

    def _to_responses(self, reports: list[AnnualReport]) -> list[AnnualReportResponse]:
        """
        Project ORM instances to AnnualReportResponse, populating client_name
        from the client repository rather than mutating the ORM objects.
        """
        if not reports:
            return []
        client_ids = {r.client_id for r in reports}
        clients = self.client_repo.list_by_ids(list(client_ids)) if client_ids else []
        id_to_name = {c.id: c.full_name for c in clients}
        result = []
        for r in reports:
            obj = AnnualReportResponse.model_validate(r)
            obj.client_name = id_to_name.get(r.client_id)
            result.append(obj)
        return result
