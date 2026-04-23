# איפיון מסכים — Frontend CRM

## מטרה

מסמך זה מגדיר איפיון אחיד למסכים הקיימים בפועל ב־`../frontend`.
המטרה היא לייצר מקור אמת ברור ל־UX, להרשאות, לנתונים, לפעולות, ולפערים המבניים שגורמים לשבירות.

## תבנית איפיון אחידה לכל מסך

- מטרה עסקית
- מי משתמש בו: `ADVISOR` / `SECRETARY` / ציבורי
- נתונים מוצגים
- פעולות מותרות
- פילטרים, מיון, חיפוש, פגינציה
- מצבי ריק / שגיאה / טעינה
- תלותים במסכים אחרים
- פערים, כפילויות ושבירות נוכחית

## עקרונות רוחביים

- כל מסך רשימה חייב להגדיר במפורש: פילטרים, מיון, חיפוש, פגינציה, empty state, error state.
- כל מסך detail חייב להגדיר: מזהה כניסה, invalid-id state, loading state, not-found/error state.
- כל מסך עם טאבים חייב להגדיר האם הטאב נשמר ב־URL.
- כל מסך חייב להגדיר הרשאות ברמת צפייה וברמת פעולה.
- אין להסתמך על "מה שהקומפוננטה עושה כרגע" במקום על חוזה מסך כתוב.

## מסכים

### 1. Login

- מטרה עסקית: כניסה מאובטחת למערכת עבור משתמשי משרד.
- מי משתמש בו: כל משתמש לא מזוהה.
- נתונים מוצגים: שדות אימייל, סיסמה, שגיאת שרת, מצב טעינה.
- פעולות מותרות: התחברות, הצגת/הסתרת סיסמה.
- פילטרים, מיון, חיפוש, פגינציה: אין.
- מצבי ריק / שגיאה / טעינה:
  - מצב רגיל: טופס התחברות.
  - מצב טעינה: כפתור במצב התחברות.
  - מצב שגיאה: הודעת שגיאה מהשרת.
  - מצב redirect: משתמש מחובר מועבר ל־`/`.
- תלותים במסכים אחרים: Dashboard לאחר login מוצלח.
- פערים, כפילויות ושבירות נוכחית:
  - הוחלף לשימוש בפרימיטיבים האחידים של המערכת (`Input`, `Button`, `Alert`), אך ה־toggle להצגת/הסתרת סיסמה עדיין ממומש מקומית בתוך השדה.
  - שפת UI נפרדת משאר האפליקציה.

### 2. Dashboard

- מטרה עסקית: תמונת מצב משרדית ופעולות מהירות לפי תפקיד.
- מי משתמש בו: `ADVISOR`, `SECRETARY`.
- נתונים מוצגים: stats, attention items, quick actions, season summary, advisor today.
- פעולות מותרות:
  - `ADVISOR`: quick actions, אישורי confirm.
  - `SECRETARY`: צפייה בלבד בגרסה מצומצמת.
- פילטרים, מיון, חיפוש, פגינציה: אין.
- מצבי ריק / שגיאה / טעינה:
  - skeleton לטעינה.
  - denied state.
  - error state.
- תלותים במסכים אחרים: binders, deadlines, annual reports, operational flows.
- פערים, כפילויות ושבירות נוכחית:
  - תצוגה תלויה role ללא חוזה מסך מפורש.
  - חלקים שלמים נעלמים לפי role במקום תבנית מסך יציבה.

### 3. Binders

- מטרה עסקית: ניהול מחזור חיים של קלסרים.
- מי משתמש בו: `ADVISOR`, `SECRETARY`.
- נתונים מוצגים: רשימת קלסרים, counters, קלסר נבחר, deep link לקלסר.
- פעולות מותרות:
  - קליטת חומר.
  - פתיחת detail drawer.
  - סימון מוכן.
  - ביטול סימון מוכן.
  - החזרה.
  - מסירה.
  - מחיקה.
  - bulk ready.
- פילטרים, מיון, חיפוש, פגינציה:
  - פילטרים לפי סטטוס ותקופה.
  - פגינציה קיימת.
  - מיון אינו מוגדר כמנגנון מסך מפורש.
- מצבי ריק / שגיאה / טעינה:
  - loading בטבלה.
  - error בטבלה.
  - empty state עם CTA לקליטת חומר.
  - dialogs ל־return/delete/bulk/handover.
