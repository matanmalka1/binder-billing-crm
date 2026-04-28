FALLBACK_CLIENT_NAME = "לקוח"
BINDER_RECEIVED_SUBJECT = "התיק שלך התקבל במשרד"
BINDER_READY_FOR_PICKUP_SUBJECT = "הקלסר שלך מוכן לאיסוף"
MANUAL_PAYMENT_REMINDER_SUBJECT = "תזכורת תשלום"
DEFAULT_NOTIFICATION_SUBJECT = "הודעה ממערכת ניהול הקלסרים"
CLIENT_REMINDER_SUBJECT = "תזכורת מועד מס"
BULK_NOTIFY_LIMIT_EXCEEDED = "לא ניתן לשלוח התראות ליותר מ-{limit} עסקים בבת אחת"

BINDER_RECEIVED_NOTIFICATION_CONTENT = (
    "שלום {name},\n\n"
    "קלסר מספר {binder_number} התקבל במשרד בתאריך {period_start}.\n\n"
    "בברכה"
)

BINDER_READY_FOR_PICKUP_NOTIFICATION_CONTENT = (
    "שלום {name},\n\n"
    "תיק מספר {binder_number} מוכן לאיסוף מהמשרד.\n\n"
    "בברכה"
)

PICKUP_REMINDER_SUBJECT = "תזכורת לאיסוף תיק"
PICKUP_REMINDER_NOTIFICATION_CONTENT = (
    "שלום {name},\n\n"
    "תזכורת: קלסר מספר {binder_number} עדיין מחכה לאיסוף מהמשרד.\n\n"
    "בברכה"
)

ANNUAL_REPORT_CLIENT_REMINDER_SUBJECT = "תזכורת לאישור דוח שנתי"
ANNUAL_REPORT_CLIENT_REMINDER_NOTIFICATION_CONTENT = (
    "שלום {name},\n\n"
    "הדוח השנתי לשנת {tax_year} מחכה לאישורך.\n\n"
    "בברכה"
)
