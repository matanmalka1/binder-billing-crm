from app.reminders.models.reminder import ReminderType
from app.reminders.schemas.reminders import ReminderCreateRequest


def create_from_request(service, request: ReminderCreateRequest, *, created_by: int):
    if request.reminder_type == ReminderType.TAX_DEADLINE_APPROACHING:
        return service.create_tax_deadline_reminder(
            client_record_id=request.client_record_id,
            tax_deadline_id=request.tax_deadline_id,
            target_date=request.target_date,
            days_before=request.days_before,
            message=request.message,
            created_by=created_by,
        )
    if request.reminder_type == ReminderType.VAT_FILING:
        return service.create_vat_filing_reminder(
            tax_deadline_id=request.tax_deadline_id,
            target_date=request.target_date,
            days_before=request.days_before,
            message=request.message,
            created_by=created_by,
        )
    if request.reminder_type == ReminderType.BINDER_IDLE:
        return service.create_idle_binder_reminder(
            binder_id=request.binder_id,
            days_idle=request.days_before,
            message=request.message,
            created_by=created_by,
        )
    if request.reminder_type == ReminderType.ANNUAL_REPORT_DEADLINE:
        return service.create_annual_report_deadline_reminder(
            annual_report_id=request.annual_report_id,
            target_date=request.target_date,
            days_before=request.days_before,
            message=request.message,
            created_by=created_by,
        )
    if request.reminder_type == ReminderType.UNPAID_CHARGE:
        return service.create_unpaid_charge_reminder(
            client_record_id=request.client_record_id,
            business_id=request.business_id,
            charge_id=request.charge_id,
            days_unpaid=request.days_before,
            message=request.message,
            created_by=created_by,
        )
    if request.reminder_type == ReminderType.ADVANCE_PAYMENT_DUE:
        return service.create_advance_payment_due_reminder(
            business_id=request.business_id,
            advance_payment_id=request.advance_payment_id,
            target_date=request.target_date,
            days_before=request.days_before,
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
