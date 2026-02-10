# API Examples (Response Shapes Match Frozen Sprint 6 Backend)

All examples use base path `/api/v1` and JSON requests unless stated otherwise.

## Authentication: Login and Using the Token

### Request

`POST /api/v1/auth/login`

```json
{
  "email": "test@example.com",
  "password": "password123"
}
```

### Response `200`

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "full_name": "Test User",
    "role": "advisor"
  }
}
```

Use the token for authenticated calls:

- `Authorization: Bearer <token>`

---

## Dashboard: Work Queue

`GET /api/v1/dashboard/work-queue?page=1&page_size=20`

### Response `200`

```json
{
  "items": [
    {
      "binder_id": 10,
      "client_id": 123,
      "client_name": "Example Corp",
      "binder_number": "WQ-001",
      "work_state": "in_progress",
      "signals": ["near_sla"],
      "days_since_received": 5,
      "expected_return_at": "2026-05-06"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

---

## Dashboard: Alerts

`GET /api/v1/dashboard/alerts`

### Response `200`

```json
{
  "items": [
    {
      "binder_id": 11,
      "client_id": 124,
      "client_name": "Another Corp",
      "binder_number": "BND-011",
      "alert_type": "overdue",
      "days_overdue": 7,
      "days_remaining": null
    },
    {
      "binder_id": 12,
      "client_id": 125,
      "client_name": "Near SLA Ltd",
      "binder_number": "BND-012",
      "alert_type": "near_sla",
      "days_overdue": null,
      "days_remaining": 12
    }
  ],
  "total": 2
}
```

---

## Dashboard: Attention

`GET /api/v1/dashboard/attention`

### Response `200` (advisor includes unpaid charges)

```json
{
  "items": [
    {
      "item_type": "idle_binder",
      "binder_id": 13,
      "client_id": 126,
      "client_name": "Idle Co",
      "description": "Binder IDLE-013 idle for 30 days"
    },
    {
      "item_type": "ready_for_pickup",
      "binder_id": 14,
      "client_id": 127,
      "client_name": "Pickup Co",
      "description": "Binder BND-014 ready for pickup"
    },
    {
      "item_type": "unpaid_charge",
      "binder_id": null,
      "client_id": 128,
      "client_name": "Billing Co",
      "description": "Unpaid charge: 1500.0 ILS"
    }
  ],
  "total": 3
}
```

---

## Search: Combined Filters

`GET /api/v1/search?query=BND&work_state=in_progress&sla_state=approaching&signal_type=near_sla&signal_type=idle_binder&has_signals=true&page=1&page_size=20`

### Response `200`

```json
{
  "results": [
    {
      "result_type": "binder",
      "client_id": 123,
      "client_name": "Example Corp",
      "binder_id": 10,
      "binder_number": "BND-010",
      "work_state": "in_progress",
      "signals": ["near_sla"]
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

---

## Client Timeline

`GET /api/v1/clients/123/timeline?page=1&page_size=50`

### Response `200`

```json
{
  "client_id": 123,
  "events": [
    {
      "event_type": "invoice_attached",
      "timestamp": "2026-02-10T12:30:00",
      "binder_id": null,
      "charge_id": 5,
      "description": "Invoice attached: INV-2026-0005",
      "metadata": {
        "provider": "external_provider",
        "external_invoice_id": "INV-2026-0005"
      }
    },
    {
      "event_type": "charge_paid",
      "timestamp": "2026-02-10T12:00:00",
      "binder_id": null,
      "charge_id": 5,
      "description": "Charge paid: one_time",
      "metadata": {
        "amount": 1500.0
      }
    },
    {
      "event_type": "notification_sent",
      "timestamp": "2026-02-01T09:00:00",
      "binder_id": 10,
      "charge_id": null,
      "description": "Notification: binder_approaching_sla",
      "metadata": {
        "trigger": "binder_approaching_sla",
        "channel": "whatsapp"
      }
    },
    {
      "event_type": "binder_received",
      "timestamp": "2026-01-01T00:00:00",
      "binder_id": 10,
      "charge_id": null,
      "description": "Binder BND-010 received",
      "metadata": {
        "binder_number": "BND-010"
      }
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 4
}
```

---

## Charge Lifecycle Example (Draft → Issued → Paid)

### 1) Create Charge (advisor-only)

`POST /api/v1/charges`

```json
{
  "client_id": 123,
  "amount": 120.0,
  "charge_type": "one_time",
  "period": "2026-02",
  "currency": "ILS"
}
```

Response `201`:

```json
{
  "id": 5,
  "client_id": 123,
  "amount": 120.0,
  "currency": "ILS",
  "charge_type": "one_time",
  "period": "2026-02",
  "status": "draft",
  "created_at": "2026-02-10T10:00:00",
  "issued_at": null,
  "paid_at": null
}
```

### 2) Issue Charge (advisor-only)

`POST /api/v1/charges/5/issue`

Response `200`:

```json
{
  "id": 5,
  "client_id": 123,
  "amount": 120.0,
  "currency": "ILS",
  "charge_type": "one_time",
  "period": "2026-02",
  "status": "issued",
  "created_at": "2026-02-10T10:00:00",
  "issued_at": "2026-02-10T10:05:00",
  "paid_at": null
}
```

### 3) Mark Paid (advisor-only)

`POST /api/v1/charges/5/mark-paid`

Response `200`:

```json
{
  "id": 5,
  "client_id": 123,
  "amount": 120.0,
  "currency": "ILS",
  "charge_type": "one_time",
  "period": "2026-02",
  "status": "paid",
  "created_at": "2026-02-10T10:00:00",
  "issued_at": "2026-02-10T10:05:00",
  "paid_at": "2026-02-10T10:10:00"
}
```

### Invalid Transition Example (`400`)

`POST /api/v1/charges/5/issue` (re-issuing a non-draft charge)

```json
{
  "detail": "Cannot issue charge with status paid",
  "error": {
    "type": "http_error",
    "detail": "Cannot issue charge with status paid",
    "status_code": 400
  }
}
```

