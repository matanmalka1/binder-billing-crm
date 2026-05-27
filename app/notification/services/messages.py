from __future__ import annotations

from app.notification.models.notification import NotificationTrigger

FALLBACK_CLIENT_NAME = "לקוח"
BINDER_RECEIVED_SUBJECT = "התיק שלך התקבל במשרד"
BINDER_READY_FOR_HANDOVER_SUBJECT = "הקלסר שלך מוכן למסירה"
MANUAL_PAYMENT_REMINDER_SUBJECT = "תזכורת תשלום"
DEFAULT_NOTIFICATION_SUBJECT = "הודעה ממערכת ניהול הקלסרים"
CLIENT_REMINDER_SUBJECT = "תזכורת מועד מס"
BULK_NOTIFY_LIMIT_EXCEEDED = "לא ניתן לשלוח התראות ליותר מ-{limit} עסקים בבת אחת"

BINDER_RECEIVED_NOTIFICATION_CONTENT = (
    "שלום {name},\n\nקלסר מספר {binder_number} התקבל במשרד בתאריך {period_start}.\n\nבברכה"
)

BINDER_READY_FOR_HANDOVER_NOTIFICATION_CONTENT = (
    "שלום {name},\n\nתיק מספר {binder_number} מוכן למסירה מהמשרד.\n\nבברכה"
)

HANDOVER_REMINDER_SUBJECT = "תזכורת למסירת תיק"
HANDOVER_REMINDER_NOTIFICATION_CONTENT = (
    "שלום {name},\n\nתזכורת: קלסר מספר {binder_number} עדיין מחכה למסירה מהמשרד.\n\nבברכה"
)

ANNUAL_REPORT_CLIENT_REMINDER_SUBJECT = "תזכורת לאישור דוח שנתי"
ANNUAL_REPORT_CLIENT_REMINDER_NOTIFICATION_CONTENT = (
    "שלום {name},\n\nהדוח השנתי לשנת {tax_year} מחכה לאישורך.\n\nבברכה"
)

MANUAL_NOTIFICATION_CONTENT = "שלום {name},\n\n{message}\n\nבברכה"

CONTENT_TEMPLATES: dict[str, str] = {
    "binder_received": BINDER_RECEIVED_NOTIFICATION_CONTENT,
    "binder_ready_for_handover": BINDER_READY_FOR_HANDOVER_NOTIFICATION_CONTENT,
    "handover_reminder": HANDOVER_REMINDER_NOTIFICATION_CONTENT,
    "annual_report_client_reminder": ANNUAL_REPORT_CLIENT_REMINDER_NOTIFICATION_CONTENT,
    "manual_payment_reminder": MANUAL_NOTIFICATION_CONTENT,
}

SUBJECTS: dict[NotificationTrigger, str] = {
    NotificationTrigger.BINDER_RECEIVED: BINDER_RECEIVED_SUBJECT,
    NotificationTrigger.BINDER_READY_FOR_HANDOVER: BINDER_READY_FOR_HANDOVER_SUBJECT,
    NotificationTrigger.HANDOVER_REMINDER: HANDOVER_REMINDER_SUBJECT,
    NotificationTrigger.ANNUAL_REPORT_CLIENT_REMINDER: ANNUAL_REPORT_CLIENT_REMINDER_SUBJECT,
    NotificationTrigger.MANUAL_PAYMENT_REMINDER: MANUAL_PAYMENT_REMINDER_SUBJECT,
}
