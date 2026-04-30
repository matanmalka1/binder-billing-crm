def build_attention_empty_checks() -> list[dict[str, str]]:
    return [
        {"key": "overdue_reminders", "label": "אין תזכורות באיחור"},
        {"key": "pending_vat", "label": "אין דוחות מע״מ ממתינים"},
        {"key": "ready_binders", "label": "אין קלסרים שממתינים לאיסוף"},
        {"key": "open_charges", "label": "אין חיובים פתוחים"},
    ]
