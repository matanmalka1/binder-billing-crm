**מסמך החלטות דומייניות**

מערכת CRM — משרד רו״ח / יועץ מס

גרסה 3.1 — מאי 2026

Domain Architecture Decision Record

Last verified against current backend models/services/OpenAPI: 2026-05-29.

Current implementation status:
- `TaxCalendarEntry` and `DeadlineRule` exist.
- `TaxDeadline` is no longer an application model/route surface.
- `AdvancePayment`, `VatWorkItem`, and `AnnualReport` have non-null `tax_calendar_entry_id` FKs in current models.
- `AdvancePayment` and `VatWorkItem` have `due_date_original` and `due_date_effective` fields.
- `AdvancePayment` still also stores `due_date` as a compatibility/current field.
- `AnnualReport` uses `filing_deadline`, `deadline_type`, and `custom_deadline_note` rather than `due_date_original/effective`.

Future / planned notes in this file are explicitly marked. Unmarked sections describe current decisions or current implementation constraints.

**0. סיכום החלטות — Quick Reference**

עשר החלטות שנעולות. לא לפתוח מחדש ללא תיעוד מפורש.

|                               |                                                                                              |                                  |
|-------------------------------|----------------------------------------------------------------------------------------------|----------------------------------|
| **\#** | **החלטה**                                                             | **סטטוס** |
| 1      | TaxCalendarEntry — כן. מועד רגולטורי כללי, לא per-client.             | ✅ נעול   |
| 2      | ClientTaxObligation — לא. Generation יוצר ישירות business objects.    | ✅ נעול   |
| 3      | TaxDeadline — הוסר מהאפליקציה. לא לפיצ׳רים חדשים.                    | ✅ נעול   |
| 4      | Anchor של workflow objects = client_record_id. לא legal_entity_id.    | ✅ נעול   |
| 5      | סטטוס — נשאר רק על האובייקט העסקי.                                    | ✅ נעול   |
| 6      | due_date_original — immutable snapshot ביצירה.                        | ✅ נעול   |
| 7      | due_date_effective — source of truth לכל overdue/reminders/dashboard. | ✅ נעול   |
| 8      | AnnualReport.period_months_count = nullable. לא 12 בכוח.              | ✅ נעול   |
| 9      | DeadlineRule — חייב effective_from/effective_to לתמיכה בשינויי חוק.   | ✅ נעול   |
| 10     | Migration הדרגתית הושלמה עד wiring שדות/FK. הסרה עתידית של `AdvancePayment.due_date` עדיין מתוכננת. | ✅ נעול   |

**1. ארכיטקטורת הישויות — מה מחובר למה**

זו ההחלטה הכי חשובה לקרוא לפני כל refactor. הבלבול כאן הוא שורש רוב הבאגים.

> LegalEntity ← זהות משפטית (ת.ז. / ח.פ.)  
> id_number  
> entity_type osek_patur \| osek_murshe \| company_ltd \| employee  
> vat_reporting_frequency monthly \| bimonthly \| exempt  
> advance_payment_frequency monthly \| bimonthly  
> advance_rate ← ברירת מחדל לגנרציה בלבד  
>   
> ↓ (1:1 active, via ClientRecord)  
>   
> ClientRecord ← הלקוח במשרד. operational anchor.  
> legal_entity_id → LegalEntity  
> accountant_id  
> status active \| frozen \| closed  
>   
> ↓  
>   
> AdvancePayment ← client_record_id (לא legal_entity_id)  
> VatWorkItem ← client_record_id (לא legal_entity_id)  
> AnnualReport ← client_record_id (לא legal_entity_id)  
>   
> Business ← legal_entity_id (ענף נפרד, לא בשרשרת התפעולית)

⛔ כלל ברזל: workflow objects (AdvancePayment, VatWorkItem, AnnualReport) מקושרים  
ל-ClientRecord — לא ל-LegalEntity ישירות.  
אלו אובייקטים שהמשרד מנהל, לא רק עובדות משפטיות על הישות.  
join ל-LegalEntity תמיד עובר דרך ClientRecord.

**2. הפרדת דומיינים — כלל הברזל**

