# Tax Rules Config — Israel 2026

מטרת החבילה: מקור אמת אחד לחובות דיווח/תשלום מס עבור מערכת CRM למשרד רו״ח/יועץ מס.

## החלטות מוצר/ארכיטקטורה

1. `Client/LegalEntity` הוא יחידת המס. לא `Business`.
2. מע״מ, מקדמות, ביטוח לאומי ודוח שנתי הם חוקים נפרדים. לא גוזרים אחד מהשני בלי שדה מפורש.
3. עוסק פטור לא מקבל דוחות מע״מ תקופתיים. כן יכול לקבל מקדמות מס הכנסה וביטוח לאומי.
4. חברה בע״מ אינה משלמת ביטוח לאומי כעצמאי. אם יש עובדים — יש חובת מעסיק.
5. PCN874 הוא לא חובה אוטומטית לכל עוסק מורשה. חובה לשמור `requires_pcn874`.
6. 6111 אינו דוח שנתי עצמאי. הוא נספח לדוח שנתי.
7. מועדים בפועל מגיעים מלוח רשמי שנתי, לא מחישוב נאיבי של 15/16/23.
8. דחיות חריגות נשמרות כ־override לפי שנה/תקופה, לא משנות את חוק הבסיס.

## קבצים

- `types.py` — enums/dataclasses בלבד.
- `sources.py` — מקורות רשמיים + תאריך בדיקה.
- `calendar_2026.py` — לוח מועדים רשמי/אפקטיבי לתקופות 2026.
- `vat.py` — מע״מ: עוסק פטור, עוסק מורשה, חברה, PCN874.
- `income_tax.py` — מקדמות מס הכנסה ודוחות שנתיים.
- `national_insurance.py` — ביטוח לאומי עצמאי/מעסיק + שיעורי 2026.
- `policy.py` — resolver שמחזיר חובות לפי פרופיל לקוח.
- `tests/` — בדיקות שלא נוצרות חובות שגויות.

## שדות מומלצים ב־DB

על `legal_entities` / `client_records` לשמור לפחות:

- `entity_type`
- `vat_reporting_frequency`
- `income_tax_advance_frequency`
- `income_tax_advance_rate`
- `requires_pcn874`
- `requires_form_6111`
- `btl_status`
- `btl_advance_amount`
- `has_employees`
- `tax_office_id`
- `vat_file_number`
- `income_tax_file_number`
- `btl_file_number`
- `representative_extension_group_id` — אם המשרד עובד עם אורכות מייצגים.

## אזהרה חשובה

זה config תפעולי. לפני production חובה לבצע reconciliation מול לוחות רשמיים שנתיים של רשות המסים/ביטוח לאומי, במיוחד עבור חודשים שהושפעו מדחיות חריגות.
