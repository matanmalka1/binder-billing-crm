# 🚀 API Contract & Documentation
**Last Updated:** 2026-03-23

---
## GET `/`
**Summary:** Root

### 📤 Success Response (200)
```json
{
  "service": "binder-billing-crm",
  "status": "running"
}
```

---

## GET `/info`
**Summary:** Info

### 📤 Success Response (200)
```json
{
  "app": "Binder Billing CRM",
  "env": "development"
}
```

---

## GET `/health`
**Summary:** Health Check

### 📤 Success Response (200)
```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

## POST `/api/v1/auth/login`
**Summary:** Login

### 📥 Request Body (JSON)
```json
{
  "email": "user@example.com",
  "password": "string",
  "rememberMe": false
}
```

### 📤 Success Response (200)
```json
{
  "token": "string",
  "user": {
    "id": 1,
    "full_name": "string",
    "role": "advisor",
    "email": "user@example.com"
  }
}
```

---

## POST `/api/v1/auth/logout`
**Summary:** Logout

---

## GET `/api/v1/annual-reports/{report_id}/annex/{schedule}`
**Summary:** List Annex Lines

### 📤 Success Response (200)
```json
[
  {
    "id": 1,
    "annual_report_id": 1,
    "schedule": "schedule_b",
    "line_number": 1,
    "data": {
      "key": "value"
    },
    "data_version": 1,
    "notes": "string",
    "created_at": "2026-01-02T03:04:05Z",
    "updated_at": "2026-01-02T03:04:05Z"
  }
]
```

---

## POST `/api/v1/annual-reports/{report_id}/annex/{schedule}`
**Summary:** Add Annex Line

### 📥 Request Body (JSON)
```json
{
  "data": {
    "key": "value"
  },
  "notes": "string"
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "annual_report_id": 1,
  "schedule": "schedule_b",
  "line_number": 1,
  "data": {
    "key": "value"
  },
  "data_version": 1,
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## PATCH `/api/v1/annual-reports/{report_id}/annex/{schedule}/{line_id}`
**Summary:** Update Annex Line

### 📥 Request Body (JSON)
```json
{
  "data": {
    "key": "value"
  },
  "notes": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "annual_report_id": 1,
  "schedule": "schedule_b",
  "line_number": 1,
  "data": {
    "key": "value"
  },
  "data_version": 1,
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## DELETE `/api/v1/annual-reports/{report_id}/annex/{schedule}/{line_id}`
**Summary:** Delete Annex Line

---

## GET `/api/v1/annual-reports/{report_id}/details`
**Summary:** Get Annual Report Detail

### 📤 Success Response (200)
```json
{
  "report_id": 1,
  "pension_contribution": "123.45",
  "donation_amount": "123.45",
  "other_credits": "123.45",
  "client_approved_at": "2026-01-02T03:04:05Z",
  "internal_notes": "string",
  "amendment_reason": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## PATCH `/api/v1/annual-reports/{report_id}/details`
**Summary:** Update Annual Report Detail

### 📥 Request Body (JSON)
```json
{
  "pension_contribution": "123.45",
  "donation_amount": "123.45",
  "other_credits": "123.45",
  "client_approved_at": "2026-01-02T03:04:05Z",
  "internal_notes": "string",
  "amendment_reason": "string"
}
```

### 📤 Success Response (200)
```json
{
  "report_id": 1,
  "pension_contribution": "123.45",
  "donation_amount": "123.45",
  "other_credits": "123.45",
  "client_approved_at": "2026-01-02T03:04:05Z",
  "internal_notes": "string",
  "amendment_reason": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## GET `/api/v1/annual-reports/{report_id}/financials`
**Summary:** Get Financial Summary

### 📤 Success Response (200)
```json
{
  "annual_report_id": 1,
  "total_income": "123.45",
  "gross_expenses": "123.45",
  "recognized_expenses": "123.45",
  "taxable_income": "123.45",
  "income_lines": [
    {
      "id": 1,
      "annual_report_id": 1,
      "source_type": "business",
      "amount": "123.45",
      "description": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "updated_at": "2026-01-02T03:04:05Z"
    }
  ],
  "expense_lines": [
    {
      "id": 1,
      "annual_report_id": 1,
      "category": "office_rent",
      "amount": "123.45",
      "recognition_rate": "123.45",
      "recognized_amount": "123.45",
      "supporting_document_ref": "string",
      "supporting_document_id": 1,
      "supporting_document_filename": "string",
      "description": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "updated_at": "2026-01-02T03:04:05Z"
    }
  ]
}
```

---

## GET `/api/v1/annual-reports/{report_id}/tax-calculation`
**Summary:** Get Tax Calculation

### 📤 Success Response (200)
```json
{
  "taxable_income": "123.45",
  "pension_deduction": "123.45",
  "tax_before_credits": "123.45",
  "credit_points_value": "123.45",
  "donation_credit": "123.45",
  "other_credits": "123.45",
  "tax_after_credits": "123.45",
  "net_profit": "123.45",
  "effective_rate": 1.0,
  "national_insurance": {
    "base_amount": "123.45",
    "high_amount": "123.45",
    "total": "123.45"
  },
  "brackets": [
    {
      "rate": 1.0,
      "from_amount": "123.45",
      "to_amount": "123.45",
      "taxable_in_bracket": "123.45",
      "tax_in_bracket": "123.45"
    }
  ],
  "total_liability": "123.45",
  "total_credit_points": 0.0
}
```

---

## GET `/api/v1/annual-reports/{report_id}/advances-summary`
**Summary:** Get Advances Summary

### 📤 Success Response (200)
```json
{
  "total_advances_paid": "123.45",
  "advances_count": 1,
  "final_balance": "123.45",
  "balance_type": "due"
}
```

---

## GET `/api/v1/annual-reports/{report_id}/readiness`
**Summary:** Get Readiness Check

### 📤 Success Response (200)
```json
{
  "annual_report_id": 1,
  "is_ready": true,
  "issues": [
    "string"
  ],
  "completion_pct": 1.0
}
```

---

## POST `/api/v1/annual-reports/{report_id}/income`
**Summary:** Add Income Line

### 📥 Request Body (JSON)
```json
{
  "source_type": "business",
  "amount": "123.45",
  "description": "string"
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "annual_report_id": 1,
  "source_type": "business",
  "amount": "123.45",
  "description": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## PATCH `/api/v1/annual-reports/{report_id}/income/{line_id}`
**Summary:** Update Income Line

### 📥 Request Body (JSON)
```json
{
  "source_type": "business",
  "amount": "123.45",
  "description": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "annual_report_id": 1,
  "source_type": "business",
  "amount": "123.45",
  "description": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## DELETE `/api/v1/annual-reports/{report_id}/income/{line_id}`
**Summary:** Delete Income Line

---

## POST `/api/v1/annual-reports/{report_id}/expenses`
**Summary:** Add Expense Line

### 📥 Request Body (JSON)
```json
{
  "category": "office_rent",
  "amount": "123.45",
  "description": "string",
  "recognition_rate": "123.45",
  "supporting_document_ref": "string",
  "supporting_document_id": 1
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "annual_report_id": 1,
  "category": "office_rent",
  "amount": "123.45",
  "recognition_rate": "123.45",
  "recognized_amount": "123.45",
  "supporting_document_ref": "string",
  "supporting_document_id": 1,
  "supporting_document_filename": "string",
  "description": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## PATCH `/api/v1/annual-reports/{report_id}/expenses/{line_id}`
**Summary:** Update Expense Line

### 📥 Request Body (JSON)
```json
{
  "category": "office_rent",
  "amount": "123.45",
  "description": "string",
  "recognition_rate": "123.45",
  "supporting_document_ref": "string",
  "supporting_document_id": 1
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "annual_report_id": 1,
  "category": "office_rent",
  "amount": "123.45",
  "recognition_rate": "123.45",
  "recognized_amount": "123.45",
  "supporting_document_ref": "string",
  "supporting_document_id": 1,
  "supporting_document_filename": "string",
  "description": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## DELETE `/api/v1/annual-reports/{report_id}/expenses/{line_id}`
**Summary:** Delete Expense Line

---

## POST `/api/v1/annual-reports`
**Summary:** Create Annual Report

### 📥 Request Body (JSON)
```json
{
  "business_id": 1,
  "tax_year": 1,
  "client_type": "individual",
  "deadline_type": "standard",
  "assigned_to": 1,
  "notes": "string",
  "submission_method": "online",
  "extension_reason": "military_service",
  "has_rental_income": false,
  "has_capital_gains": false,
  "has_foreign_income": false,
  "has_depreciation": false,
  "has_exempt_rental": false
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "business_id": 1,
  "tax_year": 1,
  "client_type": "individual",
  "form_type": "1301",
  "status": "not_started",
  "deadline_type": "standard",
  "filing_deadline": "2026-01-02T03:04:05Z",
  "custom_deadline_note": "string",
  "submitted_at": "2026-01-02T03:04:05Z",
  "ita_reference": "string",
  "assessment_amount": "123.45",
  "refund_due": "123.45",
  "tax_due": "123.45",
  "has_rental_income": false,
  "has_capital_gains": false,
  "has_foreign_income": false,
  "has_depreciation": false,
  "has_exempt_rental": false,
  "submission_method": "online",
  "extension_reason": "military_service",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z",
  "assigned_to": 1,
  "created_by": 1,
  "available_actions": [
    {
      "key": "value"
    }
  ],
  "schedules": [
    {
      "id": 1,
      "annual_report_id": 1,
      "schedule": "schedule_b",
      "is_required": true,
      "is_complete": true,
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "completed_at": "2026-01-02T03:04:05Z",
      "completed_by": 1
    }
  ],
  "status_history": [
    {
      "id": 1,
      "annual_report_id": 1,
      "from_status": "not_started",
      "to_status": "not_started",
      "changed_by": 1,
      "note": "string",
      "occurred_at": "2026-01-02T03:04:05Z"
    }
  ],
  "pension_contribution": "123.45",
  "donation_amount": "123.45",
  "other_credits": "123.45",
  "client_approved_at": "2026-01-02T03:04:05Z",
  "internal_notes": "string",
  "amendment_reason": "string",
  "tax_refund_amount": 1.0,
  "tax_due_amount": 1.0,
  "total_income": "123.45",
  "total_expenses": "123.45",
  "taxable_income": "123.45",
  "profit": "123.45",
  "final_balance": "123.45"
}
```

---

## GET `/api/v1/annual-reports`
**Summary:** List Annual Reports

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "tax_year": 1,
      "client_type": "individual",
      "form_type": "1301",
      "status": "not_started",
      "deadline_type": "standard",
      "filing_deadline": "2026-01-02T03:04:05Z",
      "custom_deadline_note": "string",
      "submitted_at": "2026-01-02T03:04:05Z",
      "ita_reference": "string",
      "assessment_amount": "123.45",
      "refund_due": "123.45",
      "tax_due": "123.45",
      "has_rental_income": false,
      "has_capital_gains": false,
      "has_foreign_income": false,
      "has_depreciation": false,
      "has_exempt_rental": false,
      "submission_method": "online",
      "extension_reason": "military_service",
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "updated_at": "2026-01-02T03:04:05Z",
      "assigned_to": 1,
      "created_by": 1,
      "available_actions": [
        {
          "key": "value"
        }
      ]
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/annual-reports/kanban/view`
**Summary:** Get Kanban View

### 📤 Success Response (200)
```json
{
  "stages": [
    {
      "stage": "material_collection",
      "reports": [
        {
          "id": 1,
          "business_id": 1,
          "business_name": "string",
          "tax_year": 1,
          "days_until_due": 1
        }
      ]
    }
  ]
}
```

---

## GET `/api/v1/annual-reports/overdue`
**Summary:** List Overdue

### 📤 Success Response (200)
```json
[
  {
    "id": 1,
    "business_id": 1,
    "tax_year": 1,
    "client_type": "individual",
    "form_type": "1301",
    "status": "not_started",
    "deadline_type": "standard",
    "filing_deadline": "2026-01-02T03:04:05Z",
    "custom_deadline_note": "string",
    "submitted_at": "2026-01-02T03:04:05Z",
    "ita_reference": "string",
    "assessment_amount": "123.45",
    "refund_due": "123.45",
    "tax_due": "123.45",
    "has_rental_income": false,
    "has_capital_gains": false,
    "has_foreign_income": false,
    "has_depreciation": false,
    "has_exempt_rental": false,
    "submission_method": "online",
    "extension_reason": "military_service",
    "notes": "string",
    "created_at": "2026-01-02T03:04:05Z",
    "updated_at": "2026-01-02T03:04:05Z",
    "assigned_to": 1,
    "created_by": 1,
    "available_actions": [
      {
        "key": "value"
      }
    ]
  }
]
```

---

## GET `/api/v1/annual-reports/{report_id}`
**Summary:** Get Annual Report

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "tax_year": 1,
  "client_type": "individual",
  "form_type": "1301",
  "status": "not_started",
  "deadline_type": "standard",
  "filing_deadline": "2026-01-02T03:04:05Z",
  "custom_deadline_note": "string",
  "submitted_at": "2026-01-02T03:04:05Z",
  "ita_reference": "string",
  "assessment_amount": "123.45",
  "refund_due": "123.45",
  "tax_due": "123.45",
  "has_rental_income": false,
  "has_capital_gains": false,
  "has_foreign_income": false,
  "has_depreciation": false,
  "has_exempt_rental": false,
  "submission_method": "online",
  "extension_reason": "military_service",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z",
  "assigned_to": 1,
  "created_by": 1,
  "available_actions": [
    {
      "key": "value"
    }
  ],
  "schedules": [
    {
      "id": 1,
      "annual_report_id": 1,
      "schedule": "schedule_b",
      "is_required": true,
      "is_complete": true,
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "completed_at": "2026-01-02T03:04:05Z",
      "completed_by": 1
    }
  ],
  "status_history": [
    {
      "id": 1,
      "annual_report_id": 1,
      "from_status": "not_started",
      "to_status": "not_started",
      "changed_by": 1,
      "note": "string",
      "occurred_at": "2026-01-02T03:04:05Z"
    }
  ],
  "pension_contribution": "123.45",
  "donation_amount": "123.45",
  "other_credits": "123.45",
  "client_approved_at": "2026-01-02T03:04:05Z",
  "internal_notes": "string",
  "amendment_reason": "string",
  "tax_refund_amount": 1.0,
  "tax_due_amount": 1.0,
  "total_income": "123.45",
  "total_expenses": "123.45",
  "taxable_income": "123.45",
  "profit": "123.45",
  "final_balance": "123.45"
}
```

---

## DELETE `/api/v1/annual-reports/{report_id}`
**Summary:** Delete Annual Report

---

## POST `/api/v1/annual-reports/{report_id}/amend`
**Summary:** Amend Annual Report

### 📥 Request Body (JSON)
```json
{
  "reason": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "tax_year": 1,
  "client_type": "individual",
  "form_type": "1301",
  "status": "not_started",
  "deadline_type": "standard",
  "filing_deadline": "2026-01-02T03:04:05Z",
  "custom_deadline_note": "string",
  "submitted_at": "2026-01-02T03:04:05Z",
  "ita_reference": "string",
  "assessment_amount": "123.45",
  "refund_due": "123.45",
  "tax_due": "123.45",
  "has_rental_income": false,
  "has_capital_gains": false,
  "has_foreign_income": false,
  "has_depreciation": false,
  "has_exempt_rental": false,
  "submission_method": "online",
  "extension_reason": "military_service",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z",
  "assigned_to": 1,
  "created_by": 1,
  "available_actions": [
    {
      "key": "value"
    }
  ],
  "schedules": [
    {
      "id": 1,
      "annual_report_id": 1,
      "schedule": "schedule_b",
      "is_required": true,
      "is_complete": true,
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "completed_at": "2026-01-02T03:04:05Z",
      "completed_by": 1
    }
  ],
  "status_history": [
    {
      "id": 1,
      "annual_report_id": 1,
      "from_status": "not_started",
      "to_status": "not_started",
      "changed_by": 1,
      "note": "string",
      "occurred_at": "2026-01-02T03:04:05Z"
    }
  ],
  "pension_contribution": "123.45",
  "donation_amount": "123.45",
  "other_credits": "123.45",
  "client_approved_at": "2026-01-02T03:04:05Z",
  "internal_notes": "string",
  "amendment_reason": "string",
  "tax_refund_amount": 1.0,
  "tax_due_amount": 1.0,
  "total_income": "123.45",
  "total_expenses": "123.45",
  "taxable_income": "123.45",
  "profit": "123.45",
  "final_balance": "123.45"
}
```

---

## POST `/api/v1/annual-reports/{report_id}/schedules`
**Summary:** Add Schedule

### 📥 Request Body (JSON)
```json
{
  "schedule": "schedule_b",
  "notes": "string"
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "annual_report_id": 1,
  "schedule": "schedule_b",
  "is_required": true,
  "is_complete": true,
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "completed_at": "2026-01-02T03:04:05Z",
  "completed_by": 1
}
```

---

## GET `/api/v1/annual-reports/{report_id}/schedules`
**Summary:** List Schedules

### 📤 Success Response (200)
```json
[
  {
    "id": 1,
    "annual_report_id": 1,
    "schedule": "schedule_b",
    "is_required": true,
    "is_complete": true,
    "notes": "string",
    "created_at": "2026-01-02T03:04:05Z",
    "completed_at": "2026-01-02T03:04:05Z",
    "completed_by": 1
  }
]
```

---

## POST `/api/v1/annual-reports/{report_id}/schedules/complete`
**Summary:** Complete Schedule

### 📥 Request Body (JSON)
```json
{
  "schedule": "schedule_b"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "annual_report_id": 1,
  "schedule": "schedule_b",
  "is_required": true,
  "is_complete": true,
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "completed_at": "2026-01-02T03:04:05Z",
  "completed_by": 1
}
```

---

## POST `/api/v1/annual-reports/{report_id}/transition`
**Summary:** Transition Stage

### 📥 Request Body (JSON)
```json
{
  "to_stage": "material_collection"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "tax_year": 1,
  "client_type": "individual",
  "form_type": "1301",
  "status": "not_started",
  "deadline_type": "standard",
  "filing_deadline": "2026-01-02T03:04:05Z",
  "custom_deadline_note": "string",
  "submitted_at": "2026-01-02T03:04:05Z",
  "ita_reference": "string",
  "assessment_amount": "123.45",
  "refund_due": "123.45",
  "tax_due": "123.45",
  "has_rental_income": false,
  "has_capital_gains": false,
  "has_foreign_income": false,
  "has_depreciation": false,
  "has_exempt_rental": false,
  "submission_method": "online",
  "extension_reason": "military_service",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z",
  "assigned_to": 1,
  "created_by": 1,
  "available_actions": [
    {
      "key": "value"
    }
  ],
  "schedules": [
    {
      "id": 1,
      "annual_report_id": 1,
      "schedule": "schedule_b",
      "is_required": true,
      "is_complete": true,
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "completed_at": "2026-01-02T03:04:05Z",
      "completed_by": 1
    }
  ],
  "status_history": [
    {
      "id": 1,
      "annual_report_id": 1,
      "from_status": "not_started",
      "to_status": "not_started",
      "changed_by": 1,
      "note": "string",
      "occurred_at": "2026-01-02T03:04:05Z"
    }
  ],
  "pension_contribution": "123.45",
  "donation_amount": "123.45",
  "other_credits": "123.45",
  "client_approved_at": "2026-01-02T03:04:05Z",
  "internal_notes": "string",
  "amendment_reason": "string",
  "tax_refund_amount": 1.0,
  "tax_due_amount": 1.0,
  "total_income": "123.45",
  "total_expenses": "123.45",
  "taxable_income": "123.45",
  "profit": "123.45",
  "final_balance": "123.45"
}
```

---

## POST `/api/v1/annual-reports/{report_id}/status`
**Summary:** Transition Status

### 📥 Request Body (JSON)
```json
{
  "status": "not_started",
  "note": "string",
  "ita_reference": "string",
  "assessment_amount": "123.45",
  "refund_due": "123.45",
  "tax_due": "123.45"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "tax_year": 1,
  "client_type": "individual",
  "form_type": "1301",
  "status": "not_started",
  "deadline_type": "standard",
  "filing_deadline": "2026-01-02T03:04:05Z",
  "custom_deadline_note": "string",
  "submitted_at": "2026-01-02T03:04:05Z",
  "ita_reference": "string",
  "assessment_amount": "123.45",
  "refund_due": "123.45",
  "tax_due": "123.45",
  "has_rental_income": false,
  "has_capital_gains": false,
  "has_foreign_income": false,
  "has_depreciation": false,
  "has_exempt_rental": false,
  "submission_method": "online",
  "extension_reason": "military_service",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z",
  "assigned_to": 1,
  "created_by": 1,
  "available_actions": [
    {
      "key": "value"
    }
  ]
}
```

---

## POST `/api/v1/annual-reports/{report_id}/submit`
**Summary:** Submit Report

### 📥 Request Body (JSON)
```json
{
  "submitted_at": "2026-01-02T03:04:05Z",
  "ita_reference": "string",
  "submission_method": "online",
  "note": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "tax_year": 1,
  "client_type": "individual",
  "form_type": "1301",
  "status": "not_started",
  "deadline_type": "standard",
  "filing_deadline": "2026-01-02T03:04:05Z",
  "custom_deadline_note": "string",
  "submitted_at": "2026-01-02T03:04:05Z",
  "ita_reference": "string",
  "assessment_amount": "123.45",
  "refund_due": "123.45",
  "tax_due": "123.45",
  "has_rental_income": false,
  "has_capital_gains": false,
  "has_foreign_income": false,
  "has_depreciation": false,
  "has_exempt_rental": false,
  "submission_method": "online",
  "extension_reason": "military_service",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z",
  "assigned_to": 1,
  "created_by": 1,
  "available_actions": [
    {
      "key": "value"
    }
  ],
  "schedules": [
    {
      "id": 1,
      "annual_report_id": 1,
      "schedule": "schedule_b",
      "is_required": true,
      "is_complete": true,
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "completed_at": "2026-01-02T03:04:05Z",
      "completed_by": 1
    }
  ],
  "status_history": [
    {
      "id": 1,
      "annual_report_id": 1,
      "from_status": "not_started",
      "to_status": "not_started",
      "changed_by": 1,
      "note": "string",
      "occurred_at": "2026-01-02T03:04:05Z"
    }
  ],
  "pension_contribution": "123.45",
  "donation_amount": "123.45",
  "other_credits": "123.45",
  "client_approved_at": "2026-01-02T03:04:05Z",
  "internal_notes": "string",
  "amendment_reason": "string",
  "tax_refund_amount": 1.0,
  "tax_due_amount": 1.0,
  "total_income": "123.45",
  "total_expenses": "123.45",
  "taxable_income": "123.45",
  "profit": "123.45",
  "final_balance": "123.45"
}
```

---

## POST `/api/v1/annual-reports/{report_id}/deadline`
**Summary:** Update Deadline

### 📥 Request Body (JSON)
```json
{
  "deadline_type": "standard",
  "custom_deadline_note": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "tax_year": 1,
  "client_type": "individual",
  "form_type": "1301",
  "status": "not_started",
  "deadline_type": "standard",
  "filing_deadline": "2026-01-02T03:04:05Z",
  "custom_deadline_note": "string",
  "submitted_at": "2026-01-02T03:04:05Z",
  "ita_reference": "string",
  "assessment_amount": "123.45",
  "refund_due": "123.45",
  "tax_due": "123.45",
  "has_rental_income": false,
  "has_capital_gains": false,
  "has_foreign_income": false,
  "has_depreciation": false,
  "has_exempt_rental": false,
  "submission_method": "online",
  "extension_reason": "military_service",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z",
  "assigned_to": 1,
  "created_by": 1,
  "available_actions": [
    {
      "key": "value"
    }
  ]
}
```

---

## GET `/api/v1/annual-reports/{report_id}/history`
**Summary:** Get Status History

### 📤 Success Response (200)
```json
[
  {
    "id": 1,
    "annual_report_id": 1,
    "from_status": "not_started",
    "to_status": "not_started",
    "changed_by": 1,
    "note": "string",
    "occurred_at": "2026-01-02T03:04:05Z"
  }
]
```

---

## GET `/api/v1/businesses/{business_id}/annual-reports`
**Summary:** List Business Reports

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "tax_year": 1,
      "client_type": "individual",
      "form_type": "1301",
      "status": "not_started",
      "deadline_type": "standard",
      "filing_deadline": "2026-01-02T03:04:05Z",
      "custom_deadline_note": "string",
      "submitted_at": "2026-01-02T03:04:05Z",
      "ita_reference": "string",
      "assessment_amount": "123.45",
      "refund_due": "123.45",
      "tax_due": "123.45",
      "has_rental_income": false,
      "has_capital_gains": false,
      "has_foreign_income": false,
      "has_depreciation": false,
      "has_exempt_rental": false,
      "submission_method": "online",
      "extension_reason": "military_service",
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "updated_at": "2026-01-02T03:04:05Z",
      "assigned_to": 1,
      "created_by": 1,
      "available_actions": [
        {
          "key": "value"
        }
      ]
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/tax-year/{tax_year}/reports`
**Summary:** List Season Reports

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "tax_year": 1,
      "client_type": "individual",
      "form_type": "1301",
      "status": "not_started",
      "deadline_type": "standard",
      "filing_deadline": "2026-01-02T03:04:05Z",
      "custom_deadline_note": "string",
      "submitted_at": "2026-01-02T03:04:05Z",
      "ita_reference": "string",
      "assessment_amount": "123.45",
      "refund_due": "123.45",
      "tax_due": "123.45",
      "has_rental_income": false,
      "has_capital_gains": false,
      "has_foreign_income": false,
      "has_depreciation": false,
      "has_exempt_rental": false,
      "submission_method": "online",
      "extension_reason": "military_service",
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "updated_at": "2026-01-02T03:04:05Z",
      "assigned_to": 1,
      "created_by": 1,
      "available_actions": [
        {
          "key": "value"
        }
      ]
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/tax-year/{tax_year}/summary`
**Summary:** Get Season Summary

### 📤 Success Response (200)
```json
{
  "tax_year": 1,
  "total": 1,
  "not_started": 1,
  "collecting_docs": 1,
  "docs_complete": 1,
  "in_preparation": 1,
  "pending_client": 1,
  "submitted": 1,
  "accepted": 1,
  "assessment_issued": 1,
  "objection_filed": 1,
  "closed": 1,
  "amended": 0,
  "completion_rate": 1.0,
  "overdue_count": 1
}
```

---

## GET `/api/v1/annual-reports/{report_id}/export/pdf`
**Summary:** Export Annual Report Pdf

### 📤 Success Response (200)
```text
Binary file response (download stream)

Variant 1 (always)
Content-Type: application/pdf
Content-Disposition: attachment; filename="annual_report_123_2026.pdf"

Body: <binary bytes>
```

---

## POST `/api/v1/tax-deadlines`
**Summary:** Create Tax Deadline

### 📥 Request Body (JSON)
```json
{
  "business_id": 1,
  "deadline_type": "vat",
  "due_date": "2026-01-15",
  "period": "string",
  "payment_amount": "123.45",
  "description": "string"
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "deadline_type": "vat",
  "period": "string",
  "due_date": "2026-01-15",
  "status": "pending",
  "payment_amount": "123.45",
  "description": "string",
  "completed_at": "2026-01-02T03:04:05Z",
  "completed_by": 1,
  "advance_payment_id": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "available_actions": [
    {
      "key": "value"
    }
  ]
}
```

---

## GET `/api/v1/tax-deadlines`
**Summary:** List Tax Deadlines

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "business_name": "string",
      "deadline_type": "vat",
      "period": "string",
      "due_date": "2026-01-15",
      "status": "pending",
      "payment_amount": "123.45",
      "description": "string",
      "completed_at": "2026-01-02T03:04:05Z",
      "completed_by": 1,
      "advance_payment_id": 1,
      "created_at": "2026-01-02T03:04:05Z",
      "available_actions": [
        {
          "key": "value"
        }
      ]
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/tax-deadlines/{deadline_id}`
**Summary:** Get Tax Deadline

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "deadline_type": "vat",
  "period": "string",
  "due_date": "2026-01-15",
  "status": "pending",
  "payment_amount": "123.45",
  "description": "string",
  "completed_at": "2026-01-02T03:04:05Z",
  "completed_by": 1,
  "advance_payment_id": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "available_actions": [
    {
      "key": "value"
    }
  ]
}
```

---

## PUT `/api/v1/tax-deadlines/{deadline_id}`
**Summary:** Update Tax Deadline

### 📥 Request Body (JSON)
```json
{
  "deadline_type": "vat",
  "due_date": "2026-01-15",
  "period": "string",
  "payment_amount": "123.45",
  "description": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "deadline_type": "vat",
  "period": "string",
  "due_date": "2026-01-15",
  "status": "pending",
  "payment_amount": "123.45",
  "description": "string",
  "completed_at": "2026-01-02T03:04:05Z",
  "completed_by": 1,
  "advance_payment_id": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "available_actions": [
    {
      "key": "value"
    }
  ]
}
```

---

## DELETE `/api/v1/tax-deadlines/{deadline_id}`
**Summary:** Delete Tax Deadline

---

## POST `/api/v1/tax-deadlines/{deadline_id}/complete`
**Summary:** Complete Tax Deadline

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "deadline_type": "vat",
  "period": "string",
  "due_date": "2026-01-15",
  "status": "pending",
  "payment_amount": "123.45",
  "description": "string",
  "completed_at": "2026-01-02T03:04:05Z",
  "completed_by": 1,
  "advance_payment_id": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "available_actions": [
    {
      "key": "value"
    }
  ]
}
```

---

## POST `/api/v1/tax-deadlines/generate`
**Summary:** Generate Deadlines

### 📥 Request Body (JSON)
```json
{
  "business_id": 1,
  "year": 1
}
```

### 📤 Success Response (201)
```json
{
  "created_count": 1
}
```

---

## GET `/api/v1/tax-deadlines/timeline`
**Summary:** Get Timeline

### 📤 Success Response (200)
```json
[
  {
    "id": 1,
    "business_id": 1,
    "deadline_type": "vat",
    "period": "string",
    "due_date": "2026-01-15",
    "status": "pending",
    "days_remaining": 1,
    "milestone_label": "string",
    "payment_amount": "123.45"
  }
]
```

---

## GET `/api/v1/tax-deadlines/dashboard/urgent`
**Summary:** Get Dashboard Deadlines

### 📤 Success Response (200)
```json
{
  "urgent": [
    {
      "id": 1,
      "business_id": 1,
      "business_name": "string",
      "deadline_type": "vat",
      "due_date": "2026-01-15",
      "urgency": "overdue",
      "days_remaining": 1,
      "payment_amount": "123.45"
    }
  ],
  "upcoming": [
    {
      "id": 1,
      "business_id": 1,
      "business_name": "string",
      "deadline_type": "vat",
      "period": "string",
      "due_date": "2026-01-15",
      "status": "pending",
      "payment_amount": "123.45",
      "description": "string",
      "completed_at": "2026-01-02T03:04:05Z",
      "completed_by": 1,
      "advance_payment_id": 1,
      "created_at": "2026-01-02T03:04:05Z",
      "available_actions": [
        {
          "key": "value"
        }
      ]
    }
  ]
}
```

---

## POST `/api/v1/businesses/{business_id}/authority-contacts`
**Summary:** Create Authority Contact

### 📥 Request Body (JSON)
```json
{
  "contact_type": "assessing_officer",
  "name": "string",
  "office": "string",
  "phone": "string",
  "email": "user@example.com",
  "notes": "string"
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "business_id": 1,
  "contact_type": "assessing_officer",
  "name": "string",
  "office": "string",
  "phone": "string",
  "email": "string",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## GET `/api/v1/businesses/{business_id}/authority-contacts`
**Summary:** List Authority Contacts

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "contact_type": "assessing_officer",
      "name": "string",
      "office": "string",
      "phone": "string",
      "email": "string",
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "updated_at": "2026-01-02T03:04:05Z"
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/businesses/authority-contacts/{contact_id}`
**Summary:** Get Authority Contact

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "contact_type": "assessing_officer",
  "name": "string",
  "office": "string",
  "phone": "string",
  "email": "string",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## PATCH `/api/v1/businesses/authority-contacts/{contact_id}`
**Summary:** Update Authority Contact

### 📥 Request Body (JSON)
```json
{
  "contact_type": "assessing_officer",
  "name": "string",
  "office": "string",
  "phone": "string",
  "email": "user@example.com",
  "notes": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "contact_type": "assessing_officer",
  "name": "string",
  "office": "string",
  "phone": "string",
  "email": "string",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## DELETE `/api/v1/businesses/authority-contacts/{contact_id}`
**Summary:** Delete Authority Contact

---

## GET `/api/v1/dashboard/tax-submissions`
**Summary:** Get Tax Submission Widget

### 📤 Success Response (200)
```json
{
  "tax_year": 1,
  "total_clients": 1,
  "reports_submitted": 1,
  "reports_in_progress": 1,
  "reports_not_started": 1,
  "submission_percentage": 1.0,
  "total_refund_due": "123.45",
  "total_tax_due": "123.45"
}
```

---

## GET `/api/v1/clients/export`
**Summary:** Export Clients

### 📤 Success Response (200)
```text
Binary file response (download stream)

Variant 1 (always)
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="clients_export_20260323_120000.xlsx"

Body: <binary bytes>
```

---

## GET `/api/v1/clients/template`
**Summary:** Download Client Template

### 📤 Success Response (200)
```text
Binary file response (download stream)

Variant 1 (always)
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="clients_template_20260323_120000.xlsx"

Body: <binary bytes>
```

---

## POST `/api/v1/clients/import`
**Summary:** Import Clients From Excel

### 📤 Success Response (200)
```json
{
  "created": 3,
  "total_rows": 5,
  "errors": [
    {
      "row": 4,
      "error": "שם מלא ומספר מזהה הם שדות חובה"
    },
    {
      "row": 5,
      "error": "Client with this id number already exists"
    }
  ]
}
```

---

## POST `/api/v1/clients`
**Summary:** Create Client

### 📥 Request Body (JSON)
```json
{
  "full_name": "string",
  "id_number": "string",
  "id_number_type": "individual",
  "phone": "string",
  "email": "user@example.com",
  "address_street": "string",
  "address_building_number": "string",
  "address_apartment": "string",
  "address_city": "string",
  "address_zip_code": "string"
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "full_name": "string",
  "id_number": "string",
  "id_number_type": "individual",
  "phone": "string",
  "email": "string",
  "address_street": "string",
  "address_building_number": "string",
  "address_apartment": "string",
  "address_city": "string",
  "address_zip_code": "string",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## GET `/api/v1/clients`
**Summary:** List Clients

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "full_name": "string",
      "id_number": "string",
      "id_number_type": "individual",
      "phone": "string",
      "email": "string",
      "address_street": "string",
      "address_building_number": "string",
      "address_apartment": "string",
      "address_city": "string",
      "address_zip_code": "string",
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "updated_at": "2026-01-02T03:04:05Z"
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/clients/{client_id}`
**Summary:** Get Client

### 📤 Success Response (200)
```json
{
  "id": 1,
  "full_name": "string",
  "id_number": "string",
  "id_number_type": "individual",
  "phone": "string",
  "email": "string",
  "address_street": "string",
  "address_building_number": "string",
  "address_apartment": "string",
  "address_city": "string",
  "address_zip_code": "string",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## PATCH `/api/v1/clients/{client_id}`
**Summary:** Update Client

### 📥 Request Body (JSON)
```json
{
  "full_name": "string",
  "phone": "string",
  "email": "user@example.com",
  "address_street": "string",
  "address_building_number": "string",
  "address_apartment": "string",
  "address_city": "string",
  "address_zip_code": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "full_name": "string",
  "id_number": "string",
  "id_number_type": "individual",
  "phone": "string",
  "email": "string",
  "address_street": "string",
  "address_building_number": "string",
  "address_apartment": "string",
  "address_city": "string",
  "address_zip_code": "string",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## DELETE `/api/v1/clients/{client_id}`
**Summary:** Delete Client

---

## GET `/api/v1/clients/conflict/{id_number}`
**Summary:** Get Conflict Info

### 📤 Success Response (200)
```json
{
  "id_number": "string",
  "active_clients": [
    {
      "id": 1,
      "full_name": "string",
      "id_number": "string"
    }
  ],
  "deleted_clients": [
    {
      "id": 1,
      "full_name": "string",
      "id_number": "string",
      "deleted_at": "2026-01-02T03:04:05Z"
    }
  ]
}
```

---

## POST `/api/v1/clients/{client_id}/restore`
**Summary:** Restore Client

### 📤 Success Response (200)
```json
{
  "id": 1,
  "full_name": "string",
  "id_number": "string",
  "id_number_type": "individual",
  "phone": "string",
  "email": "string",
  "address_street": "string",
  "address_building_number": "string",
  "address_apartment": "string",
  "address_city": "string",
  "address_zip_code": "string",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## GET `/api/v1/businesses/{business_id}/status-card`
**Summary:** Get Business Status Card

### 📤 Success Response (200)
```json
{
  "client_id": 1,
  "business_id": 1,
  "year": 1,
  "vat": {
    "net_vat_total": "123.45",
    "periods_filed": 1,
    "periods_total": 1,
    "latest_period": "string"
  },
  "annual_report": {
    "status": "string",
    "form_type": "string",
    "filing_deadline": "string",
    "refund_due": "123.45",
    "tax_due": "123.45"
  },
  "charges": {
    "total_outstanding": "123.45",
    "unpaid_count": 1
  },
  "advance_payments": {
    "total_paid": "123.45",
    "count": 1
  },
  "binders": {
    "active_count": 1,
    "in_office_count": 1
  },
  "documents": {
    "total_count": 1,
    "present_count": 1
  }
}
```

---

## GET `/api/v1/businesses/{business_id}/binders`
**Summary:** List Business Binders

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "client_id": 1,
      "client_name": "string",
      "binder_number": "string",
      "period_start": "2026-01-15",
      "period_end": "2026-01-15",
      "status": "in_office",
      "returned_at": "2026-01-15",
      "pickup_person_name": "string",
      "days_active": 1,
      "work_state": "string",
      "signals": [
        "string"
      ]
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/businesses/{business_id}/tax-profile`
**Summary:** Get Tax Profile

### 📤 Success Response (200)
```json
{
  "business_id": 1,
  "vat_type": "monthly",
  "vat_start_date": "2026-01-15",
  "vat_exempt_ceiling": "123.45",
  "accountant_name": "string",
  "advance_rate": "123.45",
  "advance_rate_updated_at": "2026-01-15",
  "fiscal_year_start_month": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## PATCH `/api/v1/businesses/{business_id}/tax-profile`
**Summary:** Update Tax Profile

### 📥 Request Body (JSON)
```json
{
  "vat_type": "monthly",
  "vat_start_date": "2026-01-15",
  "vat_exempt_ceiling": "123.45",
  "accountant_name": "string",
  "advance_rate": "123.45",
  "advance_rate_updated_at": "2026-01-15",
  "fiscal_year_start_month": 1
}
```

### 📤 Success Response (200)
```json
{
  "business_id": 1,
  "vat_type": "monthly",
  "vat_start_date": "2026-01-15",
  "vat_exempt_ceiling": "123.45",
  "accountant_name": "string",
  "advance_rate": "123.45",
  "advance_rate_updated_at": "2026-01-15",
  "fiscal_year_start_month": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z"
}
```

---

## POST `/api/v1/clients/{client_id}/businesses`
**Summary:** Create Business

### 📥 Request Body (JSON)
```json
{
  "business_type": "osek_patur",
  "opened_at": "2026-01-15",
  "business_name": "string",
  "notes": "string"
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "client_id": 1,
  "business_name": "string",
  "business_type": "osek_patur",
  "status": "active",
  "opened_at": "2026-01-15",
  "closed_at": "2026-01-15",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "available_actions": [
    {
      "key": "value"
    }
  ]
}
```

---

## GET `/api/v1/clients/{client_id}/businesses`
**Summary:** List Client Businesses

### 📤 Success Response (200)
```json
{
  "client_id": 1,
  "items": [
    {
      "id": 1,
      "client_id": 1,
      "business_name": "string",
      "business_type": "osek_patur",
      "status": "active",
      "opened_at": "2026-01-15",
      "closed_at": "2026-01-15",
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "available_actions": [
        {
          "key": "value"
        }
      ]
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/businesses`
**Summary:** List Businesses

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "client_id": 1,
      "business_name": "string",
      "business_type": "osek_patur",
      "status": "active",
      "opened_at": "2026-01-15",
      "closed_at": "2026-01-15",
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "available_actions": [
        {
          "key": "value"
        }
      ],
      "client_full_name": "string",
      "client_id_number": "string"
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/businesses/{business_id}`
**Summary:** Get Business

### 📤 Success Response (200)
```json
{
  "id": 1,
  "client_id": 1,
  "business_name": "string",
  "business_type": "osek_patur",
  "status": "active",
  "opened_at": "2026-01-15",
  "closed_at": "2026-01-15",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "available_actions": [
    {
      "key": "value"
    }
  ]
}
```

---

## PATCH `/api/v1/businesses/{business_id}`
**Summary:** Update Business

### 📥 Request Body (JSON)
```json
{
  "business_name": "string",
  "business_type": "osek_patur",
  "status": "active",
  "notes": "string",
  "closed_at": "2026-01-15"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "client_id": 1,
  "business_name": "string",
  "business_type": "osek_patur",
  "status": "active",
  "opened_at": "2026-01-15",
  "closed_at": "2026-01-15",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "available_actions": [
    {
      "key": "value"
    }
  ]
}
```

---

## DELETE `/api/v1/businesses/{business_id}`
**Summary:** Delete Business

---

## POST `/api/v1/businesses/{business_id}/restore`
**Summary:** Restore Business

### 📤 Success Response (200)
```json
{
  "id": 1,
  "client_id": 1,
  "business_name": "string",
  "business_type": "osek_patur",
  "status": "active",
  "opened_at": "2026-01-15",
  "closed_at": "2026-01-15",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "available_actions": [
    {
      "key": "value"
    }
  ]
}
```

---

## POST `/api/v1/businesses/bulk-action`
**Summary:** Bulk Business Action

### 📥 Request Body (JSON)
```json
{
  "business_ids": [
    1
  ],
  "action": "freeze"
}
```

### 📤 Success Response (200)
```json
{
  "succeeded": [
    1
  ],
  "failed": [
    {
      "id": 1,
      "error": "string"
    }
  ]
}
```

---

## GET `/api/v1/binders/open`
**Summary:** List Open Binders

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "client_id": 1,
      "client_name": "string",
      "binder_number": "string",
      "period_start": "2026-01-15",
      "period_end": "2026-01-15",
      "status": "in_office",
      "returned_at": "2026-01-15",
      "pickup_person_name": "string",
      "days_active": 1,
      "work_state": "string",
      "signals": [
        "string"
      ]
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## POST `/api/v1/binders/receive`
**Summary:** Receive Binder

### 📥 Request Body (JSON)
```json
{
  "client_id": 1,
  "binder_number": "string",
  "period_start": "2026-01-15",
  "received_at": "2026-01-15",
  "received_by": 1,
  "notes": "string",
  "materials": [
    {
      "material_type": "vat",
      "business_id": 1,
      "annual_report_id": 1,
      "description": "string"
    }
  ]
}
```

### 📤 Success Response (201)
```json
{
  "binder": {
    "id": 1,
    "client_id": 1,
    "client_name": "string",
    "binder_number": "string",
    "period_start": "2026-01-15",
    "period_end": "2026-01-15",
    "status": "in_office",
    "returned_at": "2026-01-15",
    "pickup_person_name": "string",
    "notes": "string",
    "created_at": "2026-01-02T03:04:05Z",
    "days_in_office": 1,
    "work_state": "string",
    "signals": [
      "string"
    ],
    "available_actions": [
      {
        "key": "value"
      }
    ]
  },
  "intake": {
    "id": 1,
    "binder_id": 1,
    "received_at": "2026-01-15",
    "received_by": 1,
    "received_by_name": "string",
    "notes": "string",
    "created_at": "2026-01-02T03:04:05Z",
    "materials": [
      {
        "id": 1,
        "intake_id": 1,
        "material_type": "vat",
        "business_id": 1,
        "annual_report_id": 1,
        "description": "string",
        "created_at": "2026-01-02T03:04:05Z"
      }
    ]
  },
  "is_new_binder": true
}
```

---

## POST `/api/v1/binders/{binder_id}/ready`
**Summary:** Mark Ready For Pickup

### 📤 Success Response (200)
```json
{
  "id": 1,
  "client_id": 1,
  "client_name": "string",
  "binder_number": "string",
  "period_start": "2026-01-15",
  "period_end": "2026-01-15",
  "status": "in_office",
  "returned_at": "2026-01-15",
  "pickup_person_name": "string",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "days_in_office": 1,
  "work_state": "string",
  "signals": [
    "string"
  ],
  "available_actions": [
    {
      "key": "value"
    }
  ]
}
```

---

## POST `/api/v1/binders/{binder_id}/return`
**Summary:** Return Binder

### 📥 Request Body (JSON)
```json
{
  "pickup_person_name": "string",
  "returned_by": 1
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "client_id": 1,
  "client_name": "string",
  "binder_number": "string",
  "period_start": "2026-01-15",
  "period_end": "2026-01-15",
  "status": "in_office",
  "returned_at": "2026-01-15",
  "pickup_person_name": "string",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "days_in_office": 1,
  "work_state": "string",
  "signals": [
    "string"
  ],
  "available_actions": [
    {
      "key": "value"
    }
  ]
}
```

---

## GET `/api/v1/binders`
**Summary:** List Binders

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "client_id": 1,
      "client_name": "string",
      "binder_number": "string",
      "period_start": "2026-01-15",
      "period_end": "2026-01-15",
      "status": "in_office",
      "returned_at": "2026-01-15",
      "pickup_person_name": "string",
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "days_in_office": 1,
      "work_state": "string",
      "signals": [
        "string"
      ],
      "available_actions": [
        {
          "key": "value"
        }
      ]
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/binders/{binder_id}`
**Summary:** Get Binder

### 📤 Success Response (200)
```json
{
  "id": 1,
  "client_id": 1,
  "client_name": "string",
  "binder_number": "string",
  "period_start": "2026-01-15",
  "period_end": "2026-01-15",
  "status": "in_office",
  "returned_at": "2026-01-15",
  "pickup_person_name": "string",
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "days_in_office": 1,
  "work_state": "string",
  "signals": [
    "string"
  ],
  "available_actions": [
    {
      "key": "value"
    }
  ]
}
```

---

## DELETE `/api/v1/binders/{binder_id}`
**Summary:** Delete Binder

---

## GET `/api/v1/dashboard/summary`
**Summary:** Get Dashboard Summary

### 📤 Success Response (200)
```json
{
  "binders_in_office": 1,
  "binders_ready_for_pickup": 1,
  "open_reminders": 0,
  "vat_due_this_month": 0,
  "attention": {
    "items": [
      {
        "item_type": "string",
        "binder_id": 1,
        "business_id": 1,
        "client_name": "string",
        "description": "string"
      }
    ],
    "total": 0
  }
}
```

---

## GET `/api/v1/dashboard/overview`
**Summary:** Get Dashboard Overview

### 📤 Success Response (200)
```json
{
  "total_clients": 1,
  "active_binders": 1,
  "open_reminders": 0,
  "vat_due_this_month": 0,
  "quick_actions": [
    {
      "id": "string",
      "key": "string",
      "label": "string",
      "method": "string",
      "endpoint": "string",
      "payload": {
        "key": "value"
      },
      "confirm": {
        "title": "string",
        "message": "string",
        "confirm_label": "string",
        "cancel_label": "string"
      },
      "client_name": "string",
      "binder_number": "string",
      "category": "string",
      "due_label": "string"
    }
  ],
  "attention": {
    "items": [
      {
        "item_type": "string",
        "binder_id": 1,
        "business_id": 1,
        "client_name": "string",
        "description": "string"
      }
    ],
    "total": 0
  }
}
```

---

## GET `/api/v1/binders/{binder_id}/history`
**Summary:** Get Binder History

### 📤 Success Response (200)
```json
{
  "binder_id": 1,
  "history": [
    {
      "old_status": "string",
      "new_status": "string",
      "changed_by": 1,
      "changed_at": "2026-01-02T03:04:05Z",
      "notes": "string"
    }
  ]
}
```

---

## GET `/api/v1/binders/{binder_id}/intakes`
**Summary:** Get Binder Intakes

### 📤 Success Response (200)
```json
{
  "binder_id": 1,
  "intakes": [
    {
      "id": 1,
      "binder_id": 1,
      "received_at": "2026-01-15",
      "received_by": 1,
      "received_by_name": "string",
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "materials": [
        {
          "id": 1,
          "intake_id": 1,
          "material_type": "vat",
          "business_id": 1,
          "annual_report_id": 1,
          "description": "string",
          "created_at": "2026-01-02T03:04:05Z"
        }
      ]
    }
  ]
}
```

---

## POST `/api/v1/charges`
**Summary:** Create Charge

### 📥 Request Body (JSON)
```json
{
  "business_id": 1,
  "amount": "123.45",
  "charge_type": "monthly_retainer",
  "period": "string",
  "months_covered": 1,
  "description": "string",
  "annual_report_id": 1
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "annual_report_id": 1,
  "charge_type": "monthly_retainer",
  "status": "draft",
  "amount": "123.45",
  "period": "string",
  "months_covered": 1,
  "description": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "created_by": 1,
  "issued_at": "2026-01-02T03:04:05Z",
  "issued_by": 1,
  "paid_at": "2026-01-02T03:04:05Z",
  "paid_by": 1,
  "canceled_at": "2026-01-02T03:04:05Z",
  "canceled_by": 1,
  "cancellation_reason": "string"
}
```

---

## GET `/api/v1/charges`
**Summary:** List Charges

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "business_name": "string",
      "annual_report_id": 1,
      "charge_type": "monthly_retainer",
      "status": "draft",
      "amount": "123.45",
      "period": "string",
      "months_covered": 1,
      "description": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "created_by": 1,
      "issued_at": "2026-01-02T03:04:05Z",
      "issued_by": 1,
      "paid_at": "2026-01-02T03:04:05Z",
      "paid_by": 1,
      "canceled_at": "2026-01-02T03:04:05Z",
      "canceled_by": 1,
      "cancellation_reason": "string"
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## POST `/api/v1/charges/{charge_id}/issue`
**Summary:** Issue Charge

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "annual_report_id": 1,
  "charge_type": "monthly_retainer",
  "status": "draft",
  "amount": "123.45",
  "period": "string",
  "months_covered": 1,
  "description": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "created_by": 1,
  "issued_at": "2026-01-02T03:04:05Z",
  "issued_by": 1,
  "paid_at": "2026-01-02T03:04:05Z",
  "paid_by": 1,
  "canceled_at": "2026-01-02T03:04:05Z",
  "canceled_by": 1,
  "cancellation_reason": "string"
}
```

---

## POST `/api/v1/charges/{charge_id}/mark-paid`
**Summary:** Mark Charge Paid

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "annual_report_id": 1,
  "charge_type": "monthly_retainer",
  "status": "draft",
  "amount": "123.45",
  "period": "string",
  "months_covered": 1,
  "description": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "created_by": 1,
  "issued_at": "2026-01-02T03:04:05Z",
  "issued_by": 1,
  "paid_at": "2026-01-02T03:04:05Z",
  "paid_by": 1,
  "canceled_at": "2026-01-02T03:04:05Z",
  "canceled_by": 1,
  "cancellation_reason": "string"
}
```

---

## POST `/api/v1/charges/{charge_id}/cancel`
**Summary:** Cancel Charge

### 📥 Request Body (JSON)
```json
{
  "reason": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "annual_report_id": 1,
  "charge_type": "monthly_retainer",
  "status": "draft",
  "amount": "123.45",
  "period": "string",
  "months_covered": 1,
  "description": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "created_by": 1,
  "issued_at": "2026-01-02T03:04:05Z",
  "issued_by": 1,
  "paid_at": "2026-01-02T03:04:05Z",
  "paid_by": 1,
  "canceled_at": "2026-01-02T03:04:05Z",
  "canceled_by": 1,
  "cancellation_reason": "string"
}
```

---

## GET `/api/v1/charges/{charge_id}`
**Summary:** Get Charge

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "annual_report_id": 1,
  "charge_type": "monthly_retainer",
  "status": "draft",
  "amount": "123.45",
  "period": "string",
  "months_covered": 1,
  "description": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "created_by": 1,
  "issued_at": "2026-01-02T03:04:05Z",
  "issued_by": 1,
  "paid_at": "2026-01-02T03:04:05Z",
  "paid_by": 1,
  "canceled_at": "2026-01-02T03:04:05Z",
  "canceled_by": 1,
  "cancellation_reason": "string"
}
```

---

## DELETE `/api/v1/charges/{charge_id}`
**Summary:** Delete Charge

---

## POST `/api/v1/charges/bulk-action`
**Summary:** Bulk Charge Action

### 📥 Request Body (JSON)
```json
{
  "charge_ids": [
    1
  ],
  "action": "issue",
  "cancellation_reason": "string"
}
```

### 📤 Success Response (200)
```json
{
  "succeeded": [
    1
  ],
  "failed": [
    {
      "id": 1,
      "error": "string"
    }
  ]
}
```

---

## POST `/api/v1/documents/upload`
**Summary:** Upload Permanent Document

### 📤 Success Response (201)
```json
{
  "id": 1,
  "client_id": 1,
  "business_id": 1,
  "scope": "client",
  "document_type": "id_copy",
  "storage_key": "string",
  "original_filename": "string",
  "file_size_bytes": 1,
  "mime_type": "string",
  "tax_year": 1,
  "is_present": true,
  "is_deleted": true,
  "status": "pending",
  "version": 1,
  "superseded_by": 1,
  "annual_report_id": 1,
  "notes": "string",
  "uploaded_by": 1,
  "uploaded_at": "2026-01-02T03:04:05Z",
  "approved_by": 1,
  "approved_at": "2026-01-02T03:04:05Z",
  "rejected_by": 1,
  "rejected_at": "2026-01-02T03:04:05Z"
}
```

---

## GET `/api/v1/documents/business/{business_id}`
**Summary:** List Business Documents

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "client_id": 1,
      "business_id": 1,
      "scope": "client",
      "document_type": "id_copy",
      "storage_key": "string",
      "original_filename": "string",
      "file_size_bytes": 1,
      "mime_type": "string",
      "tax_year": 1,
      "is_present": true,
      "is_deleted": true,
      "status": "pending",
      "version": 1,
      "superseded_by": 1,
      "annual_report_id": 1,
      "notes": "string",
      "uploaded_by": 1,
      "uploaded_at": "2026-01-02T03:04:05Z",
      "approved_by": 1,
      "approved_at": "2026-01-02T03:04:05Z",
      "rejected_by": 1,
      "rejected_at": "2026-01-02T03:04:05Z"
    }
  ]
}
```

---

## GET `/api/v1/documents/business/{business_id}/signals`
**Summary:** Get Operational Signals

### 📤 Success Response (200)
```json
{
  "business_id": 1,
  "missing_documents": [
    "id_copy"
  ]
}
```

---

## GET `/api/v1/documents/{document_id}/download-url`
**Summary:** Get Download Url

### 📤 Success Response (200)
```json
{
  "url": "string"
}
```

---

## DELETE `/api/v1/documents/{document_id}`
**Summary:** Delete Document

---

## PUT `/api/v1/documents/{document_id}/replace`
**Summary:** Replace Document

### 📤 Success Response (200)
```json
{
  "id": 1,
  "client_id": 1,
  "business_id": 1,
  "scope": "client",
  "document_type": "id_copy",
  "storage_key": "string",
  "original_filename": "string",
  "file_size_bytes": 1,
  "mime_type": "string",
  "tax_year": 1,
  "is_present": true,
  "is_deleted": true,
  "status": "pending",
  "version": 1,
  "superseded_by": 1,
  "annual_report_id": 1,
  "notes": "string",
  "uploaded_by": 1,
  "uploaded_at": "2026-01-02T03:04:05Z",
  "approved_by": 1,
  "approved_at": "2026-01-02T03:04:05Z",
  "rejected_by": 1,
  "rejected_at": "2026-01-02T03:04:05Z"
}
```

---

## POST `/api/v1/documents/{document_id}/approve`
**Summary:** Approve Document

### 📤 Success Response (200)
```json
{
  "id": 1,
  "client_id": 1,
  "business_id": 1,
  "scope": "client",
  "document_type": "id_copy",
  "storage_key": "string",
  "original_filename": "string",
  "file_size_bytes": 1,
  "mime_type": "string",
  "tax_year": 1,
  "is_present": true,
  "is_deleted": true,
  "status": "pending",
  "version": 1,
  "superseded_by": 1,
  "annual_report_id": 1,
  "notes": "string",
  "uploaded_by": 1,
  "uploaded_at": "2026-01-02T03:04:05Z",
  "approved_by": 1,
  "approved_at": "2026-01-02T03:04:05Z",
  "rejected_by": 1,
  "rejected_at": "2026-01-02T03:04:05Z"
}
```

---

## POST `/api/v1/documents/{document_id}/reject`
**Summary:** Reject Document

### 📥 Request Body (JSON)
```json
{
  "notes": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "client_id": 1,
  "business_id": 1,
  "scope": "client",
  "document_type": "id_copy",
  "storage_key": "string",
  "original_filename": "string",
  "file_size_bytes": 1,
  "mime_type": "string",
  "tax_year": 1,
  "is_present": true,
  "is_deleted": true,
  "status": "pending",
  "version": 1,
  "superseded_by": 1,
  "annual_report_id": 1,
  "notes": "string",
  "uploaded_by": 1,
  "uploaded_at": "2026-01-02T03:04:05Z",
  "approved_by": 1,
  "approved_at": "2026-01-02T03:04:05Z",
  "rejected_by": 1,
  "rejected_at": "2026-01-02T03:04:05Z"
}
```

---

## GET `/api/v1/documents/business/{business_id}/versions`
**Summary:** Get Document Versions

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "client_id": 1,
      "business_id": 1,
      "scope": "client",
      "document_type": "id_copy",
      "storage_key": "string",
      "original_filename": "string",
      "file_size_bytes": 1,
      "mime_type": "string",
      "tax_year": 1,
      "is_present": true,
      "is_deleted": true,
      "status": "pending",
      "version": 1,
      "superseded_by": 1,
      "annual_report_id": 1,
      "notes": "string",
      "uploaded_by": 1,
      "uploaded_at": "2026-01-02T03:04:05Z",
      "approved_by": 1,
      "approved_at": "2026-01-02T03:04:05Z",
      "rejected_by": 1,
      "rejected_at": "2026-01-02T03:04:05Z"
    }
  ]
}
```

---

## GET `/api/v1/documents/annual-report/{report_id}`
**Summary:** List By Annual Report

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "client_id": 1,
      "business_id": 1,
      "scope": "client",
      "document_type": "id_copy",
      "storage_key": "string",
      "original_filename": "string",
      "file_size_bytes": 1,
      "mime_type": "string",
      "tax_year": 1,
      "is_present": true,
      "is_deleted": true,
      "status": "pending",
      "version": 1,
      "superseded_by": 1,
      "annual_report_id": 1,
      "notes": "string",
      "uploaded_by": 1,
      "uploaded_at": "2026-01-02T03:04:05Z",
      "approved_by": 1,
      "approved_at": "2026-01-02T03:04:05Z",
      "rejected_by": 1,
      "rejected_at": "2026-01-02T03:04:05Z"
    }
  ]
}
```

---

## PATCH `/api/v1/documents/{document_id}/notes`
**Summary:** Update Notes

### 📥 Request Body (JSON)
```json
{
  "notes": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "client_id": 1,
  "business_id": 1,
  "scope": "client",
  "document_type": "id_copy",
  "storage_key": "string",
  "original_filename": "string",
  "file_size_bytes": 1,
  "mime_type": "string",
  "tax_year": 1,
  "is_present": true,
  "is_deleted": true,
  "status": "pending",
  "version": 1,
  "superseded_by": 1,
  "annual_report_id": 1,
  "notes": "string",
  "uploaded_by": 1,
  "uploaded_at": "2026-01-02T03:04:05Z",
  "approved_by": 1,
  "approved_at": "2026-01-02T03:04:05Z",
  "rejected_by": 1,
  "rejected_at": "2026-01-02T03:04:05Z"
}
```

---

## GET `/api/v1/dashboard/work-queue`
**Summary:** Get Work Queue

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "binder_id": 1,
      "business_id": 1,
      "client_name": "string",
      "binder_number": "string",
      "work_state": "string",
      "signals": [
        "string"
      ],
      "days_since_received": 1
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/dashboard/attention`
**Summary:** Get Attention Items

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "item_type": "string",
      "binder_id": 1,
      "business_id": 1,
      "client_name": "string",
      "description": "string"
    }
  ],
  "total": 0
}
```

---

## GET `/api/v1/reports/vat-compliance`
**Summary:** Get Vat Compliance Report

### 📤 Success Response (200)
```json
{
  "year": 2026,
  "total_clients": 2,
  "items": [
    {
      "client_id": 1,
      "client_name": "string",
      "periods_expected": 12,
      "periods_filed": 10,
      "periods_open": 2,
      "on_time_count": 9,
      "late_count": 1,
      "compliance_rate": 83.33
    }
  ],
  "stale_pending": [
    {
      "client_id": 1,
      "client_name": "string",
      "period": "2026-01",
      "days_pending": 45
    }
  ]
}
```

---

## GET `/api/v1/reports/advance-payments`
**Summary:** Get Advance Payment Report

### 📤 Success Response (200)
```json
{
  "year": 2026,
  "month": 3,
  "total_expected": 25000.0,
  "total_paid": 20000.0,
  "collection_rate": 80.0,
  "total_gap": 5000.0,
  "items": [
    {
      "business_id": 1,
      "client_id": 1,
      "business_name": "string",
      "client_name": "string",
      "total_expected": 12000.0,
      "total_paid": 9000.0,
      "overdue_count": 1,
      "gap": 3000.0
    }
  ]
}
```

---

## GET `/api/v1/reports/annual-reports`
**Summary:** Get Annual Report Status Report

### 📤 Success Response (200)
```json
{
  "tax_year": 2026,
  "total": 2,
  "statuses": [
    {
      "status": "collecting_docs",
      "count": 1,
      "clients": [
        {
          "client_id": 1,
          "client_name": "string",
          "form_type": "1301",
          "filing_deadline": "2026-04-30",
          "days_until_deadline": 38
        }
      ]
    }
  ]
}
```

---

## GET `/api/v1/reports/aging`
**Summary:** Get Aging Report

### 📤 Success Response (200)
```json
{
  "report_date": "2026-03-23",
  "total_outstanding": 15250.0,
  "items": [
    {
      "client_id": 1,
      "client_name": "string",
      "total_outstanding": 15250.0,
      "current": 5000.0,
      "days_30": 4000.0,
      "days_60": 3000.0,
      "days_90_plus": 3250.0,
      "oldest_invoice_date": "2025-11-20",
      "oldest_invoice_days": 123
    }
  ],
  "summary": {
    "total_clients": 1,
    "total_current": 5000.0,
    "total_30_days": 4000.0,
    "total_60_days": 3000.0,
    "total_90_plus": 3250.0
  },
  "capped": false,
  "cap_limit": 2000
}
```

---

## GET `/api/v1/reports/aging/export`
**Summary:** Export Aging Report

### 📤 Success Response (200)
```text
Binary file response (download stream)

Variant 1 (format=pdf)
Content-Type: application/pdf
Content-Disposition: attachment; filename="aging_report_20260323_120000.pdf"

Variant 2 (format=excel)
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="aging_report_20260323_120000.xlsx"

Body: <binary bytes>
```

---

## GET `/api/v1/businesses/{business_id}/timeline`
**Summary:** Get Business Timeline

### 📤 Success Response (200)
```json
{
  "business_id": 1,
  "events": [
    {
      "event_type": "string",
      "timestamp": "2026-01-02T03:04:05Z",
      "binder_id": 1,
      "charge_id": 1,
      "description": "string",
      "metadata": {
        "key": "value"
      },
      "actions": [
        {
          "key": "value"
        }
      ],
      "available_actions": [
        {
          "key": "value"
        }
      ]
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/search`
**Summary:** Search

### 📤 Success Response (200)
```json
{
  "results": [
    {
      "result_type": "string",
      "client_id": 1,
      "client_name": "string",
      "client_status": "string",
      "binder_id": 1,
      "binder_number": "string",
      "work_state": "string",
      "signals": [
        "string"
      ]
    }
  ],
  "documents": [
    {
      "id": 1,
      "business_id": 1,
      "client_name": "string",
      "document_type": "string",
      "original_filename": "string",
      "tax_year": 1,
      "status": "string"
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/users/audit-logs`
**Summary:** List Audit Logs

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "action": "login_success",
      "actor_user_id": 1,
      "target_user_id": 1,
      "email": "string",
      "status": "success",
      "reason": "string",
      "metadata": {
        "key": "value"
      },
      "created_at": "2026-01-02T03:04:05Z"
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## POST `/api/v1/users`
**Summary:** Create User

### 📥 Request Body (JSON)
```json
{
  "full_name": "string",
  "email": "user@example.com",
  "phone": "string",
  "role": "advisor",
  "password": "string"
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "full_name": "string",
  "email": "user@example.com",
  "phone": "string",
  "role": "advisor",
  "is_active": true,
  "created_at": "2026-01-02T03:04:05Z",
  "last_login_at": "2026-01-02T03:04:05Z"
}
```

---

## GET `/api/v1/users`
**Summary:** List Users

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "full_name": "string",
      "email": "user@example.com",
      "phone": "string",
      "role": "advisor",
      "is_active": true,
      "created_at": "2026-01-02T03:04:05Z",
      "last_login_at": "2026-01-02T03:04:05Z"
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/users/{user_id}`
**Summary:** Get User

### 📤 Success Response (200)
```json
{
  "id": 1,
  "full_name": "string",
  "email": "user@example.com",
  "phone": "string",
  "role": "advisor",
  "is_active": true,
  "created_at": "2026-01-02T03:04:05Z",
  "last_login_at": "2026-01-02T03:04:05Z"
}
```

---

## PATCH `/api/v1/users/{user_id}`
**Summary:** Update User

### 📥 Request Body (JSON)
```json
{
  "full_name": "string",
  "phone": "string",
  "role": "advisor",
  "email": "user@example.com"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "full_name": "string",
  "email": "user@example.com",
  "phone": "string",
  "role": "advisor",
  "is_active": true,
  "created_at": "2026-01-02T03:04:05Z",
  "last_login_at": "2026-01-02T03:04:05Z"
}
```

---

## POST `/api/v1/users/{user_id}/activate`
**Summary:** Activate User

### 📤 Success Response (200)
```json
{
  "id": 1,
  "full_name": "string",
  "email": "user@example.com",
  "phone": "string",
  "role": "advisor",
  "is_active": true,
  "created_at": "2026-01-02T03:04:05Z",
  "last_login_at": "2026-01-02T03:04:05Z"
}
```

---

## POST `/api/v1/users/{user_id}/deactivate`
**Summary:** Deactivate User

### 📤 Success Response (200)
```json
{
  "id": 1,
  "full_name": "string",
  "email": "user@example.com",
  "phone": "string",
  "role": "advisor",
  "is_active": true,
  "created_at": "2026-01-02T03:04:05Z",
  "last_login_at": "2026-01-02T03:04:05Z"
}
```

---

## POST `/api/v1/users/{user_id}/reset-password`
**Summary:** Reset Password

### 📥 Request Body (JSON)
```json
{
  "new_password": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "full_name": "string",
  "email": "user@example.com",
  "phone": "string",
  "role": "advisor",
  "is_active": true,
  "created_at": "2026-01-02T03:04:05Z",
  "last_login_at": "2026-01-02T03:04:05Z"
}
```

---

## GET `/api/v1/reminders/`
**Summary:** List Reminders

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "business_name": "string",
      "reminder_type": "tax_deadline_approaching",
      "status": "pending",
      "target_date": "2026-01-15",
      "days_before": 1,
      "send_on": "2026-01-15",
      "message": "string",
      "binder_id": 1,
      "charge_id": 1,
      "tax_deadline_id": 1,
      "annual_report_id": 1,
      "advance_payment_id": 1,
      "created_at": "2026-01-02T03:04:05Z",
      "created_by": 1,
      "sent_at": "2026-01-02T03:04:05Z",
      "canceled_at": "2026-01-02T03:04:05Z",
      "canceled_by": 1
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## POST `/api/v1/reminders/`
**Summary:** Create Reminder

### 📥 Request Body (JSON)
```json
{
  "business_id": 1,
  "reminder_type": "tax_deadline_approaching",
  "target_date": "2026-01-15",
  "days_before": 1,
  "message": "string",
  "binder_id": 1,
  "charge_id": 1,
  "tax_deadline_id": 1,
  "annual_report_id": 1,
  "advance_payment_id": 1
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "reminder_type": "tax_deadline_approaching",
  "status": "pending",
  "target_date": "2026-01-15",
  "days_before": 1,
  "send_on": "2026-01-15",
  "message": "string",
  "binder_id": 1,
  "charge_id": 1,
  "tax_deadline_id": 1,
  "annual_report_id": 1,
  "advance_payment_id": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "created_by": 1,
  "sent_at": "2026-01-02T03:04:05Z",
  "canceled_at": "2026-01-02T03:04:05Z",
  "canceled_by": 1
}
```

---

## GET `/api/v1/reminders/{reminder_id}`
**Summary:** Get Reminder

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "reminder_type": "tax_deadline_approaching",
  "status": "pending",
  "target_date": "2026-01-15",
  "days_before": 1,
  "send_on": "2026-01-15",
  "message": "string",
  "binder_id": 1,
  "charge_id": 1,
  "tax_deadline_id": 1,
  "annual_report_id": 1,
  "advance_payment_id": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "created_by": 1,
  "sent_at": "2026-01-02T03:04:05Z",
  "canceled_at": "2026-01-02T03:04:05Z",
  "canceled_by": 1
}
```

---

## POST `/api/v1/reminders/{reminder_id}/cancel`
**Summary:** Cancel Reminder

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "reminder_type": "tax_deadline_approaching",
  "status": "pending",
  "target_date": "2026-01-15",
  "days_before": 1,
  "send_on": "2026-01-15",
  "message": "string",
  "binder_id": 1,
  "charge_id": 1,
  "tax_deadline_id": 1,
  "annual_report_id": 1,
  "advance_payment_id": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "created_by": 1,
  "sent_at": "2026-01-02T03:04:05Z",
  "canceled_at": "2026-01-02T03:04:05Z",
  "canceled_by": 1
}
```

---

## POST `/api/v1/reminders/{reminder_id}/mark-sent`
**Summary:** Mark Reminder Sent

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "reminder_type": "tax_deadline_approaching",
  "status": "pending",
  "target_date": "2026-01-15",
  "days_before": 1,
  "send_on": "2026-01-15",
  "message": "string",
  "binder_id": 1,
  "charge_id": 1,
  "tax_deadline_id": 1,
  "annual_report_id": 1,
  "advance_payment_id": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "created_by": 1,
  "sent_at": "2026-01-02T03:04:05Z",
  "canceled_at": "2026-01-02T03:04:05Z",
  "canceled_by": 1
}
```