**שלושת הדומיינים עצמאיים לחלוטין. אין גזירה בין תדירויות.**

|                                   |                                         |                                                  |                                                       |
|-----------------------------------|-----------------------------------------|--------------------------------------------------|-------------------------------------------------------|
| **דומיין** | **אובייקט עסקי** | **source of truth ל**     | **תדירות מגיעה מ**             |
| מע״מ       | VatWorkItem      | עבודת הכנה + הגשה + סטטוס | vat_reporting_frequency בלבד   |
| מקדמות מ״ה | AdvancePayment   | תשלום + סטטוס + סכום      | advance_payment_frequency בלבד |
| דוח שנתי   | AnnualReport     | workflow הגשה + סטטוס     | tax_year (לא תדירות תקופתית)   |
| לוח שנה    | TaxCalendarEntry | מועד רגולטורי כללי        | DeadlineRule                   |

⚠️ אסור לגזור advance_payment_frequency מ-vat_reporting_frequency ולהפך.

**3. מודל הנתונים**

**3.1 DeadlineRule**

חוק רגולטורי. משמש כ-lookup engine בלבד. **חייב versioning** כדי לתמוך בשינויי חוק עתידיים מבלי לשבור חישובים היסטוריים.

> DeadlineRule  
> id  
> rule_type vat_monthly \| vat_bimonthly \| advance_monthly \| advance_bimonthly \| annual_report  
> due_day_of_month int  
> offset_months int  
> effective_from date ← חובה  
> effective_to date ← nullable. null = תקף עד היום  
> description str  
>   
> CONSTRAINT: לא ייתכן שני rules פעילים מאותו rule_type באותו תאריך  
> (effective_from/effective_to לא חופפות לאותו rule_type)

**3.2 TaxCalendarEntry**

עובדה רגולטורית כללית לתקופה. **אינה שייכת ללקוח ספציפי.** נוצרת פעם אחת ומשותפת לכולם.

> TaxCalendarEntry  
> id  
> obligation_type VAT \| ADVANCE_PAYMENT \| ANNUAL_REPORT \| NATIONAL_INSURANCE  
> period YYYY-MM ← null עבור ANNUAL_REPORT  
> period_months_count 1 \| 2 ← null עבור ANNUAL_REPORT  
> tax_year int  
> due_date date ← המועד הרגולטורי הכללי  
> rule_id → DeadlineRule  
>   
> -- Periodic (VAT / ADVANCE_PAYMENT):  
> UNIQUE(obligation_type, period, period_months_count)  
> WHERE obligation_type != 'ANNUAL_REPORT'  
>   
> -- Annual:  
> UNIQUE(obligation_type, tax_year)  
> WHERE obligation_type = 'ANNUAL_REPORT'  
>   
> CONSTRAINT: period IS NOT NULL OR obligation_type = 'ANNUAL_REPORT'  
> CONSTRAINT: period_months_count IS NOT NULL OR obligation_type = 'ANNUAL_REPORT'

**3.3 AdvancePayment — Current State**

> AdvancePayment  
> id  
> client_record_id → ClientRecord (לא legal_entity_id)  
> period YYYY-MM -- snapshot ביצירה  
> period_months_count 1 \| 2 -- snapshot ביצירה, frozen  
> due_date date -- עדיין קיים  
> due_date_original date \| null  
> due_date_effective date \| null  
> due_date_override_reason str \| null  
> expected_amount  
> paid_amount  
> status pending \| paid \| partial  
> paid_at  
> payment_method  
> turnover_amount  
> advance_rate  
> calculated_amount  
> override_amount  
> annual_report_id → AnnualReport (nullable)  
> tax_calendar_entry_id → TaxCalendarEntry (NOT NULL)  
>   
> UNIQUE(client_record_id, period) WHERE deleted_at IS NULL

Future / planned:

- הסרת `due_date` הישן אחרי שכל הקוד מסתמך על `due_date_effective`.
- אם נדרש שם סמנטי יותר ל-`advance_rate`, אפשר לשקול `rate_used`, אבל current code משתמש ב-`advance_rate`.

**3.4 VatWorkItem — Current State**

