from typing import Any

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.annual_reports.models import AnnualReport
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
        Project ORM instances to AnnualReportResponse, populating client context
        from the client repository rather than mutating the ORM objects.
        """
        if not reports:
            return []
        business_ids = {r.business_id for r in reports}
        businesses = self.business_repo.list_by_ids(list(business_ids)) if business_ids else []
        id_to_context = {
            b.id: {
                "client_id": b.client_id,
                "client_name": b.full_name,
                "business_name": b.business_name,
            }
            for b in businesses
        }
        from app.actions.report_deadline_actions import get_annual_report_actions
        result = []
        for r in reports:
            obj = AnnualReportResponse.model_validate(r)
            context = id_to_context.get(r.business_id, {})
            obj.client_id = context.get("client_id")
            obj.client_name = context.get("client_name")
            obj.business_name = context.get("business_name")
            obj.available_actions = get_annual_report_actions(r.id, r.status.value if hasattr(r.status, "value") else str(r.status))
            result.append(obj)
        return result
