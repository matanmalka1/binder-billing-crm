from typing import Any

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.annual_reports.models.annual_report_model import AnnualReport
from app.annual_reports.schemas.annual_report_responses import AnnualReportResponse


class AnnualReportBaseService:
    """Shared helpers for annual report service mixins."""

    repo: Any  # set by concrete service
    business_repo: Any  # set by concrete service
    user_repo: Any  # set by concrete service

    def _get_or_raise(self, report_id: int) -> AnnualReport:
        report = self.repo.get_by_id(report_id)
        if not report:
            raise NotFoundError(f"דוח שנתי {report_id} לא נמצא", "ANNUAL_REPORT.NOT_FOUND")
        return report

    def _to_responses(self, reports: list[AnnualReport]) -> list[AnnualReportResponse]:
        """
        Project ORM instances to AnnualReportResponse, populating client context.
        Reports are now client-scoped; business_name is resolved from the client's
        primary business (first non-deleted business) for display purposes.
        """
        if not reports:
            return []

        from app.clients.repositories.client_repository import ClientRepository
        client_repo = ClientRepository(self.db)

        client_ids = {r.client_id for r in reports}
        clients = {c.id: c for c in client_repo.list_by_ids(list(client_ids))} if client_ids else {}

        from app.actions.report_deadline_actions import get_annual_report_actions
        result = []
        for r in reports:
            obj = AnnualReportResponse.model_validate(r)
            client = clients.get(r.client_id)
            if client:
                obj.client_name = client.full_name
                obj.business_name = client.full_name
            obj.available_actions = get_annual_report_actions(r.id, r.status.value if hasattr(r.status, "value") else str(r.status))
            result.append(obj)
        return result