> VatWorkItem  
> id  
> client_record_id → ClientRecord  
> period YYYY-MM  
> period_type monthly \| bimonthly \| exempt  
> status  
> tax_calendar_entry_id → TaxCalendarEntry (NOT NULL)  
> due_date_original date \| null  
> due_date_effective date \| null  
> due_date_override_reason str \| null  
>   
> UNIQUE(client_record_id, period) WHERE deleted_at IS NULL

Future / planned:

- מעבר אפשרי מ-`period_type` ל-`period_months_count` אם נדרש יישור מלא מול `TaxCalendarEntry`.

**3.5 AnnualReport**

דוח שנתי הוא workflow ארוך, לא תשלום תקופתי. שונה מ-AdvancePayment ו-VatWorkItem בשלושה ממדים:

- period_months_count לא רלוונטי — TaxCalendarEntry.period_months_count = null

- due_date הוא negotiated — filing_deadline + deadline_type + custom_deadline_note הם המקבילה של due_date_effective + override_reason

- הדוח הוא תהליך עם שלבים — לא event בודד

> AnnualReport (current state — קיים במיגרציה)  
> id  
> client_record_id → ClientRecord (לא legal_entity_id)  
> tax_year int  
> deadline_type standard \| extended \| custom  
> filing_deadline datetime ← המקבילה של due_date_effective  
> custom_deadline_note ← המקבילה של override_reason  
> status not_started \| collecting_docs \| ... \| closed  
> tax_calendar_entry_id → TaxCalendarEntry (NOT NULL)  
>   
> UNIQUE(client_record_id, tax_year) WHERE deleted_at IS NULL  

**3.6 TaxDeadline — Transitional Model (Deprecated)**

⛔ TaxDeadline הוסר מהאפליקציה הנוכחית.  
אסור להשתמש בשם או בקונספט הזה לפיצ׳רים חדשים.  
כל query חדש על מועדים יפנה ל-TaxCalendarEntry או לשדות ה-snapshot על האובייקט העסקי.

TaxDeadline מערבב שני מושגים שנפרדו:

- מועד רגולטורי כללי → עבר ל-TaxCalendarEntry

- מצב תפעולי per-client → עבר לשדות על AdvancePayment / VatWorkItem / AnnualReport

Historical migration path:

1.  **שלב א׳ — Additive:** יוצרים TaxCalendarEntry + DeadlineRule. מאכלסים נתונים. מוסיפים tests.

2.  **שלב ב׳ — FK + Snapshots:** מוסיפים tax_calendar_entry_id + due_date_original/effective לאובייקטים (nullable). מריצים backfill. מאמתים coverage מלא.

3.  **שלב ג׳ — Screen Migration:** מסכים ו-queries קוראים מ-TaxCalendarEntry או משדות ה-snapshot. מריצים grep/audit לפני המעבר.

4.  **שלב ד׳ — Removal:** לאחר שכל הקוד עבר ו-audit אישר — TaxDeadline נמחק.

Current status: שלב ד׳ הושלם עבור מודל/ראוטים בשם `TaxDeadline`. עדיין נשארת משימת Future / planned להסרת `AdvancePayment.due_date` הישן.

**4. מודל due_date**

|                                                    |                                                                    |                                                              |                                                           |
|----------------------------------------------------|--------------------------------------------------------------------|--------------------------------------------------------------|-----------------------------------------------------------|
| **שדה**                     | **נמצא על**                                 | **משמעות**                            | **ניתן לשינוי?**                   |
| due_date (current)          | AdvancePayment                              | שדה ישן שנשאר לצד original+effective | כן — בינתיים                       |
| filing_deadline (current)   | AnnualReport                                | המקבילה של due_date_effective         | כן, עם deadline_type               |
| due_date                    | TaxCalendarEntry                            | המועד הרגולטורי הכללי                 | כן — לא משפיע אוטומטית על קיים     |
| due_date_original (current) | AdvancePayment / VatWorkItem                | Snapshot מ-entry בזמן יצירה           | לא — immutable לחלוטין             |
| due_date_effective (current) | AdvancePayment / VatWorkItem               | המועד בפועל                           | כן — עם reason + status constraint |

