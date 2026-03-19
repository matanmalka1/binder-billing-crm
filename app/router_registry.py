from fastapi import FastAPI

from app.advance_payments.api import advance_payments, advance_payments_overview, advance_payment_generate  # noqa: F401
from app.annual_reports.api import (
    annual_report_annex,
    annual_report_business,
    annual_report_create_read,
    annual_report_detail,
    annual_report_financials,
    annual_report_schedule,
    annual_report_season,
    annual_report_kanban,
    annual_report_status,
    routes_export as annual_report_export,
)
from app.binders.api import binders, binders_history, binders_operations
from app.clients.api import clients, clients_excel
from app.businesses.api import business_binders_router, business_status_card_router, business_tax_profile_router
from app.dashboard.api import dashboard, dashboard_extended, dashboard_overview, dashboard_tax
from app.users.api import users, users_audit
from app.signature_requests.api import routers as signature_requests_routers
from app.authority_contact.api import authority_contact
from app.charge.api import charge
from app.correspondence.api import correspondence
from app.health.api import health
from app.permanent_documents.api import permanent_documents, permanent_document_actions
from app.notification.api import notifications as notification_center
from app.notification.api.notifications import advisor_router as notification_advisor_router
from app.reminders.api import routers as reminders
from app.reports.api import reports
from app.search.api import search
from app.tax_deadline.api import tax_deadline, deadline_generate
from app.timeline.api import timeline
from app.users.api import auth
from app.vat_reports.api.routers import router as vat_reports_router


def register_routers(app: FastAPI) -> None:
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(annual_report_annex.router, prefix="/api/v1")
    app.include_router(annual_report_detail.router, prefix="/api/v1")
    app.include_router(annual_report_financials.router, prefix="/api/v1")
    app.include_router(annual_report_create_read.router, prefix="/api/v1")
    app.include_router(annual_report_schedule.router, prefix="/api/v1")
    app.include_router(annual_report_kanban.router, prefix="/api/v1")
    app.include_router(annual_report_status.router, prefix="/api/v1")
    app.include_router(annual_report_business.clients_router, prefix="/api/v1")
    app.include_router(annual_report_season.season_router, prefix="/api/v1")
    app.include_router(annual_report_export.router, prefix="/api/v1")
    app.include_router(tax_deadline.router, prefix="/api/v1")
    app.include_router(deadline_generate.router, prefix="/api/v1")
    app.include_router(authority_contact.router, prefix="/api/v1")
    app.include_router(dashboard_tax.router, prefix="/api/v1")
    # Place Excel routes before parameterized /clients/{id} to avoid path conflicts
    app.include_router(clients_excel.router, prefix="/api/v1")
    app.include_router(clients.router, prefix="/api/v1")
    app.include_router(business_status_card_router.router, prefix="/api/v1")
    app.include_router(business_binders_router.router, prefix="/api/v1")
    app.include_router(business_tax_profile_router.router, prefix="/api/v1")
    app.include_router(binders_operations.router, prefix="/api/v1")
    app.include_router(binders.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")
    app.include_router(dashboard_overview.router, prefix="/api/v1")
    app.include_router(binders_history.router, prefix="/api/v1")
    app.include_router(charge.router, prefix="/api/v1")
    app.include_router(permanent_documents.router, prefix="/api/v1")
    app.include_router(permanent_document_actions.router, prefix="/api/v1")
    app.include_router(dashboard_extended.router, prefix="/api/v1")
    app.include_router(reports.router, prefix="/api/v1")
    app.include_router(timeline.router, prefix="/api/v1")
    app.include_router(search.router, prefix="/api/v1")
    app.include_router(users_audit.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(reminders.router, prefix="/api/v1")
    app.include_router(notification_center.router, prefix="/api/v1")
    app.include_router(notification_advisor_router, prefix="/api/v1")
    app.include_router(correspondence.router, prefix="/api/v1")
    app.include_router(advance_payments.router, prefix="/api/v1")
    app.include_router(advance_payment_generate.router, prefix="/api/v1")
    app.include_router(signature_requests_routers.router, prefix="/api/v1")
    app.include_router(signature_requests_routers.signer_router)
    app.include_router(vat_reports_router, prefix="/api/v1")