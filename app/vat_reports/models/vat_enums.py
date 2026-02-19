"""VAT Report enums."""

from enum import Enum as PyEnum


class VatWorkItemStatus(str, PyEnum):
    PENDING_MATERIALS = "pending_materials"
    MATERIAL_RECEIVED = "material_received"
    DATA_ENTRY_IN_PROGRESS = "data_entry_in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    FILED = "filed"


class FilingMethod(str, PyEnum):
    MANUAL = "manual"
    ONLINE = "online"


class InvoiceType(str, PyEnum):
    INCOME = "income"       # מכירות / עסקאות
    EXPENSE = "expense"     # תשומות


class ExpenseCategory(str, PyEnum):
    OFFICE = "office"
    TRAVEL = "travel"
    PROFESSIONAL_SERVICES = "professional_services"
    EQUIPMENT = "equipment"
    RENT = "rent"
    SALARY = "salary"
    MARKETING = "marketing"
    OTHER = "other"


__all__ = [
    "ExpenseCategory",
    "FilingMethod",
    "InvoiceType",
    "VatWorkItemStatus",
]
