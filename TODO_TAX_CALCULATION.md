# TODO — Tax Calculation Engine

> Rules: max 150 lines/file · ORM only · API → Service → Repository · no raw SQL
> Frontend: `../frontend/` — React 19 + TypeScript + React Query

## מצב נוכחי

הרוב כבר ממומש. פערים ספציפיים בלבד:

**קיים ✅**
- `app/annual_reports/services/tax_engine.py` — מדרגות מס 2024, credit points, pension deduction, donation credit
- `app/annual_reports/services/ni_engine.py` — ביטוח לאומי (5.97% + 17.83%), תקרה ₪90,264
- `app/annual_reports/services/financial_tax_service.py` — `get_tax_calculation()` מחבר הכל + VAT + מקדמות
- `GET /api/v1/annual-reports/{report_id}/tax-calculation` — מחזיר `TaxCalculationResponse` מלא
- Frontend: `TaxCalculationPanel`, `TaxBracketsTable`, `TaxCreditsPanel` — מוצג ועובד

---

## פערים לתיקון

### 1. מדרגות מס — עדכון שנתי (2025 / 2026)

**Backend**
- [ ] קרא `app/annual_reports/services/tax_engine.py` — מדרגות hardcoded לשנת 2024 בלבד
- [ ] שנה את המבנה: `BRACKETS_BY_YEAR: dict[int, list[tuple]]` — מילון לפי שנה
- [ ] הוסף מדרגות 2025 (עודכנו ב-1.1.2025 לפי מדד):
  ```
  84,120  → 10%
  120,720 → 14%
  193,800 → 20%
  269,280 → 31%
  576,540 → 35%
  מעל    → 47%
  ```
- [ ] הוסף מדרגות 2026 (עדכון צפוי ~3.5% מדד — להשאיר כ-placeholder זהה ל-2025 עד עדכון רשמי)
- [ ] `calculate_tax(taxable_income, tax_year=2024, ...)` — קבל `tax_year` כפרמטר, בחר brackets בהתאם
- [ ] עדכן `financial_tax_service.py` — העבר `report.tax_year` לפונקציה
- [ ] עדכן `credit_point_value` לפי שנה:
  - 2024: ₪2,904
  - 2025: ₪3,003 (עדכון מדד)
  - 2026: ₪3,003 (placeholder)

**Frontend** — אין שינוי (מקבל תוצאות מהbackend)

---

### 2. ביטוח לאומי — עדכון תקרה לפי שנה

**Backend**
- [ ] קרא `app/annual_reports/services/ni_engine.py` — תקרה hardcoded ₪90,264 (2024)
- [ ] שנה ל: `NI_CEILING_BY_YEAR: dict[int, float]`:
  ```python
  NI_CEILING_BY_YEAR = {
      2024: 90_264,
      2025: 93_384,   # עדכון מדד 1.1.2025
      2026: 93_384,   # placeholder
  }
  ```
- [ ] `calculate_national_insurance(income, tax_year=2024)` — קבל `tax_year`, בחר תקרה בהתאם
- [ ] עדכן `financial_tax_service.py` — העבר `report.tax_year`

**Frontend** — אין שינוי

---

### 3. Credits חסרים מהחישוב

**Backend**
- [ ] קרא `app/annual_reports/services/tax_engine.py` — `pension_credit_points`, `life_insurance_credit_points`, `tuition_credit_points` קיימים ב-`AnnualReportDetail` אך **לא מועברים לפונקציה `calculate_tax()`**
- [ ] הוסף פרמטרים לפונקציה:
  ```python
  def calculate_tax(
      taxable_income,
      tax_year=2024,
      credit_points=2.25,
      pension_credit_points=0.0,
      life_insurance_credit_points=0.0,
      tuition_credit_points=0.0,
      pension_deduction=0.0,
      donation_amount=0.0,
      other_credits=0.0,
  )
  ```
- [ ] סה"כ credit points = `credit_points + pension_credit_points + life_insurance_credit_points + tuition_credit_points`
- [ ] עדכן `financial_tax_service.py` — שלוף את כל שדות ה-credit מ-`AnnualReportDetail` והעבר
- [ ] עדכן `TaxCalculationResponse` — הוסף שדה `total_credit_points: float` לתצוגה

**Frontend**
- [ ] קרא `src/features/annualReports/components/tax/TaxCreditsPanel.tsx`
- [ ] `TaxCreditsPanel` כבר מציג pension/life/tuition credit points — וודא שהסכום הכולל מוצג נכון
- [ ] קרא `src/features/annualReports/components/tax/TaxCalculationPanel.tsx`
- [ ] הוסף שורת "סה"כ נקודות זיכוי: X" בסיכום אם לא קיימת

---

### 4. הצגת total_liability — שדה חסר בUI

**Backend** — `total_liability` כבר מחושב ב-`financial_tax_service.py` (tax + NI - advances_paid)

**Frontend**
- [ ] קרא `src/features/annualReports/components/tax/TaxCalculationPanel.tsx`
- [ ] אם `total_liability` לא מוצג — הוסף כרטיס "סה"כ חבות נטו" מתחת לחישוב הראשי
- [ ] צבע: אדום אם חיובי (חוב), ירוק אם שלילי (זכאות להחזר)

---

### 5. הצגת NI בפאנל Credits

**Frontend**
- [ ] קרא `src/features/annualReports/components/tax/TaxCreditsPanel.tsx`
- [ ] ביטוח לאומי מחושב ב-backend אך לא ברור אם מוצג ב-TaxCreditsPanel
- [ ] אם לא — הוסף שורה: "ביטוח לאומי: ₪X" (base + high בפירוט)

---

## אימות

```bash
# Backend
JWT_SECRET=test-secret pytest -q app/annual_reports/

# בדוק manually:
# 1. צור annual report לשנת 2025
# 2. הוסף income line של ₪200,000
# 3. GET /api/v1/annual-reports/{id}/tax-calculation
# 4. ודא שמדרגות 2025 בשימוש
# 5. ודא שNI מחושב עם תקרת 2025
# 6. ודא ש-pension_credit_points + life_insurance_credit_points מחושבים
```

## קבצים קריטיים

**Backend (לשינוי):**
- `app/annual_reports/services/tax_engine.py`
- `app/annual_reports/services/ni_engine.py`
- `app/annual_reports/services/financial_tax_service.py`
- `app/annual_reports/schemas/annual_report_financials.py`

**Frontend (לשינוי):**
- `src/features/annualReports/components/tax/TaxCalculationPanel.tsx`
- `src/features/annualReports/components/tax/TaxCreditsPanel.tsx`
