from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.reminders.api.deps import advisor_or_secretary
from app.reminders.schemas.reminders import ReminderCreateRequest, ReminderResponse
from app.reminders.services import ReminderService

create_router = APIRouter()


@create_router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(request: ReminderCreateRequest, deps = Depends(advisor_or_secretary)):
    db, _user = deps
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
