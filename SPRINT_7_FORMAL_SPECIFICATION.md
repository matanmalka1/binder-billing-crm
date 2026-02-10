Sprint 7 – Frontend Enablement & API Consumption

Status: DRAFT
Project: Binder & Billing CRM
Precondition: Backend frozen through Sprint 6

⸻

1. Purpose

Sprint 7 is a documentation & enablement sprint.

Its purpose is to transform the existing, frozen backend (Sprint 6) into a clear, safe, and predictable API surface for frontend development, without introducing any new backend logic, behavior, or endpoints.

Sprint 7 focuses on:
	•	API usage clarity
	•	Frontend–backend responsibility boundaries
	•	Developer experience (DX)
	•	Elimination of ambiguity for UI implementation

⸻

2. Scope Definition

2.1 In Scope

Sprint 7 includes documentation-only deliverables that describe how to correctly consume the existing backend.

The following areas are in scope:
	1.	API Consumption Guide
	2.	Concrete API Examples
	3.	UI State Mapping
	4.	Frontend Role & Permission Matrix
	5.	Frontend Readiness Checklist

No backend behavior changes are allowed.

⸻

2.2 Out of Scope

The following are explicitly out of scope:
	•	❌ Any backend code changes
	•	❌ Any new API endpoints
	•	❌ Any response shape changes
	•	❌ Any business logic changes
	•	❌ UI / frontend implementation
	•	❌ Analytics, reporting, or dashboards redesign
	•	❌ Client portal features

Sprint 7 must not modify or invalidate the Sprint 6 freeze.

⸻

3. Architectural Principles

Sprint 7 is governed by the following principles:
	1.	Backend is authoritative
	•	SLA, signals, work state, attention logic are derived server-side.
	2.	Frontend is a consumer, not a decision maker
	•	UI must not recompute or infer business state.
	3.	No duplication of logic
	•	Frontend reacts to backend-derived fields only.
	4.	Explicit contracts
	•	No “assumed behavior” or hidden logic.

⸻

4. Deliverables

Sprint 7 must produce the following Markdown documents.

⸻

4.1 FRONTEND_API_GUIDE.md

A practical guide for frontend developers describing how to call the API correctly.

Required sections:
	•	Authentication flow (login → JWT usage)
	•	Required headers
	•	Pagination (limit, offset)
	•	Filtering conventions:
	•	sla_state
	•	signal_type
	•	work_state
	•	Error handling:
	•	400 / 401 / 403 / 404 / 409
	•	Idempotency and retry safety notes

⸻

4.2 API_EXAMPLES.md

Concrete, real-world examples of API usage.

Must include:
	•	Dashboard endpoints (work-queue, alerts, attention)
	•	Search with multiple filters
	•	Timeline response example
	•	Charges lifecycle example
	•	Notifications history example

All examples must reflect actual response shapes from Sprint 6.

⸻

4.3 UI_STATE_MAPPING.md

Defines how frontend UI should interpret backend-derived fields.

Examples:
	•	work_state = awaiting_documents → informational badge
	•	signal = overdue_binder → red alert
	•	attention = unpaid_charge → payment CTA

Rules:
	•	No frontend recomputation
	•	No fallback logic
	•	Backend fields are final

⸻

4.4 FRONTEND_ROLES_MATRIX.md

Defines what each role may see or trigger from the frontend perspective.

Roles:
	•	Advisor
	•	Secretary

Must include:
	•	Read permissions
	•	Action visibility
	•	Disabled/hidden UI behavior

⸻

4.5 FRONTEND_READINESS_CHECKLIST.md

A validation checklist for frontend readiness.

Must include:
	•	What endpoints exist
	•	What endpoints intentionally do not exist
	•	What frontend must never assume
	•	What always comes from backend (SLA, signals, attention)

⸻

5. API Contract Alignment

Sprint 7 must fully align with:
	•	API_CONTRACT.md
	•	Sprint 6 behavior

Sprint 7 must not reinterpret or extend the API contract.

Any ambiguity must be resolved in documentation only.

⸻

6. Change Policy
	•	Sprint 7 does not allow backend changes.
	•	Any requested backend change discovered during Sprint 7 must be deferred to Sprint 8+.
	•	Sprint 7 output must not invalidate existing tests.

⸻

7. Completion Criteria

Sprint 7 is considered complete when:
	•	All deliverable documents exist
	•	Documentation matches the frozen backend exactly
	•	Frontend developers can implement UI without backend clarification
	•	No code changes are introduced
	•	No contradictions exist between documents

⸻

8. Sprint 7 Exit Status

On completion, the project state becomes:

Backend frozen through Sprint 6
Frontend-enabled through Sprint 7
Ready for UI development

⸻

End of Sprint 7 Formal Specification