---

## GET `/api/v1/notifications`
**Summary:** List Notifications

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "business_name": "string",
      "binder_id": 1,
      "trigger": "binder_received",
      "channel": "whatsapp",
      "severity": "info",
      "recipient": "string",
      "content_snapshot": "string",
      "status": "pending",
      "sent_at": "2026-01-02T03:04:05Z",
      "failed_at": "2026-01-02T03:04:05Z",
      "error_message": "string",
      "retry_count": 1,
      "is_read": true,
      "read_at": "2026-01-02T03:04:05Z",
      "triggered_by": 1,
      "created_at": "2026-01-02T03:04:05Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 1
}
```

---

## GET `/api/v1/notifications/unread-count`
**Summary:** Get Unread Count

### 📤 Success Response (200)
```json
{
  "unread_count": 1
}
```

---

## POST `/api/v1/notifications/mark-read`
**Summary:** Mark Read

### 📥 Request Body (JSON)
```json
{
  "notification_ids": [
    1
  ]
}
```

### 📤 Success Response (200)
```json
{
  "updated": 1
}
```

---

## POST `/api/v1/notifications/mark-all-read`
**Summary:** Mark All Read

### 📤 Success Response (200)
```json
{
  "updated": 1
}
```

---

## POST `/api/v1/notifications/send`
**Summary:** Send Notification

### 📥 Request Body (JSON)
```json
{
  "business_id": 1,
  "channel": "whatsapp",
  "message": "string",
  "severity": "info"
}
```

### 📤 Success Response (200)
```json
{
  "ok": true
}
```

---

## GET `/api/v1/businesses/{business_id}/correspondence`
**Summary:** List Correspondence

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "contact_id": 1,
      "correspondence_type": "call",
      "subject": "string",
      "notes": "string",
      "occurred_at": "2026-01-02T03:04:05Z",
      "created_by": 1,
      "created_at": "2026-01-02T03:04:05Z"
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1,
  "total_pages": 1
}
```