- תלותים במסכים אחרים: clients, businesses, annual reports.
- פערים, כפילויות ושבירות נוכחית:
  - page כבד עם orchestration רב.
  - detail ו־receive חולקים drawer behavior.
  - state מפוזר בין table, drawer ו־dialogs.

### 4. Clients

- מטרה עסקית: ניהול רשימת לקוחות מלאה.
- מי משתמש בו: `ADVISOR`, `SECRETARY`.
- נתונים מוצגים: רשימת לקוחות, stats לפי status, total, pending actions.
- פעולות מותרות:
  - `ADVISOR`: יצירה, עריכה, import/export, restore.
  - `SECRETARY`: צפייה בלבד.
- פילטרים, מיון, חיפוש, פגינציה:
  - פילטרים.
  - פגינציה.
  - page size.
  - sorting קיים ברמת feature אך לא מוגדר כאן כחוזה מסך מפורש.
- מצבי ריק / שגיאה / טעינה:
  - readonly alert.
  - empty state עם CTA.
  - deleted-client conflict dialog.
  - confirm dialog לפעולות ממתינות.
- תלותים במסכים אחרים: ClientDetails, ImportExport.
- פערים, כפילויות ושבירות נוכחית:
  - יותר מדי מודלים במסך אחד: create, edit, restore, import/export.
  - orchestration כבד ברמת page.

### 5. Client Details

- מטרה עסקית: מעטפת 360 ללקוח.
- מי משתמש בו: `ADVISOR`, `SECRETARY`.
- נתונים מוצגים:
  - פרטי לקוח.
  - binders.
  - charges.
  - טאבים: details, documents, deadlines, timeline, vat, advance-payments, annual-reports, communication, finance.
- פעולות מותרות:
  - עדכון לקוח.
  - מחיקת לקוח.
  - יצירת עסק.
  - פעולות פנימיות לפי טאב.
- פילטרים, מיון, חיפוש, פגינציה:
  - לא ברמת המעטפת.
  - קיימים בתוך טאבים מסוימים.
- מצבי ריק / שגיאה / טעינה:
  - invalid id.
  - loading.
  - error / missing client.
  - readonly alert להרשאות.
- תלותים במסכים אחרים:
  - documents.
  - deadlines.
  - timeline.
  - VAT.
  - advance payments.
  - annual reports.
  - communication.
  - finance.
- פערים, כפילויות ושבירות נוכחית:
  - active tab לא מנוהל ב־URL.
  - יש deeplink רק לחלק מהטאבים דרך route נפרד.
  - refresh או שיתוף לינק לא שומרים תמיד הקשר מלא.

### 6. Business Details

- מטרה עסקית: תצוגת פרטי עסק תחת לקוח.
- מי משתמש בו: `ADVISOR`, `SECRETARY`.
- נתונים מוצגים: פרטי עסק, סטטוס, תאריכים, לקוח מקושר, notes.
- פעולות מותרות: עריכת notes לפי הרשאה.
- פילטרים, מיון, חיפוש, פגינציה: אין.
- מצבי ריק / שגיאה / טעינה:
  - invalid id.
  - loading.
  - error.
- תלותים במסכים אחרים: ClientDetails, Notes.
- פערים, כפילויות ושבירות נוכחית:
  - מסך דק מאוד שאינו מוגדר כמסך עשיר.
  - אם יתווספו פעולות עסק, המבנה הנוכחי ידרוש refactor.

### 7. Search

- מטרה עסקית: חיפוש גלובלי על פני ישויות מערכת.
- מי משתמש בו: `ADVISOR`, `SECRETARY`.
- נתונים מוצגים: תוצאות חיפוש כלליות, תוצאות מסמכים.
- פעולות מותרות:
  - חיפוש חופשי.
  - פתיחת advanced filters.
  - reset לחיפוש.
- פילטרים, מיון, חיפוש, פגינציה:
  - query חופשי.
  - client_name.
  - id_number.
  - binder_number.
  - פגינציה.
- מצבי ריק / שגיאה / טעינה:
  - no filter state.
  - no results state.
  - error alert.
  - loading בטבלה.
- תלותים במסכים אחרים: clients, binders, documents.
- פערים, כפילויות ושבירות נוכחית:
  - results ו־documents מוצגים בשני אזורים שונים.
  - אין מודל תוצאות אחיד למסך חיפוש.

