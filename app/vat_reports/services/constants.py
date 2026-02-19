"""VAT workflow constants — status transitions and validation rules."""

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
ACTION_OVERRIDE = "vat_override"
ACTION_FILED = "filed"

__all__ = [
    "ACTION_FILED",
    "ACTION_INVOICE_ADDED",
    "ACTION_INVOICE_DELETED",
    "ACTION_MATERIAL_RECEIVED",
    "ACTION_OVERRIDE",
    "ACTION_STATUS_CHANGED",
    "VALID_TRANSITIONS",
]
