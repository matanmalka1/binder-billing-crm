# Binder & Billing CRM
## API Contracts (Sprint 1)

---

## 1. Conventions
1. Base path: `/api/v1`
2. Content type: `application/json`
3. Auth: Bearer token
4. IDs are integers (`1, 2, 3, ...`)
5. Timestamps are ISO 8601 UTC strings

---

## 2. Standard Error Shape
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "pickup_person_name is required",
    "details": [
      {
        "field": "pickup_person_name",
        "reason": "required"
      }
    ]
  }
}
```

---

## 3. Auth
## 3.1 Login
`POST /api/v1/auth/login`

Request:
```json
{
  "email": "secretary@office.local",
  "password": "********"
}
```

Response `200`:
```json
{
  "token": "jwt-token",
  "user": {
    "id": 1,
    "full_name": "Office Secretary",
    "role": "secretary"
  }
}
```

---

## 4. Clients
## 4.1 Create Client
`POST /api/v1/clients`

Request:
```json
{
  "full_name": "Dana Levi",
  "id_number": "123456789",
  "client_type": "osek_murshe",
  "phone": "0501234567",
  "email": "dana@example.com",
  "opened_at": "2026-02-08"
}
```

Response `201`:
```json
{
  "id": 12,
  "full_name": "Dana Levi",
  "id_number": "123456789",
  "status": "active"
}
```

## 4.2 List Clients
`GET /api/v1/clients?page=1&page_size=20&status=active`

Response `200`:
```json
{
  "items": [
    {
      "id": 12,
      "full_name": "Dana Levi",
      "client_type": "osek_murshe",
      "status": "active"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

## 4.3 Get Client
`GET /api/v1/clients/{id}`

Response `200`:
```json
{
  "id": 12,
  "full_name": "Dana Levi",
  "id_number": "123456789",
  "status": "active"
}
```

## 4.4 Update Client
`PATCH /api/v1/clients/{id}`

Request:
```json
{
  "phone": "0520000000",
  "status": "frozen"
}
```

Response `200`:
```json
{
  "id": 12,
  "phone": "0520000000",
  "status": "frozen"
}
```

---

## 5. Binders
## 5.1 Receive Binder
`POST /api/v1/binders/receive`

Request:
```json
{
  "client_id": 12,
  "binder_number": "BND-2026-001",
  "received_at": "2026-02-08",
  "received_by": 1,
  "notes": "Monthly reporting material"
}
```

Response `201`:
```json
{
  "id": 41,
  "client_id": 12,
  "binder_number": "BND-2026-001",
  "status": "in_office",
  "expected_return_at": "2026-05-09"
}
```

## 5.2 Return Binder
`POST /api/v1/binders/{id}/return`

Request:
```json
{
  "pickup_person_name": "Avi Cohen",
  "returned_by": 1
}
```

Response `200`:
```json
{
  "id": 41,
  "status": "returned",
  "returned_at": "2026-02-10",
  "pickup_person_name": "Avi Cohen"
}
```

## 5.3 List Binders
`GET /api/v1/binders?status=in_office&client_id=12`

Response `200`:
```json
{
  "items": [
    {
      "id": 41,
      "binder_number": "BND-2026-001",
      "status": "in_office",
      "received_at": "2026-02-08",
      "expected_return_at": "2026-05-09",
      "days_in_office": 0
    }
  ]
}
```

---

## 6. Dashboard
## 6.1 Summary
`GET /api/v1/dashboard/summary`

Response `200`:
```json
{
  "binders_in_office": 14,
  "binders_ready_for_pickup": 3,
  "binders_overdue": 2
}
```

---

## 7. HTTP Status Codes
1. `200` success
2. `201` created
3. `400` validation error
4. `401` unauthenticated
5. `403` forbidden by role
6. `404` not found
7. `409` conflict (duplicate or active binder rule)
8. `500` internal server error

---

*End of API Contracts*