### 8. Charges

- מטרה עסקית: ניהול חיובים ופעולות גבייה.
- מי משתמש בו: `ADVISOR`, `SECRETARY`.
- נתונים מוצגים: רשימת חיובים, summary stats, selected ids.
- פעולות מותרות:
  - `ADVISOR`: יצירה, פעולות שורה, פעולות bulk, detail drawer.
  - `SECRETARY`: צפייה בלבד.
- פילטרים, מיון, חיפוש, פגינציה:
  - פילטרים.
  - פגינציה.
  - page size.
  - status summary filters.
- מצבי ריק / שגיאה / טעינה:
  - readonly alert.
  - empty state.
  - create error.
  - loading/error בטבלה.
- תלותים במסכים אחרים: ClientDetails, actions engine.
- פערים, כפילויות ושבירות נוכחית:
  - row actions ו־bulk actions חיים יחד במסך מורכב.
  - state של selection/action loading רגיש להתנגשויות.

### 9. Annual Reports List

- מטרה עסקית: ניהול עונת דוחות שנתיים.
- מי משתמש בו: בעיקר `ADVISOR`.
- נתונים מוצגים: season summary, overdue reports, filtered reports by tax year.
- פעולות מותרות:
  - יצירת דוח חדש.
  - פתיחת דוח קיים.
- פילטרים, מיון, חיפוש, פגינציה:
  - פילטרים.
  - אין פגינציה מפורשת במסך.
- מצבי ריק / שגיאה / טעינה:
  - loading.
  - error.
  - empty state לשנה ללא דוחות.
- תלותים במסכים אחרים: Annual Report Detail.
- פערים, כפילויות ושבירות נוכחית:
  - naming לא עקבי: hook בשם Kanban אך UI מבוסס טבלה/summary.
  - הרשאות לא מנוסחות בצורה גלויה במסך.

### 10. Annual Report Detail

- מטרה עסקית: עבודה מלאה על דוח שנתי.
- מי משתמש בו: בעיקר `ADVISOR`.
- נתונים מוצגים:
  - overview.
  - financials.
  - tax.
  - deductions.
  - documents.
  - timeline.
  - charges.
  - report status.
- פעולות מותרות:
  - save.
  - export PDF.
  - transitions.
  - update detail.
  - add/complete schedule.
  - delete report.
- פילטרים, מיון, חיפוש, פגינציה: אין.
- מצבי ריק / שגיאה / טעינה:
  - loading.
  - error / missing report.
  - delete confirm.
- תלותים במסכים אחרים:
  - documents.
  - timeline.
  - charges.
  - client context.
- פערים, כפילויות ושבירות נוכחית:
  - active section לא נשמר ב־URL.
  - מסך כבד מאוד עם state orchestration רב.
  - מסך detail מורכב אך לא מוגדר כחוזה מסך מפורט ברמת subsection.

### 11. Tax Deadlines

- מטרה עסקית: ניהול מועדי מס ומעקב הגשה.
- מי משתמש בו: `ADVISOR`, `SECRETARY`.
- נתונים מוצגים: deadlines, submission stats, selected deadline.
- פעולות מותרות:
  - `ADVISOR`: create, generate, edit, delete, complete, reopen.
  - `SECRETARY`: צפייה.
- פילטרים, מיון, חיפוש, פגינציה:
  - פילטרים.
  - פגינציה.
- מצבי ריק / שגיאה / טעינה:
  - loading page.
  - error alert.
  - drawer לפרטי מועד.
  - modals ליצירה/עריכה/generate.
- תלותים במסכים אחרים: dashboard/tax widgets, client workflows.
- פערים, כפילויות ושבירות נוכחית:
  - naming לא חד בין "דוחות מס" ל"מועדי מס".
  - מסך משלב entity management עם operational dashboard.

### 12. Advance Payments

- מטרה עסקית: מעקב מקדמות ודוח גבייה.
- מי משתמש בו: `ADVISOR`, `SECRETARY`.
- נתונים מוצגים:
  - KPI overview.
  - rows לפי לקוח/חודש/סטטוס.
  - report view.
- פעולות מותרות:
  - מעבר בין overview ל־report.
  - drilldown ללקוח.
- פילטרים, מיון, חיפוש, פגינציה:
  - year.
  - month.
  - status.
  - page.
  - tab דרך query params.