---

## POST `/api/v1/businesses/{business_id}/correspondence`
**Summary:** Create Correspondence

### 📥 Request Body (JSON)
```json
{
  "contact_id": 1,
  "correspondence_type": "call",
  "subject": "string",
  "notes": "string",
  "occurred_at": "2026-01-02T03:04:05Z"
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "business_id": 1,
  "contact_id": 1,
  "correspondence_type": "call",
  "subject": "string",
  "notes": "string",
  "occurred_at": "2026-01-02T03:04:05Z",
  "created_by": 1,
  "created_at": "2026-01-02T03:04:05Z"
}
```

---

## GET `/api/v1/businesses/{business_id}/correspondence/{correspondence_id}`
**Summary:** Get Correspondence

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "contact_id": 1,
  "correspondence_type": "call",
  "subject": "string",
  "notes": "string",
  "occurred_at": "2026-01-02T03:04:05Z",
  "created_by": 1,
  "created_at": "2026-01-02T03:04:05Z"
}
```

---

## PATCH `/api/v1/businesses/{business_id}/correspondence/{correspondence_id}`
**Summary:** Update Correspondence

### 📥 Request Body (JSON)
```json
{
  "contact_id": 1,
  "correspondence_type": "call",
  "subject": "string",
  "notes": "string",
  "occurred_at": "2026-01-02T03:04:05Z"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "contact_id": 1,
  "correspondence_type": "call",
  "subject": "string",
  "notes": "string",
  "occurred_at": "2026-01-02T03:04:05Z",
  "created_by": 1,
  "created_at": "2026-01-02T03:04:05Z"
}
```

---

## DELETE `/api/v1/businesses/{business_id}/correspondence/{correspondence_id}`
**Summary:** Delete Correspondence

---

## GET `/api/v1/businesses/{business_id}/advance-payments`
**Summary:** List Advance Payments

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "period": "string",
      "period_months_count": 1,
      "due_date": "2026-01-15",
      "expected_amount": "123.45",
      "paid_amount": "123.45",
      "status": "pending",
      "paid_at": "2026-01-02T03:04:05Z",
      "payment_method": "bank_transfer",
      "annual_report_id": 1,
      "notes": "string",
      "created_at": "2026-01-02T03:04:05Z",
      "updated_at": "2026-01-02T03:04:05Z",
      "delta": "string"
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## POST `/api/v1/businesses/{business_id}/advance-payments`
**Summary:** Create Advance Payment

### 📥 Request Body (JSON)
```json
{
  "business_id": 123,
  "due_date": "2026-04-15",
  "expected_amount": "2500.00",
  "period": "2026-03",
  "period_months_count": 1
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "business_id": 1,
  "period": "string",
  "period_months_count": 1,
  "due_date": "2026-01-15",
  "expected_amount": "123.45",
  "paid_amount": "123.45",
  "status": "pending",
  "paid_at": "2026-01-02T03:04:05Z",
  "payment_method": "bank_transfer",
  "annual_report_id": 1,
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z",
  "delta": "string"
}
```

---

## GET `/api/v1/businesses/{business_id}/advance-payments/suggest`
**Summary:** Suggest Advance Payment

### 📤 Success Response (200)
```json
{
  "business_id": 1,
  "year": 1,
  "suggested_amount": "123.45",
  "has_data": true
}
```

---

## GET `/api/v1/businesses/{business_id}/advance-payments/kpi`
**Summary:** Get Annual Kpis

### 📤 Success Response (200)
```json
{
  "business_id": 1,
  "year": 1,
  "total_expected": "123.45",
  "total_paid": "123.45",
  "collection_rate": 1.0,
  "overdue_count": 1,
  "on_time_count": 1
}
```

---

## GET `/api/v1/businesses/{business_id}/advance-payments/chart`
**Summary:** Get Chart Data

### 📤 Success Response (200)
```json
{
  "business_id": 1,
  "year": 1,
  "months": [
    {
      "period": "string",
      "expected_amount": "123.45",
      "paid_amount": "123.45",
      "overdue_amount": "123.45"
    }
  ]
}
```

---

## PATCH `/api/v1/businesses/{business_id}/advance-payments/{payment_id}`
**Summary:** Update Advance Payment

### 📥 Request Body (JSON)
```json
{
  "paid_amount": "123.45",
  "expected_amount": "123.45",
  "status": "pending",
  "paid_at": "2026-01-02T03:04:05Z",
  "payment_method": "bank_transfer",
  "notes": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "period": "string",
  "period_months_count": 1,
  "due_date": "2026-01-15",
  "expected_amount": "123.45",
  "paid_amount": "123.45",
  "status": "pending",
  "paid_at": "2026-01-02T03:04:05Z",
  "payment_method": "bank_transfer",
  "annual_report_id": 1,
  "notes": "string",
  "created_at": "2026-01-02T03:04:05Z",
  "updated_at": "2026-01-02T03:04:05Z",
  "delta": "string"
}
```

---

## DELETE `/api/v1/businesses/{business_id}/advance-payments/{payment_id}`
**Summary:** Delete Advance Payment

---

## GET `/api/v1/advance-payments/overview`
**Summary:** List Advance Payments Overview

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "business_name": "string",
      "period": "string",
      "period_months_count": 1,
      "due_date": "2026-01-15",
      "expected_amount": "123.45",
      "paid_amount": "123.45",
      "status": "pending"
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1,
  "total_expected": "123.45",
  "total_paid": "123.45",
  "collection_rate": 1.0
}
```

