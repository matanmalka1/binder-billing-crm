def build_attention_empty_checks(
    *,
    open_reminders: int = 0,
    pending_vat: int = 0,
    open_charges: int = 0,
) -> list[dict[str, str]]:
    """Return empty-state checks for the attention board, based on actual counts.

    Only includes a check when the corresponding category is truly empty (count == 0),
    so the frontend displays accurate "all clear" messaging.
    """
    checks = []
    if open_reminders == 0:
        checks.append({"key": "overdue_reminders", "label": "אין תזכורות ידניות פתוחות"})
    if pending_vat == 0:
        checks.append({"key": "pending_vat", "label": "אין דוחות מע״מ ממתינים"})
    if open_charges == 0:
        checks.append({"key": "open_charges", "label": "אין חיובים פתוחים"})
    return checks
