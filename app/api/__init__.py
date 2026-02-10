from app.api import auth, binders, binders_history, binders_operations, clients
from app.api import charge, clients_binders, dashboard, dashboard_overview, health, permanent_documents
from app.api import dashboard_extended, search, timeline
__all__ = [
    "auth",
    "clients",
    "binders",
    "dashboard",
    "dashboard_extended",
    "binders_operations",
    "clients_binders",
    "dashboard_overview",
    "binders_history",
    "charge",
    "permanent_documents",
    "health",
    "search",
    "timeline",
]
