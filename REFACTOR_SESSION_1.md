# סיכום ריפקטור מודלים — סשן 1

## מה עשינו

### מתודולוגיה
עברנו מודל מודל, הבנו את הלוגיקה העסקית האמיתית של משרד יועץ מס ישראלי,
ותיקנו את המבנה בהתאם.

---

## מודלים שהושלמו ✅

### 1. `Binder` (קלסר)
**קובץ:** `binder.py`

**שינויים:**
- `business_id` → `client_id` — קלסר שייך ללקוח, לא לעסק ספציפי
- הוסר `binder_type` — הסוג שייך לחומר, לא לקלסר
- הוסר `annual_report_id` — קשר שגוי, עובר ל-`BinderIntakeMaterial`
- הוסר `received_at`, `received_by` — שייכים ל-`BinderIntake`
- נוסף `period_start`, `period_end` — תקופת הקלסר (01/2026 עד 06/2026)
- נוסף `created_by`
- נשאר `status` (IN_OFFICE, READY_FOR_PICKUP, RETURNED)
- נשאר `returned_at`, `pickup_person_name`
- `binder_number` — ייחודי גלובלי, המערכת מציעה MAX+1 עם אפשרות דריסה

**לוגיקה עסקית:**
- קלסר = כלי פיזי שמייצג לקוח (לא עסק)
- לקוח עם 3 עסקים → כל החומר באותו קלסר
- כשקלסר מתמלא → פותחים קלסר חדש עם אותו מספר ותקופה חדשה
- READY_FOR_PICKUP → שולח התראה ללקוח לאסוף
- חובת שמירה 7 שנים → לקוחות לא תמיד אוספים בזמן

---

### 2. `BinderIntake` (אירוע קבלת חומר)
**קובץ:** `binder_intake.py`

**שינויים:**
- נשאר כמעט זהה — `binder_id`, `received_at`, `received_by`, `notes`
- הופרד מ-`BinderIntakeMaterial` לקובץ נפרד

---

### 3. `BinderIntakeMaterial` (פריט חומר) — **חדש לחלוטין**
**קובץ:** `binder_intake_material.py`

**שדות:**
```
intake_id       → FK לאירוע הקבלה
business_id     → FK לעסק ספציפי (nullable — לחומר כללי)
material_type   → סוג החומר (enum)
annual_report_id → FK לדוח שנתי (nullable)
description     → תיאור חופשי
```

**`MaterialType` enum (חדש — מחליף את `BinderType`):**
```
vat, income_tax, annual_report, salary, bookkeeping,
national_insurance, capital_declaration, pension_and_insurance,
corporate_docs, tax_assessment, other
```

**לוגיקה עסקית:**
- רק רישום — אין קובץ מצורף
- אם צריך לשמור קובץ חשוב → PermanentDocument
- business_id קריטי כי חשבוניות של עסק גינון ≠ חשבוניות של מסעדה

---

### 4. `BinderStatusLog`
**קובץ:** `binder_status_log.py`

ללא שינוי מבני — נשאר כמו שהיה.

---

### 5. `Business`
**קובץ:** `business.py`

**שינויים:**
- נוסף `official_phone` (עמודת DB) + property `phone` עם fallback ל-`client.phone`
- נוסף `official_email` (עמודת DB) + property `email` עם fallback ל-`client.email`
- נוסף property `full_name` → `business_name or client.full_name`
- נוסף `client = relationship("Client", lazy="select")`
- הוסר `primary_binder_number` — שריד מ-`clients`, אין שימוש
- `lazy="select"` גלובלי + `joinedload` מפורש ב-repository כשצריך

**לוגיקה עסקית:**
- עסק בע"מ יכול להיות בעל מייל/טלפון שונה מהאדם הפרטי
- עוסק פטור = בדרך כלל אותם פרטים כמו הלקוח
- properties עם fallback שומרים על backward compatibility

---

### 6. `Client`
**קובץ:** `client.py`