⛔ כלל ברזל: כל חישוב overdue, reminder, urgency, badge, alert —  
חייב להשתמש ב-due_date_effective (או filing_deadline ל-AnnualReport).  
אסור להשתמש ב-TaxCalendarEntry.due_date או ב-due_date_original.

**תנאים לעדכון due_date_effective**

- due_date_override_reason חייב להיות מסופק

- status לא טרמינלי. בפועל אין endpoint ייעודי שמעדכן `due_date_effective`; שינוי עתידי חייב לאכוף reason והרשאות.

- המשתמש בעל הרשאת override מפורשת

**5. Invariants — חייבים להיבדק בטסטים**

**INV-01 — אי-חפיפה בתקופות**

**Service/test invariant בשלב ראשון — לא DB constraint.** לא לנסות לאכוף ב-DB עכשיו, זה מורכב.

> לא ייתכן שתי רשומות מאותו סוג ואותה ישות שהתקופות שלהן חופפות:  
> period=2026-03, months=2 → מכסה מרץ + אפריל  
> period=2026-04, months=2 → מכסה אפריל + מאי ← אפריל כפול. אסור.

**INV-02 — period_months_count עקבי עם תדירות הישות**

ClientRecord עם vat_reporting_frequency=monthly לא יכול להיות עם VatWorkItem שמכיל period_months_count=2, אלא אם קיים override מפורש.

**INV-03 — period_months_count nullable רק ל-ANNUAL_REPORT**

ב-TaxCalendarEntry, period_months_count מותר כ-null רק כאשר obligation_type=ANNUAL_REPORT. על ADVANCE_PAYMENT או VAT — null הוא באג.

**INV-04 — due_date_original immutable**

due_date_original נכתב רק בעת יצירה. לא קיים update endpoint שמקבל אותו.

**INV-05 — due_date_effective בכל overdue query**

כל query שמחשב overdue, כל badge אדום, כל reminder — חייב לרוץ על due_date_effective. שימוש ב-due_date_original או ב-TaxCalendarEntry.due_date בהקשר זה הוא באג.

**INV-06 — advance_rate snapshot frozen**

AdvancePayment.advance_rate הוא snapshot בזמן היצירה. לא נטען מחדש. שינוי ב-LegalEntity.advance_rate לא משפיע על רשומות קיימות.

**INV-07 — הפרדת תדירויות**

אסור לכל קוד להשתמש ב-vat_reporting_frequency לקביעת advance_payment_frequency ולהפך.

**INV-08 — period הוא source of truth, לא due_date**

אסור לגזור period מתוך due_date. הכיוון תמיד: period → due_date.

**INV-09 — status transitions חוקיות**

- VatWorkItem לא עובר ל-filed ללא assigned_to

- AdvancePayment יכול להחזיק `paid_at`, אך current update schema אינו מחייב `paid_at` במעבר ל-`paid`.

- due_date_effective לא מתעדכן ללא due_date_override_reason

- Future / planned: אם נוסף endpoint לשינוי `due_date_effective`, אסור לעדכן רשומות טרמינליות.

**INV-10 — UNIQUE constraints**

> TaxCalendarEntry (periodic): UNIQUE(obligation_type, period, period_months_count)  
> WHERE obligation_type != 'ANNUAL_REPORT'  
> TaxCalendarEntry (annual): UNIQUE(obligation_type, tax_year)  
> WHERE obligation_type = 'ANNUAL_REPORT'  
> AdvancePayment: UNIQUE(client_record_id, period) WHERE deleted_at IS NULL  
> VatWorkItem: UNIQUE(client_record_id, period) WHERE deleted_at IS NULL  
> AnnualReport: UNIQUE(client_record_id, tax_year) WHERE deleted_at IS NULL

**INV-11 — DeadlineRule לא חופף**

לא ייתכן שני DeadlineRule פעילים מאותו rule_type באותו תאריך. effective_from/effective_to לא חופפות לאותו rule_type.

**6. כללי Grouping**

**כלל יסוד:** תקופה עסקית = (period, period_months_count). לא due_date.