---

## POST `/api/v1/advance-payments/generate`
**Summary:** Generate Advance Payment Schedule

### 📥 Request Body (JSON)
```json
{
  "business_id": 1,
  "year": 1,
  "period_months_count": 1
}
```

### 📤 Success Response (200)
```json
{
  "created": 1,
  "skipped": 1
}
```

---

## POST `/api/v1/signature-requests`
**Summary:** Create Signature Request

### 📥 Request Body (JSON)
```json
{
  "business_id": 1,
  "request_type": "engagement_agreement",
  "title": "string",
  "description": "string",
  "signer_name": "string",
  "signer_email": "user@example.com",
  "signer_phone": "string",
  "annual_report_id": 1,
  "document_id": 1,
  "content_to_hash": "string"
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "business_id": 1,
  "created_by": 1,
  "request_type": "engagement_agreement",
  "title": "string",
  "description": "string",
  "signer_name": "string",
  "signer_email": "string",
  "signer_phone": "string",
  "status": "draft",
  "content_hash": "string",
  "storage_key": "string",
  "annual_report_id": 1,
  "document_id": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "sent_at": "2026-01-02T03:04:05Z",
  "expires_at": "2026-01-02T03:04:05Z",
  "signed_at": "2026-01-02T03:04:05Z",
  "declined_at": "2026-01-02T03:04:05Z",
  "canceled_at": "2026-01-02T03:04:05Z",
  "canceled_by": 1,
  "signer_ip_address": "string",
  "decline_reason": "string",
  "signed_document_key": "string"
}
```

