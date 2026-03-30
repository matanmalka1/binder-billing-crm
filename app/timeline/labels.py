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
    "vat_filing": "מועד דוח מע״מ",
    "advance_payment_due": "תשלום מקדמה",
    "annual_report_deadline": "מועד הגשת דוח שנתי",
    "document_missing": "מסמך חסר",
}

SIGNATURE_REQUEST_TYPE_HE = {
    "engagement_agreement": "הסכם התקשרות",
    "annual_report_approval": "אישור דוח שנתי",
    "power_of_attorney": "ייפוי כוח",
    "vat_return_approval": 'אישור דוח מע"מ',
    "custom": "חתימה",
}

DEADLINE_TYPE_HE = {
    "vat": "מע״מ",
    "advance_payment": "מקדמה",
    "national_insurance": "ביטוח לאומי",
    "annual_report": "דוח שנתי",
    "other": "אחר",
}

ANNUAL_REPORT_STATUS_HE = {
    "not_started": "טרם התחיל",
    "collecting_docs": "איסוף מסמכים",
    "docs_complete": "מסמכים התקבלו",
    "in_preparation": "בהכנה",
    "pending_client": "ממתין לאישור לקוח",
    "submitted": "הוגש",
    "accepted": "התקבל",
    "assessment_issued": "שומה הוצאה",
    "objection_filed": "השגה הוגשה",
    "closed": "סגור",
}

CHARGE_TYPE_HE = {
    "monthly_retainer": "ריטיינר חודשי",
    "annual_report_fee": "שכר טרחה לדוח שנתי",
    "vat_filing_fee": "שכר טרחה לדוח מע״מ",
    "representation_fee": "שכר טרחה לייצוג",
    "consultation_fee": "שכר טרחה לייעוץ",
    "other": "אחר",
}

# "none" is a legacy sentinel value that may appear in old status_log rows
# before the enum was introduced — kept for backward compatibility.
BINDER_STATUS_HE = {
    "none": "חדש",
    "in_office": "במשרד",
    "ready_for_pickup": "מוכן לאיסוף",
    "returned": "הוחזר",
}

NOTIFICATION_TRIGGER_HE = {
    "binder_received": "קלסר התקבל",
    "binder_ready_for_pickup": "קלסר מוכן לאיסוף",
    "manual_payment_reminder": "תזכורת תשלום ידנית",
}
