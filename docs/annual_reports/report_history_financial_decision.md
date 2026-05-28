## Scope
This file owns only:
- Reference context for a historical annual reports product decision discussion.
- Decision rationale that may need promotion to a formal ADR in a later phase.

This file must not contain:
- Current implemented annual reports behavior.
- New product requirements.
- Canonical architecture rules.

Source of truth: reference

# החלטה מוצרית: נתונים פיננסיים בהיסטוריית דוחות שנתיים

## רקע

במסך פירוט דוח שנתי קיימת טבלת "היסטוריית דוחות" (`ReportHistoryTable`) שמציגה דוחות שנתיים קודמים של אותו לקוח. הטבלה נטענת דרך קריאת list:

```text
GET /api/v1/clients/{client_record_id}/annual-reports
```

הקריאה הזו מחזירה היום מודל רשימה (`AnnualReportResponse`) ולא מודל פירוט מלא (`AnnualReportDetailResponse`).

בפרונט היה בעבר שימוש בטיפוס `AnnualReportFull` גם עבור רשימות, ולכן TypeScript איפשר שימוש בשדות detail-only שלא קיימים בפועל בתגובת הרשימה:

- `total_income`
- `total_expenses`
- `profit`
- `final_balance`
- `schedules`
- `status_history`
- שדות פירוט נוספים

הפער תוקן בצד frontend על ידי הפרדה בין:

- `AnnualReportSummary` — תואם לתגובות list.
- `AnnualReportFull` — תואם לתגובת פירוט דוח.

כתוצאה מכך, `ReportHistoryTable` לא יכולה להציג כרגע `total_income`, `total_expenses`, `profit`, `final_balance` מתוך מקור הנתונים הקיים, כי השדות אינם חוזרים מה־API.

## מה מוצג היום במקום אחר

הנתונים הפיננסיים כן מופיעים במקומות אחרים במסך הדוח:

- `ReportSummaryCards` מציג לדוח הנוכחי הכנסות, הוצאות, רווח נקי, מס שנתי ומקדמות.
- `AnnualPLSummary` מציג לדוח הנוכחי סיכום רווח והפסד מפורט.
- `MultiYearPLChart` מציג מגמה רב־שנתית גרפית, ומביא לכל דוח נתוני financial summary ו־tax calculation בקריאות ייעודיות.

אבל אין כרגע טבלה רב־שנתית מפורטת שמציגה לכל שנת מס:

- הכנסות
- הוצאות
- רווח
- יתרה לתשלום או החזר

## השאלה המוצרית

האם "היסטוריית דוחות" צריכה להיות טבלת סטטוס בסיסית בלבד, או טבלת השוואה פיננסית בין שנים?

זו לא רק החלטת API. זו החלטה על התפקיד של האזור במסך:

- אם מטרת האזור היא ניווט בין דוחות: מספיק להציג שנה, סטטוס, מועד הגשה, שומה, חבות והחזר.
- אם מטרת האזור היא סקירת לקוח רב־שנתית: כדאי להציג הכנסות, הוצאות, רווח ויתרה, כי אלה הנתונים שמאפשרים להבין שינוי עסקי בין שנים.

## ערך מוצרי של הצגת השדות

מוצרית, יש ערך גבוה להצגת השדות הפיננסיים בהיסטוריית הדוחות:

- מאפשר לזהות מגמות בין שנים בלי לפתוח כל דוח בנפרד.
- עוזר ליועץ לראות אם הכנסות או הוצאות השתנו בצורה חריגה.
- מאפשר להבין מהר האם הלקוח בדרך לתשלום או החזר.
- מחזק את מסך הדוח כמרכז עבודה שנתי ולא רק כטופס טכני.
- משלים את הגרף הרב־שנתי בנתונים מספריים מדויקים.

הגרף (`MultiYearPLChart`) טוב לזיהוי מגמה, אבל טבלה טובה יותר לבדיקה חשבונאית, השוואה מהירה ופעולת יועץ.

## סיכון בהחזרת כל מודל הפירוט ברשימות

לא מומלץ להפוך את כל list endpoints ל־`AnnualReportFull`.

סיבות:

- `schedules` ו־`status_history` הן ישויות detail-heavy ולא נדרשות לכל רשימה.
- זה יגדיל payload ויחבר מסכי רשימה למבנה פנימי של מסך פירוט.
- זה עלול ליצור שאילתות כבדות יותר או N+1 queries אם לא מטופל בזהירות.
- זה מטשטש את ההבדל בין summary endpoint לבין detail endpoint.

לכן ההחלטה לא צריכה להיות "להחזיר הכל ברשימות", אלא האם להוסיף summary פיננסי ייעודי להקשר שבו הוא נדרש.

## חלופות

### חלופה 1: להשאיר את המצב הנוכחי

`ReportHistoryTable` תציג רק שדות שכבר קיימים ב־`AnnualReportSummary`:

- שנת מס
- שומה
- החזר מס
- חבות מס
- תאריך הגשה
- סטטוס

יתרונות:

