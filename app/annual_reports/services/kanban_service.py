from app.core.exceptions import AppError
from app.annual_reports.schemas.annual_report_responses import AnnualReportResponse
from app.annual_reports.services.constants import STAGE_TO_STATUS
from .base import AnnualReportBaseService
from .messages import INVALID_STAGE_ERROR


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
            raise AppError(INVALID_STAGE_ERROR.format(stage=to_stage), "ANNUAL_REPORT.INVALID_STAGE")
        return self.transition_status(
            report_id=report_id,
            new_status=target_status,
            changed_by=changed_by,
            changed_by_name=changed_by_name,
        )


__all__ = ["AnnualReportKanbanService"]