---

## GET `/api/v1/signature-requests/pending`
**Summary:** List Pending Requests

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "created_by": 1,
      "request_type": "engagement_agreement",
      "title": "string",
      "description": "string",
      "signer_name": "string",
      "signer_email": "string",
      "signer_phone": "string",
      "status": "draft",
      "content_hash": "string",
      "storage_key": "string",
      "annual_report_id": 1,
      "document_id": 1,
      "created_at": "2026-01-02T03:04:05Z",
      "sent_at": "2026-01-02T03:04:05Z",
      "expires_at": "2026-01-02T03:04:05Z",
      "signed_at": "2026-01-02T03:04:05Z",
      "declined_at": "2026-01-02T03:04:05Z",
      "canceled_at": "2026-01-02T03:04:05Z",
      "canceled_by": 1,
      "signer_ip_address": "string",
      "decline_reason": "string",
      "signed_document_key": "string"
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/api/v1/signature-requests/{request_id}/audit-trail`
**Summary:** Get Signature Request Audit Trail

### 📤 Success Response (200)
```json
[
  {
    "id": 1,
    "event_type": "string",
    "actor_type": "string",
    "actor_id": 1,
    "actor_name": "string",
    "ip_address": "string",
    "notes": "string",
    "occurred_at": "2026-01-02T03:04:05Z"
  }
]
```

---

## GET `/api/v1/signature-requests/{request_id}`
**Summary:** Get Signature Request

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "created_by": 1,
  "request_type": "engagement_agreement",
  "title": "string",
  "description": "string",
  "signer_name": "string",
  "signer_email": "string",
  "signer_phone": "string",
  "status": "draft",
  "content_hash": "string",
  "storage_key": "string",
  "annual_report_id": 1,
  "document_id": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "sent_at": "2026-01-02T03:04:05Z",
  "expires_at": "2026-01-02T03:04:05Z",
  "signed_at": "2026-01-02T03:04:05Z",
  "declined_at": "2026-01-02T03:04:05Z",
  "canceled_at": "2026-01-02T03:04:05Z",
  "canceled_by": 1,
  "signer_ip_address": "string",
  "decline_reason": "string",
  "signed_document_key": "string",
  "audit_trail": [
    {
      "id": 1,
      "event_type": "string",
      "actor_type": "string",
      "actor_id": 1,
      "actor_name": "string",
      "ip_address": "string",
      "notes": "string",
      "occurred_at": "2026-01-02T03:04:05Z"
    }
  ]
}
```