- מצבי ריק / שגיאה / טעינה:
  - loading.
  - error.
  - empty table.
- תלותים במסכים אחרים: ClientDetails, reports.
- פערים, כפילויות ושבירות נוכחית:
  - שתי תצוגות שונות מאוד בתוך אותו מסך.
  - ניהול URL ידני ולא אחיד עם שאר מסכי הרשימות.

### 13. VAT Work Items

- מטרה עסקית: ניהול תיקי מע"מ חודשיים ברמת לקוח.
- מי משתמש בו: `ADVISOR`, `SECRETARY`.
- נתונים מוצגים: work items, status stats, urgency badges.
- פעולות מותרות:
  - פתיחת תיק.
  - פעולות שורה.
  - כניסה לתיק מע"מ.
- פילטרים, מיון, חיפוש, פגינציה:
  - פילטרים.
  - פגינציה.
  - page size.
- מצבי ריק / שגיאה / טעינה:
  - loading.
  - error.
  - readonly alert.
  - empty state.
  - create modal.
- תלותים במסכים אחרים: VAT Work Item Detail, ClientDetails.
- פערים, כפילויות ושבירות נוכחית:
  - create flow תלוי גם URL params וגם local state.
  - update מוטבילי של `URLSearchParams` רגיש לשבירות.

### 14. VAT Work Item Detail

- מטרה עסקית: עבודה בתוך תיק מע"מ.
- מי משתמש בו: `ADVISOR`, `SECRETARY`.
- נתונים מוצגים:
  - summary.
  - income invoices.
  - expense invoices.
  - history.
  - filed banner.
- פעולות מותרות:
  - הזנת חשבוניות.
  - עריכת חשבוניות.
  - פעולות הגשה לפי סטטוס.
  - מעבר בין טאבים.
- פילטרים, מיון, חיפוש, פגינציה:
  - טאב ב־URL.
  - אין פגינציה ברמת page.
- מצבי ריק / שגיאה / טעינה:
  - invalid id redirect.
  - loading skeleton.
  - error alert.
- תלותים במסכים אחרים: VAT list, client VAT context.
- פערים, כפילויות ושבירות נוכחית:
  - זה אחד המסכים היחידים עם tab sync ב־URL.
  - מדגיש חוסר אחידות מול Client Details ו־Annual Report Detail.

### 15. VAT Compliance Report

- מטרה עסקית: דוח ניהולי לציות מע"מ.
- מי משתמש בו: בעיקר `ADVISOR`.
- נתונים מוצגים:
  - compliance per client.
  - stale pending items.
  - year selector.
- פעולות מותרות: החלפת שנה.
- פילטרים, מיון, חיפוש, פגינציה:
  - שנה בלבד.
  - אין חיפוש.
  - אין פגינציה.
  - אין sorting גלוי.
- מצבי ריק / שגיאה / טעינה:
  - loading.
  - error.
  - no data for year.
- תלותים במסכים אחרים: VAT operational screens.
- פערים, כפילויות ושבירות נוכחית:
  - טבלאות HTML ידניות במקום פרימיטיב אחיד.
  - אין drilldown מהדוח למסך לקוח/תיק.

### 16. Reminders

- מטרה עסקית: ניהול תזכורות רוחביות.
- מי משתמש בו: `ADVISOR`, `SECRETARY`.
- נתונים מוצגים:
  - reminders.
  - pending/sent counts.
  - linked entities ליצירת reminder.
- פעולות מותרות:
  - יצירת תזכורת.
  - ביטול.
  - סימון כנשלח.
  - פתיחת drawer.
- פילטרים, מיון, חיפוש, פגינציה:
  - status filter.
  - type filter.
  - search.
  - אין פגינציה במסך.
- מצבי ריק / שגיאה / טעינה:
  - loading.
  - error.
  - no reminders.
  - no results for filter.
- תלותים במסכים אחרים:
  - binders.
  - charges.
  - tax deadlines.
  - annual reports.
  - advance payments.
- פערים, כפילויות ושבירות נוכחית:
  - מסך אינטגרטיבי עם הרבה תלותים רוחביים.
  - סיכון גבוה לשבירה כשדומיין אחד משתנה.

### 17. Signature Requests

- מטרה עסקית: ניהול בקשות חתימה בכלל הלקוחות.
- מי משתמש בו: `ADVISOR`, `SECRETARY`.
- נתונים מוצגים:
  - requests.
  - draft/pending/terminal counts.
  - signing URLs.
  - business lookup.
