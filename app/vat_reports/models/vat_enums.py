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
    VEHICLE = "vehicle"           # רכב פרטי — ניכוי אסור
    ENTERTAINMENT = "entertainment"  # אירוח / כיבוד — ניכוי אסור
    GIFTS = "gifts"               # מתנות — ניכוי אסור
    OTHER = "other"


class VatRateType(str, PyEnum):
    """Tax rate category per invoice line (Israeli VAT law)."""
    STANDARD = "standard"    # חייב במע"מ 18%
    EXEMPT = "exempt"        # פטור ממע"מ (שכ"ד למגורים, פירות/ירקות, עמותות)
    ZERO_RATE = "zero_rate"  # אפס (ייצוא, אזורי עידוד)


class DocumentType(str, PyEnum):
    """Legal document type per Israeli VAT law."""
    TAX_INVOICE = "tax_invoice"              # חשבונית מס — מעניק זכות ניכוי תשומות
    TRANSACTION_INVOICE = "transaction_invoice"  # חשבונית עסקה — ללא זכות ניכוי
    RECEIPT = "receipt"                      # קבלה — ללא זכות ניכוי
    CONSOLIDATED = "consolidated"            # חשבונית מרוכזת
    SELF_INVOICE = "self_invoice"            # חשבונית עצמית (חיוב עצמי)


__all__ = [
    "DocumentType",
    "ExpenseCategory",
    "FilingMethod",
    "InvoiceType",
    "VatRateType",
    "VatWorkItemStatus",
]
