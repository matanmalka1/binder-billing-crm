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
    status_filter: Optional[str] = Query(None, alias="status"),
):
    """
    List reminders with optional status filter.

    When no status is provided, returns pending reminders whose send_on <= today
    (the operational work queue).

    When status is provided, returns all reminders of that status across all dates
    (history / audit view). Valid values: pending, sent, canceled.

    Available to ADVISOR and SECRETARY.
    """
    service = ReminderService(db)

    try:
        items, total = service.get_reminders(status=status_filter, page=page, page_size=page_size)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

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
    Each reminder_type requires the matching foreign key:
      tax_deadline_approaching → tax_deadline_id
      binder_idle              → binder_id
      unpaid_charge            → charge_id
      custom                   → message required, no foreign key needed
    """
    service = ReminderService(db)

    try:
        if request.reminder_type == "tax_deadline_approaching":
            if not request.tax_deadline_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="tax_deadline_id required for tax_deadline_approaching reminders",
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
                    detail="binder_id required for binder_idle reminders",
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
                    detail="charge_id required for unpaid_charge reminders",
                )
            reminder = service.create_unpaid_charge_reminder(
                client_id=request.client_id,
                charge_id=request.charge_id,
                days_unpaid=request.days_before,
                message=request.message,
            )

        elif request.reminder_type == "custom":
            if not request.message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="message is required for custom reminders",
                )
            reminder = service.create_custom_reminder(
                client_id=request.client_id,
                target_date=request.target_date,
                days_before=request.days_before,
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
        reminder = service.mark_sent(reminder_id)
        return ReminderResponse.model_validate(reminder)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )