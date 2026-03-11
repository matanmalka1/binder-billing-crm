from app.core.exceptions import AppError
from app.annual_reports.schemas.annual_report import AnnualReportResponse
from .base import AnnualReportBaseService


STAGE_TO_STATUS: dict[str, str] = {
    "material_collection": "collecting_docs",
    "in_progress": "docs_complete",
    "final_review": "in_preparation",
    "client_signature": "pending_client",
    "transmitted": "submitted",
}


class AnnualReportKanbanService(AnnualReportBaseService):
    def transition_stage(
        self,
        report_id: int,
        to_stage: str,
        changed_by: int,
        changed_by_name: str,
    ) -> AnnualReportResponse:
        target_status = STAGE_TO_STATUS.get(to_stage)
        if not target_status:
            raise AppError(f"שלב לא חוקי: {to_stage}", "ANNUAL_REPORT.INVALID_STAGE")
        return self.transition_status(
            report_id=report_id,
            new_status=target_status,
            changed_by=changed_by,
            changed_by_name=changed_by_name,
        )


__all__ = ["AnnualReportKanbanService", "STAGE_TO_STATUS"]