- אין שינוי backend.
- אין עלות ביצועים נוספת.
- חוזה ה־API נשאר נקי וברור.

חסרונות:

- הטבלה פחות מועילה להשוואה בין שנים.
- נתוני הכנסה/הוצאה/רווח מופיעים רק בדוח הנוכחי או בגרף.
- המשתמש צריך לפתוח דוחות או להסתמך על גרף כדי להבין תמונה רב־שנתית.

### חלופה 2: להעשיר את `listClientReports` בלבד

להוסיף ל־response של:

```text
GET /api/v1/clients/{client_record_id}/annual-reports
```

שדות financial rollup קלים:

- `total_income`
- `total_expenses`
- `profit`
- `final_balance`

יתרונות:

- מתאים להקשר: זו רשימת דוחות של לקוח אחד, לא רשימה כללית.
- מאפשר להחזיר את הטבלה הרב־שנתית בלי הרבה קריאות frontend.
- שומר את list הכללי `/annual-reports` רזה.

חסרונות:

- אותו type בשם `AnnualReportSummary` כבר לא יהיה זהה בכל list endpoints אם לא מפרידים חוזים.
- דורש backend aggregation מחושב לכל דוח ברשימת הלקוח.
- צריך לוודא ביצועים ולהימנע מ־N+1.

אם בוחרים בחלופה זו, מומלץ ליצור טיפוס נפרד:

- backend: `ClientAnnualReportHistoryResponse`
- frontend: `AnnualReportHistoryItem`

ולא להעמיס את `AnnualReportSummary` הכללי.

### חלופה 3: להוסיף endpoint ייעודי להיסטוריה פיננסית

להוסיף endpoint חדש:

```text
GET /api/v1/clients/{client_record_id}/annual-reports/history
```

או:

```text
GET /api/v1/annual-reports/{report_id}/client-history
```

ה־response יהיה מותאם ישירות לטבלה:

- `id`
- `tax_year`
- `status`
- `submitted_at`
- `assessment_amount`
- `refund_due`
- `tax_due`
- `total_income`
- `total_expenses`
- `profit`
- `final_balance`

יתרונות:

- חוזה ברור ומוצרי.
- לא מזהם list endpoints קיימים.
- מאפשר backend optimization ייעודי.
- אפשר להשתמש בו גם בטבלה וגם בהשוואות עתידיות.

חסרונות:

- דורש endpoint חדש, schema חדש, service/repository logic ובדיקות.
- עוד query בפרונט.

זו החלופה הנקייה ביותר אם הטבלה אמורה להיות כלי השוואה פיננסי קבוע.

### חלופה 4: לבצע fetch משלים בפרונט לכל דוח

`ReportHistoryTable` תמשיך לטעון `listClientReports`, ואז עבור כל דוח תטען:

- financial summary
- tax calculation
- advances summary

בדומה ל־`MultiYearPLChart`.

יתרונות:

- לא דורש backend חדש.
- משתמש endpoints קיימים.
- מהיר למימוש.

חסרונות:

- הרבה קריאות HTTP במסך אחד.
- טיפול loading/error מורכב יותר.
- כפילות לוגיקה מול `MultiYearPLChart`.
- פחות מתאים אם מספר הדוחות ללקוח יגדל.

זו חלופה סבירה לטווח קצר בלבד.

## המלצה

ההמלצה היא לבחור בחלופה 3: endpoint ייעודי להיסטוריה פיננסית של דוחות שנתיים ללקוח.

נימוקים:

- מוצרית, הנתונים הפיננסיים חשובים בהיסטוריית הדוחות.
- הנראות צריכה להיות טבלאית ולא רק גרפית.
- הנושא שייך להקשר "לקוח לאורך שנים", לא לכל רשימת דוחות כללית.
- endpoint ייעודי שומר על הפרדה נכונה בין summary list, detail view ו־financial history.
- מאפשר להחזיר בדיוק את הנתונים שהמסך צריך, בלי `schedules`, `status_history` ושדות detail כבדים.

## החלטה נדרשת

צריך להחליט אחת מהאפשרויות:

1. היסטוריית דוחות נשארת טבלת סטטוס בסיסית, ללא נתוני הכנסה/הוצאה/רווח/יתרה.
2. היסטוריית דוחות הופכת לטבלת השוואה פיננסית, ומוסיפים endpoint ייעודי.
3. פתרון ביניים זמני: fetch משלים בפרונט, עד להוספת endpoint.

הבחירה המומלצת: אפשרות 2.

## אם מאשרים את ההמלצה

משימות backend:

- להוסיף schema ייעודי ל־history item.
- להוסיף endpoint client-scoped.
- לחשב לכל דוח את:
  - total income
  - total expenses
  - profit
  - final balance
- לוודא שהשאילתות לא יוצרות N+1.
- להוסיף בדיקות API/service.

משימות frontend:

- להחליף את מקור הנתונים של `ReportHistoryTable` ל־history endpoint.
- להחזיר עמודות:
  - הכנסות
  - הוצאות
  - רווח
  - יתרה/החזר
- להשאיר `AnnualReportSummary` עבור list endpoints רגילים.

