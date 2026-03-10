from fastapi import APIRouter, Depends, HTTPException
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.schemas import AnnualReportDetailResponse, StageTransitionRequest
from app.annual_reports.services import AnnualReportService

router = APIRouter(
    prefix="/annual-reports",
    tags=["annual-reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)

STAGE_TO_STATUS = {
    "material_collection": "collecting_docs",
    "in_progress": "docs_complete",
    "final_review": "in_preparation",
    "client_signature": "pending_client",
    "transmitted": "submitted",
}


@router.post("/{report_id}/transition", response_model=AnnualReportDetailResponse)
def transition_stage(report_id: int, body: StageTransitionRequest, db: DBSession, user: CurrentUser):
    target_status = STAGE_TO_STATUS.get(body.to_stage)
    if not target_status:
        raise HTTPException(status_code=400, detail=f"Unknown stage: {body.to_stage}")
    service = AnnualReportService(db)
    return service.transition_status(
        report_id=report_id,
        new_status=target_status,
        changed_by=user.id,
        changed_by_name=user.full_name,
    )
