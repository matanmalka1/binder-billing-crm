from app.timeline.labels import (
    DOCUMENT_TYPE_HE,
    REMINDER_TYPE_HE,
    SIGNATURE_REQUEST_TYPE_HE,
)


def client_created_event(client) -> dict:
    client_name = getattr(client, "full_name", None) or getattr(client, "official_name", "")
    return {
        "event_type": "client_created",
        "timestamp": client.created_at,
        "binder_id": None,
        "charge_id": None,
        "description": f"לקוח נוצר: {client_name}",
        "metadata": {"entity_type": client.entity_type.value},
        "available_actions": [],
    }


def client_info_updated_event(client) -> dict:
    return {
        "event_type": "client_info_updated",
        "timestamp": client.updated_at,
        "binder_id": None,
        "charge_id": None,
        "description": "פרטי לקוח עודכנו",
        "metadata": {},
        "available_actions": [],
    }


def tax_profile_updated_event(profile) -> dict:
    return {
        "event_type": "tax_profile_updated",
        "timestamp": profile.updated_at,
        "binder_id": None,
        "charge_id": None,
        "description": "פרופיל מס עודכן",
        "metadata": {"tax_profile_id": profile.id},
        "available_actions": [],
    }


def reminder_created_event(reminder) -> dict:
    type_he = REMINDER_TYPE_HE.get(reminder.reminder_type.value, reminder.reminder_type.value)
    return {
        "event_type": "reminder_created",
        "timestamp": reminder.created_at,
        "binder_id": reminder.binder_id,
        "charge_id": reminder.charge_id,
        "description": f"תזכורת נוצרה: {type_he}",
        "metadata": {
            "reminder_type": reminder.reminder_type.value,
            "send_on": reminder.send_on.isoformat(),
        },
        "available_actions": [],
    }


def document_uploaded_event(document) -> dict:
    doc_type = (
        document.document_type.value
        if hasattr(document.document_type, "value")
        else document.document_type
    )
    type_he = DOCUMENT_TYPE_HE.get(doc_type, doc_type)
    return {
        "event_type": "document_uploaded",
        "timestamp": document.uploaded_at,
        "binder_id": None,
        "charge_id": None,
        "description": f"מסמך הועלה: {type_he}",
        "metadata": {"document_type": doc_type},
        "available_actions": [],
    }


def signature_request_created_event(sig_request) -> dict:
    type_he = SIGNATURE_REQUEST_TYPE_HE.get(
        sig_request.request_type.value, sig_request.request_type.value
    )
    return {
        "event_type": "signature_request_created",
        "timestamp": sig_request.created_at,
        "binder_id": None,
        "charge_id": None,
        "description": f"בקשת חתימה נוצרה: {type_he}",
        "metadata": {
            "signature_request_id": sig_request.id,
            "status": sig_request.status.value,
        },
        "available_actions": [],
    }