---

## POST `/api/v1/signature-requests/{request_id}/send`
**Summary:** Send Signature Request

### 📥 Request Body (JSON)
```json
{
  "expiry_days": 14
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "created_by": 1,
  "request_type": "engagement_agreement",
  "title": "string",
  "description": "string",
  "signer_name": "string",
  "signer_email": "string",
  "signer_phone": "string",
  "status": "draft",
  "content_hash": "string",
  "storage_key": "string",
  "annual_report_id": 1,
  "document_id": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "sent_at": "2026-01-02T03:04:05Z",
  "expires_at": "2026-01-02T03:04:05Z",
  "signed_at": "2026-01-02T03:04:05Z",
  "declined_at": "2026-01-02T03:04:05Z",
  "canceled_at": "2026-01-02T03:04:05Z",
  "canceled_by": 1,
  "signer_ip_address": "string",
  "decline_reason": "string",
  "signed_document_key": "string",
  "signing_token": "string",
  "signing_url_hint": "string"
}
```

---

## POST `/api/v1/signature-requests/{request_id}/cancel`
**Summary:** Cancel Signature Request

### 📥 Request Body (JSON)
```json
{
  "reason": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "created_by": 1,
  "request_type": "engagement_agreement",
  "title": "string",
  "description": "string",
  "signer_name": "string",
  "signer_email": "string",
  "signer_phone": "string",
  "status": "draft",
  "content_hash": "string",
  "storage_key": "string",
  "annual_report_id": 1,
  "document_id": 1,
  "created_at": "2026-01-02T03:04:05Z",
  "sent_at": "2026-01-02T03:04:05Z",
  "expires_at": "2026-01-02T03:04:05Z",
  "signed_at": "2026-01-02T03:04:05Z",
  "declined_at": "2026-01-02T03:04:05Z",
  "canceled_at": "2026-01-02T03:04:05Z",
  "canceled_by": 1,
  "signer_ip_address": "string",
  "decline_reason": "string",
  "signed_document_key": "string"
}
```