- Grouping תמיד לפי (obligation_type, period, period_months_count)

- מיון לפי due_date_effective מותר — אבל לא כ-grouping key

- שני אובייקטים עם due_date זהה אינם אותה תקופה אם period שונה

> דוגמה — אותו due_date, שני אובייקטים שונים לחלוטין:  
> VatWorkItem: period=2026-04, months=1, due_date=15/05 -- עוסק חודשי  
> AdvancePayment: period=2026-03, months=2, due_date=15/05 -- דו-חודשי  
> -- אסור לאחד.

**7. Generation — יצירת אובייקטים**

**7.1 Onboarding — לקוח חדש**

5.  **שלב 1:** יוצרים LegalEntity + ClientRecord

6.  **שלב 2:** קובעים vat_reporting_frequency, advance_payment_frequency, advance_rate

7.  **שלב 3:** Generation יוצר obligations מ-reference_date עד סוף שנת המס הנוכחית

8.  **שלב 4:** לפי advance_payment_frequency — יוצר AdvancePayment per TaxCalendarEntry, עם snapshot

9.  **שלב 5:** לפי vat_reporting_frequency — יוצר VatWorkItem per TaxCalendarEntry, עם snapshot

10. **שלב 6:** לקוח מופיע במסך מועדים דרך האובייקטים המקושרים

**7.2 Scheduled Generation — שוטף**

- רץ לפחות אחת לחודש

- יוצר אובייקטים לפחות 12 חודשים קדימה

- לא "חודשיים קדימה" — זה דל מדי למסך מועדים שימושי

⚠️ Generation לא יוצר ClientTaxObligation. יוצר ישירות AdvancePayment/VatWorkItem עם FK ל-TaxCalendarEntry.

**8. מסכים — מה קורא מאיפה**

**מסך מועדים ראשי**

- קורא מ-TaxCalendarEntry + aggregation מ-AdvancePayment/VatWorkItem/AnnualReport

- קיבוץ לפי (obligation_type, period, period_months_count) — לא לפי due_date

- חישוב overdue לפי due_date_effective — לא TaxCalendarEntry.due_date

**מסך מקדמות**

- קורא מ-AdvancePayment לפי client_record_id

- period/due/status מהאובייקט עצמו — לא מ-TaxCalendarEntry בזמן ריצה

**מסך מע״מ**

- קורא מ-VatWorkItem בלבד

**כרטיס לקוח**

- קורא מ-AdvancePayment + VatWorkItem + AnnualReport לפי client_record_id

- join ל-LegalEntity עובר דרך ClientRecord בלבד

|                                    |                                                       |                                                                  |
|------------------------------------|-------------------------------------------------------|------------------------------------------------------------------|
| **מסך**     | **קורא מ**                     | **אסור**                                  |
| מועדים ראשי | TaxCalendarEntry + aggregation | לגזור period מ-due_date                   |
| מקדמות      | AdvancePayment                 | לקרוא due_date מ-entry בזמן ריצה          |
| מע״מ        | VatWorkItem                    | לסנן לפי due_date בלי period              |
| כרטיס לקוח  | כל האובייקטים של הלקוח         | join ישיר ל-LegalEntity מ-business object |
| דוח חודשי   | כל האובייקטים                  | לקבץ לפי due_date בלבד                    |

**9. Current Implementation Notes**

Current backend already includes:

- `TaxCalendarEntry` model, repository, generation/materialization services, and grouped routes.
- `DeadlineRule` model, repository, bootstrap defaults, and settings routes.
- `tax_calendar_entry_id` on VAT, advance payments, and annual reports.
- `due_date_original/effective` snapshots on VAT and advance payments.
- due-date queries in work queue, VAT compliance, and notification policy using `due_date_effective` where relevant.

Future / planned:

- Remove legacy `AdvancePayment.due_date` after consumers are audited.
- Add an explicit due-date override endpoint only if product needs it, with reason, permissions, and terminal-state guards.

מסמך זה הוא decision log. כל שינוי מבני חייב לעבור עדכון כאן לפני כתיבת קוד.

גרסה 3.1 — מאי 2026
