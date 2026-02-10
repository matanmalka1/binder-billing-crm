"""
Service layer package.

Avoid eager imports to prevent circular import issues between services and repositories.
"""

from typing import Any

__all__ = [
    "AuthService",
    "ClientService",
    "BinderService",
    "DashboardService",
    "SLAService",
    "BinderOperationsService",
    "DashboardOverviewService",
    "BinderHistoryService",
    "BillingService",
    "InvoiceService",
    "NotificationService",
    "PermanentDocumentService",
    "DailySLAJobService",
    "WorkStateService",
    "SignalsService",
    "DashboardExtendedService",
    "TimelineService",
    "SearchService",
]


def __getattr__(name: str) -> Any:
    if name == "AuthService":
        from app.services.auth_service import AuthService

        return AuthService
    if name == "ClientService":
        from app.services.client_service import ClientService

        return ClientService
    if name == "BinderService":
        from app.services.binder_service import BinderService

        return BinderService
    if name == "DashboardService":
        from app.services.dashboard_service import DashboardService

        return DashboardService
    if name == "SLAService":
        from app.services.sla_service import SLAService

        return SLAService
    if name == "BinderOperationsService":
        from app.services.binder_operations_service import BinderOperationsService

        return BinderOperationsService
    if name == "DashboardOverviewService":
        from app.services.dashboard_overview_service import DashboardOverviewService

        return DashboardOverviewService
    if name == "BinderHistoryService":
        from app.services.binder_history_service import BinderHistoryService

        return BinderHistoryService
    if name == "BillingService":
        from app.services.billing_service import BillingService

        return BillingService
    if name == "InvoiceService":
        from app.services.invoice_service import InvoiceService

        return InvoiceService
    if name == "NotificationService":
        from app.services.notification_service import NotificationService

        return NotificationService
    if name == "PermanentDocumentService":
        from app.services.permanent_document_service import PermanentDocumentService

        return PermanentDocumentService
    if name == "DailySLAJobService":
        from app.services.daily_sla_job_service import DailySLAJobService

        return DailySLAJobService
    if name == "WorkStateService":
        from app.services.work_state_service import WorkStateService

        return WorkStateService
    if name == "SignalsService":
        from app.services.signals_service import SignalsService

        return SignalsService
    if name == "DashboardExtendedService":
        from app.services.dashboard_extended_service import DashboardExtendedService

        return DashboardExtendedService
    if name == "TimelineService":
        from app.services.timeline_service import TimelineService

        return TimelineService
    if name == "SearchService":
        from app.services.search_service import SearchService

        return SearchService

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
