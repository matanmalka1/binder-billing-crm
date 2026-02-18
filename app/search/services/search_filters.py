from datetime import date

from app.binders.services.sla_service import SLAService


def matches_sla_state(binder, sla_state: str, reference_date: date) -> bool:
    if sla_state == "overdue":
        return SLAService.is_overdue(binder, reference_date)
    if sla_state == "approaching":
        return SLAService.is_approaching_sla(binder, reference_date)
    if sla_state == "on_track":
        return not SLAService.is_overdue(
            binder, reference_date
        ) and not SLAService.is_approaching_sla(binder, reference_date)
    return True


def matches_signal_type(current_signals: list[str], signal_types: list[str]) -> bool:
    if not signal_types:
        return True
    return any(signal in current_signals for signal in signal_types)