- פעולות מותרות:
  - יצירת בקשה.
  - שליחה.
  - ביטול.
  - צפייה ב־audit.
  - toggle להצגת ארכיון.
- פילטרים, מיון, חיפוש, פגינציה:
  - show all / active only.
  - אין חיפוש.
  - אין פגינציה.
  - אין filters עשירים.
- מצבי ריק / שגיאה / טעינה:
  - loading.
  - error.
  - empty state.
- תלותים במסכים אחרים: Signing Page, ClientDetails.
- פערים, כפילויות ושבירות נוכחית:
  - מסך queue בלי יכולות חיפוש/פילטור מספקות.
  - columns נבנים inline ב־page ומכבידים על התחזוקה.

### 18. Users

- מטרה עסקית: ניהול משתמשים, תפקידים והרשאות.
- מי משתמש בו: `ADVISOR` בלבד.
- נתונים מוצגים: users, filters, audit logs, current user context.
- פעולות מותרות:
  - create user.
  - edit user.
  - reset password.
  - activate/deactivate.
  - פתיחת audit logs.
- פילטרים, מיון, חיפוש, פגינציה:
  - filters.
  - פגינציה.
  - page size.
- מצבי ריק / שגיאה / טעינה:
  - access denied.
  - loading/error.
  - empty state.
  - confirm dialog להפעלה/השבתה.
- תלותים במסכים אחרים: Auth state, audit logs.
- פערים, כפילויות ושבירות נוכחית:
  - הרשאה נאכפת גם ב־router וגם ב־page.
  - כפילות באכיפת access.

### 19. Public Signing

- מטרה עסקית: חתימה ציבורית על בקשת חתימה באמצעות token.
- מי משתמש בו: חותם חיצוני.
- נתונים מוצגים:
  - פרטי בקשה לחתימה.
  - סטטוס חתימה.
  - decline reason.
- פעולות מותרות:
  - approve.
  - decline.
  - confirm approve.
  - confirm decline.
- פילטרים, מיון, חיפוש, פגינציה: אין.
- מצבי ריק / שגיאה / טעינה:
  - loading.
  - error.
  - signed.
  - declined.
  - expired.
- תלותים במסכים אחרים: Signature Requests.
- פערים, כפילויות ושבירות נוכחית:
  - אין איפיון מפורש למעברי state בין ready / confirm / terminal.
  - שפה ויזואלית נפרדת, ללא מסמך UX משלים.

## תבניות שבירה רוחביות

### A. אחידות state management

- יש ערבוב בין `PageStateGuard`, `PageLoading`, `Alert`, וטעינה ידנית.
- אין חוזה אחיד למסך רשימה מול מסך detail.

### B. אחידות URL state

- `VAT Work Item Detail` שומר tab ב־URL.
- `Client Details` ו־`Annual Report Detail` לא שומרים state זהה ב־URL.
- התוצאה: deep link לא אחיד ושבירות ב־refresh/navigation.

### C. אחידות רשימות

- יש `PaginatedDataTable`, `DataTable + PaginationCard`, וטבלאות HTML ידניות.
- אין תבנית UX אחת למסכי list.

### D. הרשאות

- חלק מההרשאות נאכפות ב־router.
- חלק ב־page.
- חלק ב־hook.
- נדרש matrix אחד ברור: `view`, `create`, `edit`, `delete`, `execute`.

### E. מסכים שמנים

- המסכים המועמדים המרכזיים לפירוק:
  - `Clients`
  - `Binders`
  - `Charges`
  - `AdvancePayments`
  - `SignatureRequests`
  - `AnnualReportFullPanel`

## החלטות מוצר/UX מומלצות להמשך

- להגדיר חוזה אחיד למסך list.
- להגדיר חוזה אחיד למסך detail.
- להחליט שכל tab משמעותי נשמר ב־URL.
- להגדיר matrix הרשאות מסכי מערכת.
- להפריד בין screen shell, screen state, screen actions.
- לצמצם page orchestration ולהעביר ל־screen controller hooks קטנים.

## סדר עדיפויות מומלץ

1. חוזה אחיד ל־list screens.
2. URL state אחיד למסכים עם tabs.
3. matrix הרשאות מסודר לכל מסך.
4. פירוק המסכים השמנים.
5. איחוד empty/loading/error states.
