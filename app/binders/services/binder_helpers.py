from typing import Optional

from app.core.exceptions import AppError
from app.binders.models.binder import Binder, BinderStatus




def validate_ready_transition(binder: Binder) -> None:
    """Validate binder can be marked ready for pickup."""
    if binder.status != BinderStatus.IN_OFFICE:
        raise AppError(
            f"לא ניתן לסמן תיק כמוכן מסטטוס {binder.status}",
            "BINDER.INVALID_STATUS",
        )


def validate_return_transition(
    binder: Binder, pickup_person_name: Optional[str]
) -> None:
    """Validate binder can be returned."""
    if not pickup_person_name or not pickup_person_name.strip():
        raise AppError("שם האיש המאסף הוא שדה חובה", "BINDER.MISSING_PICKUP_PERSON")

    if binder.status != BinderStatus.READY_FOR_PICKUP:
        raise AppError(
            f"לא ניתן להחזיר תיק מסטטוס {binder.status}",
            "BINDER.INVALID_STATUS",
        )


def validate_revert_ready_transition(binder: Binder) -> None:
    """Validate binder can be reverted from READY_FOR_PICKUP back to IN_OFFICE."""
    if binder.status != BinderStatus.READY_FOR_PICKUP:
        raise AppError(
            f"לא ניתן לבטל סטטוס מוכן מסטטוס {binder.status}",
            "BINDER.INVALID_STATUS",
        )
