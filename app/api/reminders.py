from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole, ReminderStatus
from app.services.reminder_service import ReminderService

router = APIRouter(
    prefix="/reminders",
    tags=["reminders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("")
def list_reminders(
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
):
    """
    List reminders with optional filters.
    
    Available to ADVISOR and SECRETARY.
    """
    service = ReminderService(db)
    
    # Get all reminders for now (can add pagination later)
    reminders = service.get_pending_reminders()
    
    # Filter by status if provided
    if status:
        reminders = [r for r in reminders if r.status.value == status]
    
    return {"items": reminders, "page": page, "page_size": page_size, "total": len(reminders)}


@router.get("/{reminder_id}")
def get_reminder(
    reminder_id: int,
    db: DBSession,
    user: CurrentUser,
):
    """Get single reminder by ID."""
    from app.models import Reminder
    
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found",
        )
    
    return reminder


@router.post("", status_code=status.HTTP_201_CREATED)
def create_reminder(
    request: dict,  # TODO: Use proper Pydantic schema
    db: DBSession,
    user: CurrentUser,
):
    """
    Create a new reminder.
    
    Available to ADVISOR and SECRETARY.
    """
    service = ReminderService(db)
    
    # Determine which type of reminder to create based on reminder_type
    reminder_type = request.get("reminder_type")
    
    if reminder_type == "TAX_DEADLINE_APPROACHING":
        reminder = service.create_tax_deadline_reminder(
            client_id=request["client_id"],
            tax_deadline_id=request.get("tax_deadline_id"),
            target_date=date.fromisoformat(request["target_date"]),
            days_before=request["days_before"],
            message=request.get("message"),
        )
    elif reminder_type == "BINDER_IDLE":
        reminder = service.create_idle_binder_reminder(
            client_id=request["client_id"],
            binder_id=request.get("binder_id"),
            days_idle=request["days_before"],  # Reuse days_before field
            message=request.get("message"),
        )
    elif reminder_type == "UNPAID_CHARGE":
        reminder = service.create_unpaid_charge_reminder(
            client_id=request["client_id"],
            charge_id=request.get("charge_id"),
            days_unpaid=request["days_before"],  # Reuse days_before field
            message=request.get("message"),
        )
    else:
        # Custom reminder
        # TODO: Add custom reminder support to service
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Custom reminders not yet supported",
        )
    
    return reminder


@router.post("/{reminder_id}/cancel")
def cancel_reminder(
    reminder_id: int,
    db: DBSession,
    user: CurrentUser,
):
    """
    Cancel a pending reminder.
    
    Available to ADVISOR and SECRETARY.
    """
    service = ReminderService(db)
    
    try:
        reminder = service.cancel_reminder(reminder_id)
        if not reminder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder not found",
            )
        return reminder
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{reminder_id}/mark-sent")
def mark_reminder_sent(
    reminder_id: int,
    db: DBSession,
    user: CurrentUser,
):
    """
    Mark a reminder as sent.
    
    Typically used by background jobs.
    Available to ADVISOR and SECRETARY.
    """
    service = ReminderService(db)
    
    reminder = service.mark_sent(reminder_id)
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found",
        )
    
    return reminder