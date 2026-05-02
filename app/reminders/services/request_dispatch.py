from app.reminders.models.reminder import ReminderType
from app.reminders.schemas.reminders import ReminderCreateRequest


def create_from_request(service, request: ReminderCreateRequest, *, created_by: int):
    if request.reminder_type == ReminderType.BINDER_IDLE:
        return service.create_idle_binder_reminder(
            binder_id=request.binder_id,
            days_idle=request.days_before,
            message=request.message,
            created_by=created_by,
        )
    if request.reminder_type == ReminderType.DOCUMENT_MISSING:
        return service.create_document_missing_reminder(
            business_id=request.business_id,
            target_date=request.target_date,
            days_before=request.days_before,
            message=request.message,
            created_by=created_by,
        )
    return service.create_custom_reminder(
        client_record_id=request.client_record_id,
        business_id=request.business_id,
        target_date=request.target_date,
        days_before=request.days_before,
        message=request.message,
        created_by=created_by,
    )
