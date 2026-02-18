"""Compatibility re-exports for legacy app.repositories imports.
Prefer importing repository classes from their feature packages."""
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository
from app.clients.repositories.client_repository import ClientRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.invoice.repositories.invoice_repository import InvoiceRepository
from app.notification.repositories.notification_repository import NotificationRepository
from app.users.repositories.user_repository import UserRepository
from app.users.repositories.user_audit_log_repository import UserAuditLogRepository
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository
from app.dashboard.repositories.dashboard_overview_repository import DashboardOverviewRepository
from app.timeline.repositories.timeline_repository import TimelineRepository
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.authority_contact.repositories.authority_contact_repository import AuthorityContactRepository

__all__ = [
    'BinderRepository', 'BinderStatusLogRepository', 'ClientRepository', 'ChargeRepository',
    'InvoiceRepository', 'NotificationRepository', 'UserRepository', 'UserAuditLogRepository',
    'PermanentDocumentRepository', 'DashboardOverviewRepository', 'TimelineRepository',
    'TaxDeadlineRepository', 'AuthorityContactRepository',
]
