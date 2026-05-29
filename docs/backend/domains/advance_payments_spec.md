## Scope
This file owns only:
- Historical context for a previous advance payments specification.

This file must not contain:
- Current implemented behavior.
- New product requirements.
- Canonical architecture rules.

Source of truth: historical

# מקדמות מס הכנסה — אפיון מלא

> החלטות שהתקבלו בשיחת אפיון. מקור אמת לפני פיתוח.

---

## רקע עסקי

מקדמה = תשלום תקופתי על חשבון מס הכנסה שנתי.

```
מחזור לתקופה × אחוז מקדמות (advance_rate) = סכום מקדמה
```

- due_date = ה-15 לחודש שאחרי תום התקופה
- תדירות: חודשי (period_months_count=1) או דו-חודשי (period_months_count=2)
- מחזור מגיע מדוח מע"מ של אותה תקופה — אבל אין תלות קשיחה (דוח מע"מ לא חייב להיות מוגש לפני המקדמה)
- בסוף שנה: מס שנתי סופי − מקדמות ששולמו = יתרה לתשלום / החזר

---

## מודל נתונים — שינויים נדרשים

### הוצאת `overdue` מה-enum

**לפני:** `status: pending | partial | paid | overdue`

**אחרי:** שני שדות נפרדים:

| שדה | סוג | הסבר |
|-----|-----|-------|
| `payment_status` | enum: `pending \| partial \| paid` | מצב התשלום בפועל |
| `timing_status` | computed (לא נשמר) | `on_time \| overdue` — נגזר מ-`today > due_date AND payment_status != paid` |
| `paid_late` | computed (לא נשמר) | `paid_at > due_date` — שולם במלואו אבל באיחור |

`paid_at` כבר קיים ב-model — נשאר.

**migration נדרש**: הסרת `overdue` מ-enum, עדכון שורות קיימות.

### הוספת שדות מחזור (snapshot)

| שדה | סוג | הסבר |
|-----|-----|-------|
| `reported_turnover` | `Numeric(12,2) \| null` | snapshot של מחזור בזמן דיווח/תשלום |
| `turnover_source_vat_report_id` | `Integer \| null` | FK → vat_reports — איזה דוח שימש |

**לוגיקת snapshot:**

```
payment_status == pending/partial:
  → הצג live מ-vat_reports (אם קיים)
  → אם לא קיים: "דוח מע"מ טרם הוגש"

payment_status == paid:
  → הצג reported_turnover (snapshot)
  → אם vat_report השתנה אחרי: ⚠ "דוח המע"מ עודכן לאחר דיווח המקדמה"
```

**שמירת snapshot**: אוטומטית בעת מעבר ל-`paid` — שולף מ-vat_reports ושומר.

---

## missing_turnover signal

```
missing_turnover = no vat_report for period AND no reported_turnover snapshot
```

פעולות אפשריות:
- **משוך מדוח מע"מ** — אם בינתיים נוצר דוח
- **הזן מחזור ידנית** — דיווח מקדמה ללא דוח מע"מ
- **סמן לא רלוונטי** — אין חובה בפועל

לא חוסם פעולות בודדות. **כן חוסם**: "סמן batch כמוכן לתשלום" אם יש לקוחות עם missing_turnover.

---

## עמוד Overview (`/advance-payments`)

### מטרה
מבט תפעולי שבועי/חודשי — מי צריך לשלם, מי פיגר, מה נגבה.

### גרופינג לפי חודש — collapsed כברירת מחדל

```
מקדמות מאי 2026  ·  42 לקוחות  ·  18 חסרים מחזור  ·  7 באיחור  ·  ₪128,400 לתשלום
▼ פתיחה → רשימת לקוחות
```

**header של כל batch:**
- חודש + שנה
- סה"כ לקוחות בבאטץ'
- `missing_turnover_count` — חסרי מחזור
- `overdue_count` — timing_status=overdue
- סה"כ לתשלום (expected − paid)

**בפתיחת batch:**
- לקוחות עם missing_turnover מופיעים ראשונים עם badge "חסר מחזור"
- שאר הלקוחות ממוינים לפי שם

