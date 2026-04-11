from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.reminders.models.reminder import ReminderType
from app.reminders.schemas.reminders import ReminderCreateRequest, ReminderResponse
from app.reminders.services.reminder_service import ReminderService

create_router = APIRouter()


@create_router.post(
    "/",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def create_reminder(
    request: ReminderCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    service = ReminderService(db)

    if request.reminder_type == ReminderType.TAX_DEADLINE_APPROACHING:
        reminder = service.create_tax_deadline_reminder(
            client_id=request.client_id,
            tax_deadline_id=request.tax_deadline_id,
            target_date=request.target_date,
            days_before=request.days_before,
            message=request.message,
            created_by=user.id,
        )

    elif request.reminder_type == ReminderType.VAT_FILING:
        reminder = service.create_vat_filing_reminder(
            tax_deadline_id=request.tax_deadline_id,
            target_date=request.target_date,
            days_before=request.days_before,
            message=request.message,
            created_by=user.id,
        )

    elif request.reminder_type == ReminderType.BINDER_IDLE:
        reminder = service.create_idle_binder_reminder(
            binder_id=request.binder_id,
            days_idle=request.days_before,
            message=request.message,
            created_by=user.id,
        )

    elif request.reminder_type == ReminderType.UNPAID_CHARGE:
        reminder = service.create_unpaid_charge_reminder(
            business_id=request.business_id,
            charge_id=request.charge_id,
            days_unpaid=request.days_before,
            message=request.message,
            created_by=user.id,
        )

    elif request.reminder_type == ReminderType.ANNUAL_REPORT_DEADLINE:
        reminder = service.create_annual_report_deadline_reminder(
            annual_report_id=request.annual_report_id,
            target_date=request.target_date,
            days_before=request.days_before,
            message=request.message,
            created_by=user.id,
        )

    elif request.reminder_type == ReminderType.ADVANCE_PAYMENT_DUE:
        reminder = service.create_advance_payment_due_reminder(
            business_id=request.business_id,
            advance_payment_id=request.advance_payment_id,
            target_date=request.target_date,
            days_before=request.days_before,
            message=request.message,
            created_by=user.id,
        )

    elif request.reminder_type == ReminderType.DOCUMENT_MISSING:
        reminder = service.create_document_missing_reminder(
            business_id=request.business_id,
            target_date=request.target_date,
            days_before=request.days_before,
            message=request.message,
            created_by=user.id,
        )

    else:  # ReminderType.CUSTOM
        reminder = service.create_custom_reminder(
            business_id=request.business_id,
            target_date=request.target_date,
            days_before=request.days_before,
            message=request.message,
            created_by=user.id,
        )

    return ReminderResponse.model_validate(reminder)
