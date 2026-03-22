"""Centralised Hebrew display labels for annual report domain."""

SCHEDULE_LABELS: dict[str, str] = {
    "schedule_b": "נספח ב — שכירות",
    "schedule_bet": "נספח בית — רווחי הון",
    "schedule_gimmel": 'נספח ג — הכנסות מחו"ל',
    "schedule_dalet": "נספח ד — פחת",
    "schedule_heh": "נספח ה — שכר דירה פטור",
}

INCOME_LABELS: dict[str, str] = {
    "business": "הכנסות עסק",
    "salary": "שכר עבודה",
    "interest": "ריבית",
    "dividends": "דיבידנד",
    "capital_gains": "רווח הון",
    "rental": "שכירות",
    "foreign": 'הכנסה מחו"ל',
    "pension": "קצבה",
    "other": "אחר",
}

EXPENSE_LABELS: dict[str, str] = {
    "office_rent": 'שכ"ד משרד',
    "professional_services": "שירותים מקצועיים",
    "salaries": "שכר עובדים",
    "depreciation": "פחת",
    "vehicle": "רכב",
    "marketing": "שיווק",
    "insurance": "ביטוח",
    "communication": "תקשורת",
    "travel": "נסיעות",
    "training": "הכשרה",
    "bank_fees": "עמלות בנק",
    "other": "אחר",
}

CLIENT_TYPE_LABELS: dict[str, str] = {
    "individual": "יחיד (1301)",
    "self_employed": "עצמאי (1215)",
    "corporation": "חברה (6111)",
    "partnership": "שותפות (1215)",
}

STATUS_LABELS: dict[str, str] = {
    "not_started": "טרם החל",
    "collecting_docs": "איסוף מסמכים",
    "docs_complete": "מסמכים הושלמו",
    "in_preparation": "בהכנה",
    "pending_client": "ממתין ללקוח",
    "submitted": "הוגש",
    "accepted": "התקבל",
    "assessment_issued": "שומה הוצאה",
    "objection_filed": "הגשת השגה",
    "closed": "סגור",
    "amended": "מתוקן",
}

__all__ = [
    "SCHEDULE_LABELS",
    "INCOME_LABELS",
    "EXPENSE_LABELS",
    "CLIENT_TYPE_LABELS",
    "STATUS_LABELS",
]