### KPI header (כל הסינון הנוכחי)
- סה"כ צפוי | סה"כ שולם | אחוז גבייה | סה"כ באיחור

### פילטרים
- שנה (נשאר)
- סטטוס (נשאר)
- ~~חודש~~ — מוסר, גרופינג מחליף

### עמודות בתוך batch פתוח
| עמודה | הערה |
|-------|------|
| מס' לקוח | |
| שם עסק | |
| תאריך יעד | |
| מחזור לתקופה | live / snapshot / "—" |
| סכום צפוי | |
| שולם | |
| יתרה (delta) | |
| payment_status | badge |
| timing_status | badge נפרד (overdue / paid_late) |
| שיטת תשלום | חדש |

### לחיצה על שורה
→ drawer עריכה (ראה פרטים למטה)

---

## טאב לקוח — מקדמות

### header
```
[שם לקוח]
אחוז מקדמות: 5%  |  תדירות: חודשי/דו-חודשי
```

### KPI cards
| כרטיס | שינוי |
|-------|-------|
| סה"כ צפוי שנתי | נשאר |
| סה"כ שולם | נשאר |
| אחוז גבייה | נשאר |
| באיחור (timing_status) | שם משתנה מ"סיגנורים" |

### פילטרים
- שנה (נשאר)
- סטטוס: pending / partial / paid (ללא overdue)

### טבלה — עמודות
| עמודה | שינוי |
|-------|-------|
| תקופה | נשאר |
| מחזור לתקופה | **חדש** — live/snapshot/— |
| סכום צפוי | נשאר |
| שולם | נשאר |
| payment_status | badge |
| timing_status | badge נפרד |
| תאריך יעד | נשאר |
| יתרה (delta) | נשאר |
| הערות | אייקון (נשאר) |

### פעולות
- **הוסף מקדמה** — modal יצירה (נשאר)
- **צור לו מקדמות לשנה** — generate_schedule (נשאר)

### לחיצה על שורה → Drawer עריכה

**שדות בdrawer:**
- `paid_amount` — עריכה
- `expected_amount` — עריכה
- `payment_status` — select
- `payment_method` — select (חדש)
- `paid_at` — date picker (חדש)
- `notes` — textarea עריכה (כרגע read-only בלבד)
- מחזור לתקופה — read-only (live/snapshot)
- אם missing_turnover: פעולות (משוך / הזן ידנית / לא רלוונטי)

---

## סדר פיתוח מוצע

### שלב 1 — Backend (תנאי מוקדם)
1. Migration: הסר `overdue` מ-enum, עדכן שורות קיימות
2. הוסף `reported_turnover` + `turnover_source_vat_report_id` ל-AdvancePayment
3. `timing_status` + `paid_late` כ-computed fields על schema response
4. לוגיקת snapshot בעת update ל-paid
5. endpoint/join לשליפת vat_report turnover לפי period+client
6. `missing_turnover` flag ב-AdvancePaymentRow + OverviewRow
7. batch aggregation: `missing_turnover_count`, `overdue_count` per month group

### שלב 2 — Frontend Overview
1. גרופינג לפי חודש (collapsed by default)
2. batch header עם KPIs
3. עמודות חדשות: מחזור, timing_status, payment_method
4. drawer עריכה

### שלב 3 — Frontend טאב לקוח
1. header עם advance_rate
2. עמודות חדשות
3. drawer עריכה (shared component עם overview)
4. שינוי KPI "סיגנורים" → "באיחור"

---

## החלטות שנסגרו

| נושא | החלטה |
|------|--------|
| overdue | computed (timing_status), לא enum value |
| paid_late | computed מ-paid_at vs due_date |
| מחזור | live מ-vat_reports לפני תשלום, snapshot אחרי |
| עריכה | drawer (לא inline, לא modal) |
| overview layout | גרופינג לפי חודש, collapsed by default |
| advance_rate | מוצג ב-header של טאב לקוח |
| generate_schedule | נשאר בשני המסכים |
| חסר מחזור | signal תפעולי, לא חוסם — אלא אם "סמן batch כמוכן" |
