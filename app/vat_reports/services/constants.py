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
    "other": "אחר",
}

# Deduction rates per expense category (0.0 = prohibited, 1.0 = fully deductible)
# Source: Israeli VAT Law §41
CATEGORY_DEDUCTION_RATES: dict[str, Decimal] = {
    "office": Decimal("1.0000"),
    "travel": Decimal("0.6667"),          # 2/3 deductible
    "professional_services": Decimal("1.0000"),
    "equipment": Decimal("1.0000"),
    "rent": Decimal("1.0000"),
    "salary": Decimal("0.0000"),          # payroll is not a VAT input
    "marketing": Decimal("1.0000"),
    "vehicle": Decimal("0.0000"),         # private vehicle — prohibited
    "entertainment": Decimal("0.0000"),   # hospitality — prohibited
    "gifts": Decimal("0.0000"),           # gifts — prohibited
    "other": Decimal("0.0000"),           # unknown — conservative default
}

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
    "ACTION_OVERRIDE",
    "ACTION_STATUS_CHANGED",
    "CATEGORY_DEDUCTION_RATES",
    "CATEGORY_LABELS_SERVER",
    "EXCEPTIONAL_INVOICE_THRESHOLD",
    "OSEK_PATUR_CEILING_ILS",
    "VALID_TRANSITIONS",
]