**שינויים:**
- `Client` = זהות בלבד (שם, ת.ז., פרטי קשר, כתובת)
- שדות legacy נשמרו כ-`nullable` + מסומנים `DEPRECATED`:
  - `client_type` → השתמש ב-`Business.business_type`
  - `status` → השתמש ב-`Business.status`
  - `primary_binder_number` → אין שימוש
  - `opened_at` → השתמש ב-`Business.opened_at`
  - `closed_at` → השתמש ב-`Business.closed_at`
- `ClientType`, `ClientStatus` נשמרו כ-aliases ל-`BusinessType`, `BusinessStatus`

**סיבה לשמירת legacy:**
- SQLite (dev) לא תומך ב-DROP COLUMN
- PostgreSQL (prod) הסיר אותם במיגרציה `e1f2a3b4c5d6`
- אין קוד שכותב לשדות אלה — רק קריאות שצריכות תיקון

**קוד שצריך תיקון (קורא legacy fields):**
```
client_lookup.py (lines 45, 50, 62)     → client.status    → business.status
action_contracts.py (line 74)           → client.status    → business.status
timeline_client_builders.py (lines 29, 33) → client.client_type/opened_at → business
timeline_client_aggregator.py (line 28) → מעביר Business לפונקציה שמצפה Client
```

---

## מודלים שנשאר לעבור ❌

### עדיפות גבוהה (בעיות קריטיות)

1. **`VatWorkItem`**
   - `client_id` → צריך `business_id`
   - `UniqueConstraint("client_id", "period")` → צריך `("business_id", "period")`
   - Repository כבר עובד עם `business_id` — סתירה קריטית
   - שאלה פתוחה: האם כל עסק מגיש דוח מע"מ נפרד?

2. **`AuthorityContact`**
   - מודל Python עדיין עם `client_id` ישיר
   - Migration יצר `authority_contact_links` (M2M) בנפרד
   - Repository כבר עובד עם `business_id`
   - אי עקביות: האם עובדים ישירות או דרך links?

3. **`NotificationService`**
   - עדיין מקבל `client_id` ומחפש פרטי קשר ב-`Client`
   - אחרי הריפקטור: `phone`/`email` יכולים להיות על `Business`

### עדיפות בינונית

4. **`PermanentDocument`**
   - `client_id` (NOT NULL) + `business_id` (nullable) + `scope`
   - האם `client_id` חובה גם למסמכי `scope=business`?
   - CheckConstraint קיים אבל לא מלא

5. **`client_tax_profiles`** vs **`business_tax_profiles`**
   - שתי טבלאות עם אותו תפקיד
   - `client_tax_profiles` לא נמחקה אחרי migration
   - האם ניתן למחוק?

6. **`annual_reports`**
   - `client_type` — האם snapshot נכון או צריך לבוא מ-`business.business_type`?

### עדיפות נמוכה (שריד / תיקון קוד)

7. **`client_excel_service.py`** — מעביר `client_type`/`opened_at` ל-`create_client`
8. **`timeline_client_builders.py`** — שני אירועים נפרדים: `client_created` vs `business_created`
9. **`reports/services/`** — JOINים על `client_id` במקום `business_id`:
   - `annual_report_status_report.py`
   - `vat_compliance_report.py`
   - `advance_payment_report.py`
   - `reports_service.py` (aging)
10. **`search_service.py`** — קורא ל-`business_repo.search(business_name=...)` שלא קיים
11. **`binders_common.py`** — קורא ל-`get_binder_with_client_name()` שלא קיים

---

## החלטות ארכיטקטורליות שהתקבלו

| נושא | החלטה |
|------|--------|
| קלסר שייך ל... | לקוח (Client), לא עסק |
| סוג חומר | על BinderIntakeMaterial, לא על Binder |
| binder_number | ייחודי גלובלי, MAX+1 עם אפשרות דריסה |
| phone/email על Business | כן — official_phone/email עם fallback |
| full_name על Business | property: business_name or client.full_name |
| lazy loading | lazy="select" + joinedload מפורש |
| legacy fields על Client | נשמרים nullable לתאימות SQLite |
| client_created vs business_created | שני אירועי timeline נפרדים |
