from typing import Optional

from app.binders.models.binder import Binder, BinderStatus


def validate_ready_transition(binder: Binder) -> None:
    """Validate binder can be marked ready for pickup."""
    if binder.status != BinderStatus.IN_OFFICE:
       raise ValueError(f"לא ניתן לסמן תיק כמוכן מסטטוס {binder.status}")


def validate_return_transition(
    binder: Binder, pickup_person_name: Optional[str]
) -> None:
    """Validate binder can be returned."""
    if not pickup_person_name or not pickup_person_name.strip():
        raise ValueError("שם האיש המאסף הוא שדה חובה")
    
    if binder.status != BinderStatus.READY_FOR_PICKUP:
        raise ValueError(f"לא ניתן להחזיר תיק מסטטוס {binder.status}")