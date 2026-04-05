"""VAT workflow constants — status transitions and validation rules."""

from decimal import Decimal

from app.vat_reports.models.vat_enums import VatWorkItemStatus

# Valid status transitions: from → set of allowed next statuses
VALID_TRANSITIONS: dict[VatWorkItemStatus, set[VatWorkItemStatus]] = {
    VatWorkItemStatus.PENDING_MATERIALS: {
        VatWorkItemStatus.MATERIAL_RECEIVED,
    },
    VatWorkItemStatus.MATERIAL_RECEIVED: {
        VatWorkItemStatus.PENDING_MATERIALS,   # send back if incomplete
        VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS,
    },
    VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS: {
        VatWorkItemStatus.READY_FOR_REVIEW,
        VatWorkItemStatus.MATERIAL_RECEIVED,   # rollback
    },
    VatWorkItemStatus.READY_FOR_REVIEW: {
        VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS,  # advisor sends back for correction
        VatWorkItemStatus.FILED,
    },
    VatWorkItemStatus.FILED: set(),  # terminal — immutable
}

# Audit action labels
ACTION_WORK_ITEM_CREATED_PENDING = "work_item_created_pending"
ACTION_MATERIAL_RECEIVED = "material_received"
ACTION_STATUS_CHANGED = "status_changed"
ACTION_INVOICE_ADDED = "invoice_added"
ACTION_INVOICE_DELETED = "invoice_deleted"
ACTION_INVOICE_UPDATED = "invoice_updated"
ACTION_OVERRIDE = "vat_override"
ACTION_FILED = "filed"

CATEGORY_LABELS_SERVER: dict[str, str] = {
    "office": "משרד",
    "travel": "נסיעות",
    "professional_services": "שירותים מקצועיים",
    "equipment": "ציוד",
    "rent": "שכירות",
    "salary": "שכר עבודה",
    "marketing": "שיווק",
    "vehicle": "רכב פרטי",
    "entertainment": "אירוח וכיבוד",
    "gifts": "מתנות",
    "fuel": "דלק",
    "vehicle_maintenance": "תחזוקת רכב",
    "vehicle_leasing": "ליסינג רכב",
    "maintenance": "תחזוקה",
    "utilities": "חשמל ומים",
    "communication": "תקשורת",
    "postage_and_shipping": "משלוחים ודואר",
    "bank_fees": "עמלות בנק",
    "tolls_and_parking": "חניה וכבישי אגרה",
    "mixed_expense": "הוצאה מעורבת",
    "vehicle_insurance": "ביטוח רכב",
    "insurance": "ביטוח",
    "municipal_tax": "ארנונה",
}

# Deduction rates per expense category (0.0 = prohibited, 1.0 = fully deductible)
# Source: Israeli VAT Law §41
CATEGORY_DEDUCTION_RATES: dict[str, Decimal] = {
    # 100% קיזוז
    "office":                Decimal("1.0000"),
    "professional_services": Decimal("1.0000"),
    "equipment":             Decimal("1.0000"),
    "rent":                  Decimal("1.0000"),
    "marketing":             Decimal("1.0000"),
    "maintenance":           Decimal("1.0000"),
    "utilities":             Decimal("1.0000"),
    "postage_and_shipping":  Decimal("1.0000"),
    "bank_fees":             Decimal("1.0000"),

    # 2/3 קיזוז — הוצאות מעורבות
    "travel":                Decimal("0.6667"),
    "fuel":                  Decimal("0.6667"),
    "vehicle":               Decimal("0.6667"),
    "vehicle_maintenance":   Decimal("0.6667"),
    "vehicle_leasing":       Decimal("0.6667"),
    "tolls_and_parking":     Decimal("0.6667"),
    "communication":         Decimal("0.6667"),
    "mixed_expense":         Decimal("0.6667"),  # ברירת מחדל שמרנית

    # 0% — ללא מע"מ או ניכוי אסור
    "salary":                Decimal("0.0000"),  # שכר — לא תשומת מע"מ
    "entertainment":         Decimal("0.0000"),  # אירוח — אסור
    "gifts":                 Decimal("0.0000"),  # מתנות — אסור
    "vehicle_insurance":     Decimal("0.0000"),  # ביטוח — ללא מע"מ
    "insurance":             Decimal("0.0000"),  # ביטוח — ללא מע"מ
    "municipal_tax":         Decimal("0.0000"),  # ארנונה — ללא מע"מ
}

# VAT submission deadlines
# 15 = statutory deadline by law; 19 = digital filing extension granted by tax authority.
# Work items use the statutory deadline as the conservative target.
VAT_STATUTORY_DEADLINE_DAY = 15   # base legal deadline
VAT_ONLINE_EXTENDED_DEADLINE_DAY = 19  # extension for digital filing only

# OSEK PATUR annual turnover ceiling (updated annually per tax authority)
# 2026 value: 122,833 ₪  (2025: 120,000 ₪)
OSEK_PATUR_CEILING_ILS: Decimal = Decimal("122833")

# Exceptional invoice threshold — requires special reporting
EXCEPTIONAL_INVOICE_THRESHOLD: Decimal = Decimal("25000")

__all__ = [
    "ACTION_FILED",
    "ACTION_INVOICE_ADDED",
    "ACTION_INVOICE_DELETED",
    "ACTION_INVOICE_UPDATED",
    "ACTION_MATERIAL_RECEIVED",
    "ACTION_WORK_ITEM_CREATED_PENDING",
    "ACTION_OVERRIDE",
    "ACTION_STATUS_CHANGED",
    "CATEGORY_DEDUCTION_RATES",
    "CATEGORY_LABELS_SERVER",
    "EXCEPTIONAL_INVOICE_THRESHOLD",
    "OSEK_PATUR_CEILING_ILS",
    "VAT_ONLINE_EXTENDED_DEADLINE_DAY",
    "VAT_STATUTORY_DEADLINE_DAY",
    "VALID_TRANSITIONS",
]
