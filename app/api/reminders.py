from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole
from app.schemas.reminders import (
    ReminderCreateRequest,
    ReminderListResponse,
    ReminderResponse,
)
from app.services.reminder_service import ReminderService

router = APIRouter(
    prefix="/reminders",
    tags=["reminders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("", response_model=ReminderListResponse)
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
    
    # Delegate to service - no business logic here
    items, total = service.get_pending_reminders(page=page, page_size=page_size)
    
    # TODO: Filter by status if provided (requires service method)
    if status:
        items = [r for r in items if r.status.value == status]
        total = len(items)
    
    return ReminderListResponse(
        items=[ReminderResponse.model_validate(r) for r in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{reminder_id}", response_model=ReminderResponse)
def get_reminder(
    reminder_id: int,
    db: DBSession,
    user: CurrentUser,
):
    """Get single reminder by ID."""
    service = ReminderService(db)
    
    # Delegate to service
    reminder = service.get_reminder(reminder_id)
    
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found",
        )
    
    return ReminderResponse.model_validate(reminder)


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(
    request: ReminderCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """
    Create a new reminder.
    
    Available to ADVISOR and SECRETARY.
    """
    service = ReminderService(db)
    
    try:
        # Delegate based on reminder type - service handles all business logic
        if request.reminder_type == "tax_deadline_approaching":
            if not request.tax_deadline_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="tax_deadline_id required for tax deadline reminders",
                )
            
            reminder = service.create_tax_deadline_reminder(
                client_id=request.client_id,
                tax_deadline_id=request.tax_deadline_id,
                target_date=request.target_date,
                days_before=request.days_before,
                message=request.message,
            )
            
        elif request.reminder_type == "binder_idle":
            if not request.binder_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="binder_id required for binder idle reminders",
                )
            
            reminder = service.create_idle_binder_reminder(
                client_id=request.client_id,
                binder_id=request.binder_id,
                days_idle=request.days_before,
                message=request.message,
            )
            
        elif request.reminder_type == "unpaid_charge":
            if not request.charge_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="charge_id required for unpaid charge reminders",
                )
            
            reminder = service.create_unpaid_charge_reminder(
                client_id=request.client_id,
                charge_id=request.charge_id,
                days_unpaid=request.days_before,
                message=request.message,
            )
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported reminder type: {request.reminder_type}",
            )
        
        return ReminderResponse.model_validate(reminder)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{reminder_id}/cancel", response_model=ReminderResponse)
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
        # Delegate to service
        reminder = service.cancel_reminder(reminder_id)
        return ReminderResponse.model_validate(reminder)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{reminder_id}/mark-sent", response_model=ReminderResponse)
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
    
    try:
        # Delegate to service
        reminder = service.mark_sent(reminder_id)
        return ReminderResponse.model_validate(reminder)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )