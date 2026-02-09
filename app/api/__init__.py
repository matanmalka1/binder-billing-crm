from app.api import auth, binders, binders_history, binders_operations, clients
from app.api import charge, clients_binders, dashboard, dashboard_overview, health, permanent_documents

__all__ = [
    "auth",
    "clients",
    "binders",
    "dashboard",
    "binders_operations",
    "clients_binders",
    "dashboard_overview",
    "binders_history",
    "charge",
    "permanent_documents",
    "health",
]