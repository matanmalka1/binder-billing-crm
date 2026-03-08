You are a senior full-stack engineer working on a Tax Advisor CRM system built with FastAPI (Python) backend and React/TypeScript frontend.

The Annual Reports module already has:
- Report creation with client_type, tax_year, form_type (1301/1215/6111)
- 10-status lifecycle with enforced VALID_TRANSITIONS state machine
- Income lines (AnnualReportIncomeLine) and expense lines (AnnualReportExpenseLine) models
- financial_service.py with get_financial_summary() returning total_income, total_expenses, taxable_income
- Filing readiness gate blocking SUBMITTED transition
- Schedules (annexes) as completion flags only
- AnnualReportDetail sub-entity with tax_refund_amount, tax_due_amount (manually entered)
- SignatureRequest domain with annual_report_id FK and SIGNED status
- AdvancePayment domain exists but has NO link to AnnualReport

You must implement the following missing capabilities IN ORDER. Read CLAUDE.md before starting. Follow all existing patterns exactly.

---

## TASK 1 — Run the pending migration

Run:
  alembic upgrade head

Verify the following tables exist in the DB:
- annual_report_income_lines
- annual_report_expense_lines

Verify the following columns exist:
- charges.annual_report_id
- binders.annual_report_id
- reminders.annual_report_id

---

## TASK 2 — Israeli income tax calculation engine

### Backend

Create: app/annual_reports/services/tax_engine.py

Implement a pure function (no DB calls):

  def calculate_tax(taxable_income: float, credit_points: float = 2.25) -> TaxCalculationResult

TaxCalculationResult is a dataclass or Pydantic model with:
  - taxable_income: float
  - tax_before_credits: float
  - credit_points_value: float        # credit_points × 2,904 (2024 value)
  - tax_after_credits: float          # max(0, tax_before_credits - credit_points_value)
  - effective_rate: float             # tax_after_credits / taxable_income

Use 2024 Israeli tax brackets:
  0       – 81,480     → 10%
  81,480  – 116,760    → 14%
  116,760 – 187,440    → 20%
  187,440 – 260,520    → 31%
  260,520 – 557,640    → 35%
  557,640 – ∞          → 47%

Credit point value for 2024: ₪2,904 per point.

Add to financial_service.py:
  def get_tax_calculation(self, report_id: int) -> TaxCalculationResult
  
  This method:
  1. Calls get_financial_summary() to get taxable_income
  2. Reads credit_points from AnnualReportDetail (default 2.25 if not set)
  3. Calls calculate_tax(taxable_income, credit_points)
  4. Returns the result

Add credit_points field (Numeric 5,2, default 2.25, nullable) to AnnualReportDetail model.

Update AnnualReportDetailUpdateRequest schema to include credit_points: Optional[float].

Write Alembic migration: 0007_add_credit_points_to_annual_report_detail.py

Add endpoint to annual_report_financials.py router:
  GET /annual-reports/{report_id}/tax-calculation
  Returns TaxCalculationResult

### Frontend

Add to annualReports.api.ts:
  - TaxCalculationResult type
  - annualReportsApi.getTaxCalculation(reportId): Promise<TaxCalculationResult>

Add endpoint to endpoints.ts:
  annualReportTaxCalculation: (id) => `/annual-reports/${id}/tax-calculation`

Add QK:
  annualReportTaxCalc: (id) => [...base, id, 'tax-calc']

Create component: TaxCalculationPanel.tsx
  - Displays: taxable income, tax before credits, credit points value, final tax, effective rate
  - All values formatted as ₪ with he-IL locale
  - Shows a note: "חישוב מס לפי מדרגות 2024"
  - Uses useQuery to fetch from the new endpoint

Wire TaxCalculationPanel into AnnualReportDetailDrawer after the IncomeExpensePanel section.

---

## TASK 3 — Link advance payments to annual report

### Backend

In app/advance_payments/models/advance_payment.py:
  Add: annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=True, index=True)

Write Alembic migration: 0008_add_annual_report_id_to_advance_payments.py