---

## GET `/api/v1/businesses/{business_id}/signature-requests`
**Summary:** List Business Signature Requests

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "created_by": 1,
      "request_type": "engagement_agreement",
      "title": "string",
      "description": "string",
      "signer_name": "string",
      "signer_email": "string",
      "signer_phone": "string",
      "status": "draft",
      "content_hash": "string",
      "storage_key": "string",
      "annual_report_id": 1,
      "document_id": 1,
      "created_at": "2026-01-02T03:04:05Z",
      "sent_at": "2026-01-02T03:04:05Z",
      "expires_at": "2026-01-02T03:04:05Z",
      "signed_at": "2026-01-02T03:04:05Z",
      "declined_at": "2026-01-02T03:04:05Z",
      "canceled_at": "2026-01-02T03:04:05Z",
      "canceled_by": 1,
      "signer_ip_address": "string",
      "decline_reason": "string",
      "signed_document_key": "string"
    }
  ],
  "page": 1,
  "page_size": 1,
  "total": 1
}
```

---

## GET `/sign/{token}`
**Summary:** Signer View

### 📤 Success Response (200)
```json
{
  "request_id": 1,
  "title": "string",
  "description": "string",
  "signer_name": "string",
  "status": "draft",
  "content_hash": "string",
  "expires_at": "2026-01-02T03:04:05Z"
}
```

---

## POST `/sign/{token}/approve`
**Summary:** Signer Approve

### 📤 Success Response (200)
```json
{
  "request_id": 1,
  "title": "string",
  "description": "string",
  "signer_name": "string",
  "status": "draft",
  "content_hash": "string",
  "expires_at": "2026-01-02T03:04:05Z"
}
```

---

## POST `/sign/{token}/decline`
**Summary:** Signer Decline

### 📥 Request Body (JSON)
```json
{
  "reason": "string"
}
```

### 📤 Success Response (200)
```json
{
  "request_id": 1,
  "title": "string",
  "description": "string",
  "signer_name": "string",
  "status": "draft",
  "content_hash": "string",
  "expires_at": "2026-01-02T03:04:05Z"
}
```

---

## POST `/api/v1/vat/work-items`
**Summary:** Create Work Item

### 📥 Request Body (JSON)
```json
{
  "business_id": 1,
  "period": "string",
  "assigned_to": 1,
  "mark_pending": false,
  "pending_materials_note": "string"
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "business_status": "active",
  "period": "string",
  "period_type": "monthly",
  "status": "pending_materials",
  "pending_materials_note": "string",
  "total_output_vat": "string",
  "total_input_vat": "string",
  "net_vat": "string",
  "total_output_net": "string",
  "total_input_net": "string",
  "final_vat_amount": "string",
  "is_overridden": true,
  "override_justification": "string",
  "submission_method": "online",
  "filed_at": "2026-01-15T10:30:00Z",
  "filed_by": 1,
  "filed_by_name": "string",
  "submission_reference": "string",
  "is_amendment": false,
  "amends_item_id": 1,
  "created_by": 1,
  "assigned_to": 1,
  "assigned_to_name": "string",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z",
  "submission_deadline": "2026-01-15",
  "days_until_deadline": 1,
  "is_overdue": true
}
```

---

## GET `/api/v1/vat/work-items`
**Summary:** List Work Items

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "business_name": "string",
      "business_status": "active",
      "period": "string",
      "period_type": "monthly",
      "status": "pending_materials",
      "pending_materials_note": "string",
      "total_output_vat": "string",
      "total_input_vat": "string",
      "net_vat": "string",
      "total_output_net": "string",
      "total_input_net": "string",
      "final_vat_amount": "string",
      "is_overridden": true,
      "override_justification": "string",
      "submission_method": "online",
      "filed_at": "2026-01-15T10:30:00Z",
      "filed_by": 1,
      "filed_by_name": "string",
      "submission_reference": "string",
      "is_amendment": false,
      "amends_item_id": 1,
      "created_by": 1,
      "assigned_to": 1,
      "assigned_to_name": "string",
      "created_at": "2026-01-15T10:30:00Z",
      "updated_at": "2026-01-15T10:30:00Z",
      "submission_deadline": "2026-01-15",
      "days_until_deadline": 1,
      "is_overdue": true
    }
  ],
  "total": 1
}
```

