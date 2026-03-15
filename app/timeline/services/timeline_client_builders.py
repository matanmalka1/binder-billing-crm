from datetime import datetime


DOCUMENT_TYPE_HE = {
    "id_copy": "צילום ת.ז.",
    "power_of_attorney": "ייפוי כוח",
    "engagement_agreement": "הסכם התקשרות",
}

REMINDER_TYPE_HE = {
    "tax_deadline_approaching": "מועד מס מתקרב",
    "binder_idle": "תיק לא פעיל",
    "unpaid_charge": "חיוב שלא שולם",
    "custom": "תזכורת מותאמת",
}

SIGNATURE_REQUEST_TYPE_HE = {
    "engagement_agreement": "הסכם התקשרות",
    "annual_report_approval": "אישור דוח שנתי",
    "power_of_attorney": "ייפוי כוח",
    "vat_return_approval": 'אישור דוח מע"מ',
    "custom": "חתימה",
}


def client_created_event(client) -> dict:
    return {
        "event_type": "client_created",
        "timestamp": datetime.combine(client.opened_at, datetime.min.time()),
        "binder_id": None,
        "charge_id": None,
        "description": f"לקוח נוצר: {client.full_name}",
        "metadata": {"client_type": client.client_type.value},
        "actions": [],
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
        "actions": [],
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
        "actions": [],
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
        "actions": [],
        "available_actions": [],
    }


def document_uploaded_event(document) -> dict:
    type_he = DOCUMENT_TYPE_HE.get(document.document_type, document.document_type)
    return {
        "event_type": "document_uploaded",
        "timestamp": document.uploaded_at,
        "binder_id": None,
        "charge_id": None,
        "description": f"מסמך הועלה: {type_he}",
        "metadata": {"document_type": document.document_type},
        "actions": [],
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
        "actions": [],
        "available_actions": [],
    }