In financial_service.py add:
  def get_advances_summary(self, report_id: int) -> AdvancesSummary

  AdvancesSummary is a Pydantic model with:
    - total_advances_paid: float      # sum of all PAID advance payments for this report's client + tax_year
    - advances_count: int
    - final_balance: float            # tax_after_credits - total_advances_paid (negative = refund)
    - balance_type: Literal["due", "refund", "zero"]

  Logic:
  1. Get the report to find client_id and tax_year
  2. Query AdvancePayment WHERE client_id = report.client_id
     AND tax_year = report.tax_year (if advance_payment has tax_year)
     OR created_at year = report.tax_year (fallback)
     AND status = PAID (or equivalent)
  3. Sum amounts
  4. Get tax_after_credits from get_tax_calculation()
  5. Compute final_balance

Add endpoint:
  GET /annual-reports/{report_id}/advances-summary
  Returns AdvancesSummary

### Frontend

Add AdvancesSummary type and annualReportsApi.getAdvancesSummary(reportId).

Add endpoint: annualReportAdvancesSummary: (id) => `/annual-reports/${id}/advances-summary`

Add QK: annualReportAdvancesSummary: (id) => [...base, id, 'advances-summary']

Create component: FinalBalancePanel.tsx
  Displays:
  - Total advances paid
  - Tax liability (from TaxCalculationResult)
  - Final balance with color coding:
      red   = tax due (עוד לתשלום)
      green = refund  (החזר מס)
      gray  = zero
  - advances_count

Wire FinalBalancePanel into AnnualReportDetailDrawer after TaxCalculationPanel.

---

## TASK 4 — Schedule content (annex data)

### Backend

Create model: app/annual_reports/models/annual_report_annex_data.py

  class AnnualReportAnnexData(Base):
      __tablename__ = "annual_report_annex_data"
      id
      annual_report_id  FK → annual_reports.id, index=True
      schedule          Enum(AnnualReportSchedule), nullable=False
      line_number       Integer, nullable=False  # ordering
      data              JSON, nullable=False      # flexible per schedule type
      notes             Text, nullable=True
      created_at
      updated_at

The JSON `data` field stores different shapes per schedule:
  SCHEDULE_B (rental):
    { "property_address": str, "gross_income": float, "expenses": float, "net_income": float }

  SCHEDULE_BET (capital gains):
    { "asset_description": str, "purchase_date": str, "sale_date": str,
      "purchase_price": float, "sale_price": float, "exempt_amount": float, "taxable_gain": float }

  SCHEDULE_GIMMEL (foreign income):
    { "country": str, "income_type": str, "gross_amount": float,
      "foreign_tax_paid": float, "credit_claimed": float }

  SCHEDULE_DALET (depreciation):
    { "asset_name": str, "purchase_date": str, "cost": float,
      "depreciation_rate": float, "annual_depreciation": float, "accumulated": float }

  SCHEDULE_HEH (exempt rental):
    { "property_address": str, "monthly_rent": float, "annual_rent": float,
      "exempt_ceiling": float, "taxable_portion": float }

Write migration: 0009_add_annual_report_annex_data.py

Create repository: app/annual_reports/repositories/annex_data_repository.py
  - list_by_report_and_schedule(report_id, schedule) → list[AnnualReportAnnexData]
  - add_line(report_id, schedule, line_number, data, notes) → AnnualReportAnnexData
  - update_line(line_id, data, notes) → AnnualReportAnnexData
  - delete_line(line_id) → bool

Create schemas: app/annual_reports/schemas/annual_report_annex.py
  - AnnexDataLineResponse
  - AnnexDataAddRequest (schedule, data: dict, notes: Optional[str])
  - AnnexDataUpdateRequest (data: dict, notes: Optional[str])

Add service methods to a new annex_service.py (mixin pattern, same as other services):
  - get_annex_lines(report_id, schedule)
  - add_annex_line(report_id, schedule, data, notes)
  - update_annex_line(report_id, line_id, data, notes)
  - delete_annex_line(report_id, line_id)

Register the annex service as a mixin in AnnualReportService.

