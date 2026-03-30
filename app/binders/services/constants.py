from enum import Enum as PyEnum


class WorkState(str, PyEnum):
    """Derived operational work state (NOT persisted)."""

    WAITING_FOR_WORK = "waiting_for_work"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class SignalType(str, PyEnum):
    """Operational signal types (internal, non-blocking)."""

    MISSING_DOCUMENTS = "missing_permanent_documents"
    READY_FOR_PICKUP = "ready_for_pickup"
    UNPAID_CHARGES = "unpaid_charges"
    IDLE_BINDER = "idle_binder"


IDLE_THRESHOLD_DAYS = 14