---

## POST `/api/v1/vat/work-items/{item_id}/materials-complete`
**Summary:** Mark Materials Complete

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "business_status": "active",
  "period": "string",
  "period_type": "monthly",
  "status": "pending_materials",
  "pending_materials_note": "string",
  "total_output_vat": "string",
  "total_input_vat": "string",
  "net_vat": "string",
  "total_output_net": "string",
  "total_input_net": "string",
  "final_vat_amount": "string",
  "is_overridden": true,
  "override_justification": "string",
  "submission_method": "online",
  "filed_at": "2026-01-15T10:30:00Z",
  "filed_by": 1,
  "filed_by_name": "string",
  "submission_reference": "string",
  "is_amendment": false,
  "amends_item_id": 1,
  "created_by": 1,
  "assigned_to": 1,
  "assigned_to_name": "string",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z",
  "submission_deadline": "2026-01-15",
  "days_until_deadline": 1,
  "is_overdue": true
}
```

---

## POST `/api/v1/vat/work-items/{item_id}/invoices`
**Summary:** Add Invoice

### 📥 Request Body (JSON)
```json
{
  "invoice_type": "income",
  "invoice_number": "string",
  "invoice_date": "2026-01-15",
  "counterparty_name": "string",
  "net_amount": "123.45",
  "vat_amount": "123.45",
  "counterparty_id": "string",
  "counterparty_id_type": "il_business",
  "expense_category": "office",
  "rate_type": "standard",
  "document_type": "tax_invoice"
}
```

### 📤 Success Response (201)
```json
{
  "id": 1,
  "work_item_id": 1,
  "invoice_type": "income",
  "document_type": "tax_invoice",
  "invoice_number": "string",
  "invoice_date": "2026-01-15",
  "counterparty_name": "string",
  "counterparty_id": "string",
  "counterparty_id_type": "il_business",
  "net_amount": "123.45",
  "vat_amount": "123.45",
  "expense_category": "office",
  "rate_type": "standard",
  "deduction_rate": "123.45",
  "is_exceptional": true,
  "created_by": 1,
  "created_at": "2026-01-15"
}
```

---

## GET `/api/v1/vat/work-items/{item_id}/invoices`
**Summary:** List Invoices

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "work_item_id": 1,
      "invoice_type": "income",
      "document_type": "tax_invoice",
      "invoice_number": "string",
      "invoice_date": "2026-01-15",
      "counterparty_name": "string",
      "counterparty_id": "string",
      "counterparty_id_type": "il_business",
      "net_amount": "123.45",
      "vat_amount": "123.45",
      "expense_category": "office",
      "rate_type": "standard",
      "deduction_rate": "123.45",
      "is_exceptional": true,
      "created_by": 1,
      "created_at": "2026-01-15"
    }
  ]
}
```

---

## PATCH `/api/v1/vat/work-items/{item_id}/invoices/{invoice_id}`
**Summary:** Update Invoice

### 📥 Request Body (JSON)
```json
{
  "net_amount": "123.45",
  "vat_amount": "123.45",
  "invoice_number": "string",
  "invoice_date": "2026-01-15",
  "counterparty_name": "string",
  "counterparty_id": "string",
  "counterparty_id_type": "il_business",
  "expense_category": "office",
  "rate_type": "standard",
  "document_type": "tax_invoice"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "work_item_id": 1,
  "invoice_type": "income",
  "document_type": "tax_invoice",
  "invoice_number": "string",
  "invoice_date": "2026-01-15",
  "counterparty_name": "string",
  "counterparty_id": "string",
  "counterparty_id_type": "il_business",
  "net_amount": "123.45",
  "vat_amount": "123.45",
  "expense_category": "office",
  "rate_type": "standard",
  "deduction_rate": "123.45",
  "is_exceptional": true,
  "created_by": 1,
  "created_at": "2026-01-15"
}
```

---

## DELETE `/api/v1/vat/work-items/{item_id}/invoices/{invoice_id}`
**Summary:** Delete Invoice

---

## POST `/api/v1/vat/work-items/{item_id}/ready-for-review`
**Summary:** Mark Ready For Review

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "business_status": "active",
  "period": "string",
  "period_type": "monthly",
  "status": "pending_materials",
  "pending_materials_note": "string",
  "total_output_vat": "string",
  "total_input_vat": "string",
  "net_vat": "string",
  "total_output_net": "string",
  "total_input_net": "string",
  "final_vat_amount": "string",
  "is_overridden": true,
  "override_justification": "string",
  "submission_method": "online",
  "filed_at": "2026-01-15T10:30:00Z",
  "filed_by": 1,
  "filed_by_name": "string",
  "submission_reference": "string",
  "is_amendment": false,
  "amends_item_id": 1,
  "created_by": 1,
  "assigned_to": 1,
  "assigned_to_name": "string",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z",
  "submission_deadline": "2026-01-15",
  "days_until_deadline": 1,
  "is_overdue": true
}
```

---

## POST `/api/v1/vat/work-items/{item_id}/send-back`
**Summary:** Send Back For Correction

### 📥 Request Body (JSON)
```json
{
  "correction_note": "string"
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "business_status": "active",
  "period": "string",
  "period_type": "monthly",
  "status": "pending_materials",
  "pending_materials_note": "string",
  "total_output_vat": "string",
  "total_input_vat": "string",
  "net_vat": "string",
  "total_output_net": "string",
  "total_input_net": "string",
  "final_vat_amount": "string",
  "is_overridden": true,
  "override_justification": "string",
  "submission_method": "online",
  "filed_at": "2026-01-15T10:30:00Z",
  "filed_by": 1,
  "filed_by_name": "string",
  "submission_reference": "string",
  "is_amendment": false,
  "amends_item_id": 1,
  "created_by": 1,
  "assigned_to": 1,
  "assigned_to_name": "string",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z",
  "submission_deadline": "2026-01-15",
  "days_until_deadline": 1,
  "is_overdue": true
}
```

---

## POST `/api/v1/vat/work-items/{item_id}/file`
**Summary:** File Vat Return

### 📥 Request Body (JSON)
```json
{
  "submission_method": "online",
  "override_amount": 1.0,
  "override_justification": "string",
  "submission_reference": "string",
  "is_amendment": false,
  "amends_item_id": 1
}
```

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "business_status": "active",
  "period": "string",
  "period_type": "monthly",
  "status": "pending_materials",
  "pending_materials_note": "string",
  "total_output_vat": "string",
  "total_input_vat": "string",
  "net_vat": "string",
  "total_output_net": "string",
  "total_input_net": "string",
  "final_vat_amount": "string",
  "is_overridden": true,
  "override_justification": "string",
  "submission_method": "online",
  "filed_at": "2026-01-15T10:30:00Z",
  "filed_by": 1,
  "filed_by_name": "string",
  "submission_reference": "string",
  "is_amendment": false,
  "amends_item_id": 1,
  "created_by": 1,
  "assigned_to": 1,
  "assigned_to_name": "string",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z",
  "submission_deadline": "2026-01-15",
  "days_until_deadline": 1,
  "is_overdue": true
}
```

---

## GET `/api/v1/vat/work-items/{item_id}`
**Summary:** Get Work Item

### 📤 Success Response (200)
```json
{
  "id": 1,
  "business_id": 1,
  "business_name": "string",
  "business_status": "active",
  "period": "string",
  "period_type": "monthly",
  "status": "pending_materials",
  "pending_materials_note": "string",
  "total_output_vat": "string",
  "total_input_vat": "string",
  "net_vat": "string",
  "total_output_net": "string",
  "total_input_net": "string",
  "final_vat_amount": "string",
  "is_overridden": true,
  "override_justification": "string",
  "submission_method": "online",
  "filed_at": "2026-01-15T10:30:00Z",
  "filed_by": 1,
  "filed_by_name": "string",
  "submission_reference": "string",
  "is_amendment": false,
  "amends_item_id": 1,
  "created_by": 1,
  "assigned_to": 1,
  "assigned_to_name": "string",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z",
  "submission_deadline": "2026-01-15",
  "days_until_deadline": 1,
  "is_overdue": true
}
```

---

## GET `/api/v1/vat/businesses/{business_id}/work-items`
**Summary:** List Business Work Items

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "business_name": "string",
      "business_status": "active",
      "period": "string",
      "period_type": "monthly",
      "status": "pending_materials",
      "pending_materials_note": "string",
      "total_output_vat": "string",
      "total_input_vat": "string",
      "net_vat": "string",
      "total_output_net": "string",
      "total_input_net": "string",
      "final_vat_amount": "string",
      "is_overridden": true,
      "override_justification": "string",
      "submission_method": "online",
      "filed_at": "2026-01-15T10:30:00Z",
      "filed_by": 1,
      "filed_by_name": "string",
      "submission_reference": "string",
      "is_amendment": false,
      "amends_item_id": 1,
      "created_by": 1,
      "assigned_to": 1,
      "assigned_to_name": "string",
      "created_at": "2026-01-15T10:30:00Z",
      "updated_at": "2026-01-15T10:30:00Z",
      "submission_deadline": "2026-01-15",
      "days_until_deadline": 1,
      "is_overdue": true
    }
  ],
  "total": 1
}
```

---

## GET `/api/v1/vat/work-items/{item_id}/audit`
**Summary:** Get Audit Trail

### 📤 Success Response (200)
```json
{
  "items": [
    {
      "id": 1,
      "work_item_id": 1,
      "performed_by": 1,
      "performed_by_name": "string",
      "action": "string",
      "old_value": "string",
      "new_value": "string",
      "note": "string",
      "performed_at": "2026-01-02T03:04:05Z"
    }
  ]
}
```

---

## GET `/api/v1/vat/businesses/{business_id}/summary`
**Summary:** Get Vat Business Summary

### 📤 Success Response (200)
```json
{
  "business_id": 1,
  "periods": [
    {
      "work_item_id": 0,
      "period": "string",
      "status": "pending_materials",
      "total_output_vat": "123.45",
      "total_input_vat": "123.45",
      "net_vat": "123.45",
      "total_output_net": "123.45",
      "total_input_net": "123.45",
      "final_vat_amount": "123.45",
      "filed_at": "2026-01-02T03:04:05Z"
    }
  ],
  "annual": [
    {
      "year": 1,
      "total_output_vat": "123.45",
      "total_input_vat": "123.45",
      "net_vat": "123.45",
      "periods_count": 1,
      "filed_count": 1
    }
  ]
}
```

---

## GET `/api/v1/vat/businesses/{business_id}/export`
**Summary:** Export Vat Business

### 📤 Success Response (200)
```text
Binary file response (download stream)

Variant 1 (format=pdf)
Content-Type: application/pdf
Content-Disposition: attachment; filename="vat_business_42_2026.pdf"

Variant 2 (format=excel)
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="vat_business_42_2026.xlsx"

Body: <binary bytes>
```

---

