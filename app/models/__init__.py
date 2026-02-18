"""Compatibility re-exports for legacy app.models imports.
Prefer importing from feature packages directly in new code.
"""
from app.users.models.user import User, UserRole
from app.users.models.user_audit_log import AuditAction, AuditStatus, UserAuditLog
from app.clients.models.client import Client, ClientStatus, ClientType
from app.clients.models.client_tax_profile import ClientTaxProfile, VatType
from app.binders.models.binder import Binder, BinderStatus
from app.binders.models.binder_status_log import BinderStatusLog
from app.charge.models.charge import Charge, ChargeStatus
from app.invoice.models.invoice import Invoice
from app.notification.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)
from app.reminders.models.reminder import Reminder, ReminderType, ReminderStatus
from app.tax_deadline.models.tax_deadline import TaxDeadline, DeadlineType, UrgencyLevel
from app.permanent_documents.models.permanent_document import PermanentDocument, DocumentType
from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
from app.annual_reports.models.annual_report_model import AnnualReport
from app.annual_reports.models.annual_report_detail import AnnualReportDetail
from app.annual_reports.models.annual_report_enums import ReportStage, AnnualReportStatus, AnnualReportSchedule

__all__ = [
    'User', 'UserRole', 'AuditAction', 'AuditStatus', 'UserAuditLog',
    'Client', 'ClientStatus', 'ClientType', 'ClientTaxProfile', 'VatType',
    'Binder', 'BinderStatus', 'BinderStatusLog',
    'Charge', 'ChargeStatus', 'Invoice',
    'Notification', 'NotificationChannel', 'NotificationStatus', 'NotificationTrigger',
    'Reminder', 'ReminderType', 'ReminderStatus',
    'TaxDeadline', 'DeadlineType', 'UrgencyLevel',
    'PermanentDocument', 'DocumentType',
    'AuthorityContact', 'ContactType',
    'AnnualReport', 'AnnualReportDetail', 'ReportStage', 'AnnualReportStatus', 'AnnualReportSchedule',
]