Create API router: app/annual_reports/api/annual_report_annex.py
  GET    /annual-reports/{report_id}/annex/{schedule}
  POST   /annual-reports/{report_id}/annex/{schedule}
  PATCH  /annual-reports/{report_id}/annex/{schedule}/{line_id}
  DELETE /annual-reports/{report_id}/annex/{schedule}/{line_id}

Register in __init__.py and main.py.

### Frontend

Add types for AnnexDataLine and each schedule's data shape.

Add API methods: getAnnexLines, addAnnexLine, updateAnnexLine, deleteAnnexLine.

Create component: AnnexDataPanel.tsx
  Props: reportId, schedule, scheduleLabel

  Behavior:
  - Lists existing lines in a table
  - "Add line" button opens an inline form
  - Form fields are determined by the schedule type:
      SCHEDULE_B:     property_address (text), gross_income (number), expenses (number) → auto-computes net_income
      SCHEDULE_BET:   asset_description (text), purchase_date (date), sale_date (date),
                      purchase_price (number), sale_price (number), exempt_amount (number) → auto-computes taxable_gain
      SCHEDULE_GIMMEL: country (text), income_type (text), gross_amount (number),
                       foreign_tax_paid (number), credit_claimed (number)
      SCHEDULE_DALET: asset_name (text), purchase_date (date), cost (number),
                      depreciation_rate (number) → auto-computes annual_depreciation
      SCHEDULE_HEH:   property_address (text), monthly_rent (number) → auto-computes annual_rent,
                      exempt_ceiling (number), taxable_portion (number)
  - Delete button per line
  - Invalidates schedule QK and readiness QK after mutations

Update ScheduleChecklist.tsx:
  - Add an expand/collapse button per schedule entry
  - When expanded, render <AnnexDataPanel reportId={...} schedule={entry.schedule} />
  - Only show expand button for incomplete schedules or schedules with data

Wire into AnnualReportDetailDrawer — the existing "נספחים" section already renders ScheduleChecklist;
the expansion is added inside ScheduleChecklist itself.

---

## TASK 5 — Deadline update UI

### Frontend only (endpoint already exists: POST /annual-reports/{id}/deadline)

Add to annualReportsApi:
  updateDeadline(reportId, payload: { deadline_type: string; custom_deadline_note?: string })

Add endpoint: annualReportDeadline: (id) => `/annual-reports/${id}/deadline`

Create component: DeadlineUpdatePanel.tsx
  Displays current deadline_type and filing_deadline.
  Radio buttons: Standard (30 אפריל) | Extended (31 ינואר — מייצגים) | Custom
  When Custom selected: show text input for custom_deadline_note.
  Save button calls updateDeadline mutation.
  On success: invalidate report detail QK and show toast.

Wire into AnnualReportDetailDrawer as a new DrawerSection titled "מועד הגשה" after the "פרטים" section.

---

## TASK 6 — Auto-advance report on signature

### Backend only

In app/signature_requests/services/signature_service.py (or wherever SignatureRequest.SIGNED transition occurs):

After setting a SignatureRequest to SIGNED status:
1. Check if signature_request.annual_report_id is not None
2. If so, load the linked AnnualReport
3. If the report status is PENDING_CLIENT:
   a. Call AnnualReportService.transition_status(
        report_id=annual_report_id,
        new_status="submitted",
        changed_by=system_user_id,   # use a constant SYSTEM_USER_ID = 0
        changed_by_name="מערכת",
        note="הדוח הוגש אוטומטית לאחר אישור לקוח"
      )
   b. Also set AnnualReportDetail.client_approved_at = now()

Do NOT break the existing signature flow if the annual_report_id is None.
Wrap in try/except so a failure here does not prevent the signature from being marked SIGNED.

---

## VALIDATION

After all tasks:

1. Run: alembic upgrade head — must succeed with no errors
2. Run: cd backend && python -c "from app.annual_reports.services.tax_engine import calculate_tax; r = calculate_tax(387400); print(r)" — must print a result
3. Run: npm run typecheck — must pass with 0 errors
4. Run: npm run lint — must pass with 0 warnings
5. Run: pytest -q tests/ -k "annual_report or financial or tax_engine or readiness" — existing passing tests must still pass