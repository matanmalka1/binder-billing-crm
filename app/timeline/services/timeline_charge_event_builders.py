from app.actions.action_contracts import get_charge_actions


CHARGE_TYPE_HE = {
    "monthly_retainer": "ריטיינר חודשי",
    "annual_report_fee": "שכר טרחה לדוח שנתי",
    "vat_filing_fee": "שכר טרחה לדוח מע״מ",
    "representation_fee": "שכר טרחה לייצוג",
    "consultation_fee": "שכר טרחה לייעוץ",
    "other": "אחר",
}


def _attach_actions(event: dict, actions: list) -> dict:
    """
    Attach actions to the event payload.

    `available_actions` is kept for backward compatibility with older clients
    that read that key; both keys intentionally reference the same list.
    """
    event["actions"] = actions
    event["available_actions"] = actions
    return event


def charge_created_event(charge) -> dict:
    actions = get_charge_actions(charge)
    return _attach_actions(
        {
            "event_type": "charge_created",
            "timestamp": charge.created_at,
            "binder_id": None,
            "charge_id": charge.id,
            "description": f"חיוב חדש: {CHARGE_TYPE_HE.get(charge.charge_type.value, 'סוג לא ידוע')}",
            "metadata": {
                "amount": float(charge.amount),
                "status": charge.status.value,
            },
        },
        actions,
    )


def charge_issued_event(charge) -> dict:
    actions = get_charge_actions(charge)
    return _attach_actions(
        {
            "event_type": "charge_issued",
            "timestamp": charge.issued_at,
            "binder_id": None,
            "charge_id": charge.id,
            "description": f"חיוב הונפק: {CHARGE_TYPE_HE.get(charge.charge_type.value, 'סוג לא ידוע')}",
            "metadata": {"amount": float(charge.amount)},
        },
        actions,
    )


def charge_paid_event(charge) -> dict:
    return _attach_actions(
        {
            "event_type": "charge_paid",
            "timestamp": charge.paid_at,
            "binder_id": None,
            "charge_id": charge.id,
            "description": f"חיוב שולם: {CHARGE_TYPE_HE.get(charge.charge_type.value, 'סוג לא ידוע')}",
            "metadata": {"amount": float(charge.amount)},
        },
        [],
    )


def invoice_attached_event(charge, invoice) -> dict:
    return _attach_actions(
        {
            "event_type": "invoice_attached",
            "timestamp": invoice.created_at,
            "binder_id": None,
            "charge_id": charge.id,
            "description": f"חשבונית צורפה: {invoice.external_invoice_id}",
            "metadata": {
                "provider": invoice.provider,
                "external_invoice_id": invoice.external_invoice_id,
            },
        },
        [],
    )
