# backAndFront_GAPS — Task List

Full audit + fix plan for all sync gaps between backend and frontend.
Each task is self-contained with the exact files to touch and what to change.

**Status: ALL 11 TASKS COMPLETE** ✓

---

## TASK 1 — Add `GET /annual-reports/{id}/history` endpoint ✅
**Severity**: Critical | **Domain**: Annual Reports | **Side**: Backend

### Problem
Frontend calls `GET /annual-reports/{id}/history` on every report detail load.
Backend has the service method (`get_status_history()`) and schema (`StatusHistoryResponse`) but no HTTP route — every call 404s.

### Files to change

**`app/annual_reports/api/annual_report_status.py`** (currently 69 lines)
- Add import: `StatusHistoryResponse` from `app.annual_reports.schemas`
- Add endpoint:
  ```python
  @router.get("/{report_id}/history", response_model=list[StatusHistoryResponse])
  def get_status_history(report_id: int, db: DBSession, user: CurrentUser):
      service = AnnualReportService(db)
      return service.get_status_history(report_id)
  ```

### Reuse
- Service method: `app/annual_reports/services/query_service.py:45-47` — `get_status_history(report_id)`
- Schema: `StatusHistoryResponse` already in `app/annual_reports/schemas/annual_report.py`

### Notes
- No migrations
- No new files
- File stays under 150 lines

---

## TASK 2 — Add `POST /annual-reports/{id}/submit` endpoint + wire frontend button ✅
**Severity**: Critical | **Domain**: Annual Reports | **Side**: Backend + Frontend

### Problem
Frontend `annualReportStatusApi.submitReport()` posts to `POST /annual-reports/{id}/submit` with `{ submitted_at?, ita_reference?, note? }`. Backend has no route — 404 every time. The frontend function is also imported but never invoked — no button calls it.

### Files to change

**`app/annual_reports/schemas/annual_report.py`**
- Add schema (if not already present):
  ```python
  class SubmitRequest(BaseModel):
      submitted_at: Optional[datetime] = None
      ita_reference: Optional[str] = None
      note: Optional[str] = None
  ```

**`app/annual_reports/api/annual_report_status.py`**
- Import `SubmitRequest` from `app.annual_reports.schemas`
- Add endpoint:
  ```python
  @router.post("/{report_id}/submit", response_model=AnnualReportDetailResponse)
  def submit_report(report_id: int, body: SubmitRequest, db: DBSession, user: CurrentUser):
      service = AnnualReportService(db)
      return service.transition_status(
          report_id=report_id,
          new_status="submitted",
          changed_by=user.id,
          changed_by_name=user.full_name,
          note=body.note,
          ita_reference=body.ita_reference,
      )
  ```

**`src/features/annualReports/hooks/useReportDetail.ts`** (frontend)
- `submitReport()` is already imported from `annualReportStatusApi` but never called
- Wire it to a `useMutation` and expose it from the hook so a UI button can call it

### Reuse
- `status_service.py:24-81` — `transition_status()` handles all the logic, no new service code needed
- `SubmitRequest` and `StatusHistoryResponse` already exported from `app/annual_reports/schemas/__init__.py`

### Notes
- No migrations
- `SubmitRequest` schema may already exist — verify before adding

---

## TASK 3 — Add `POST /annual-reports/{id}/transition` endpoint (fixes Kanban drag-drop) ✅
**Severity**: Critical | **Domain**: Annual Reports | **Side**: Backend

### Problem
Every Kanban column drag calls `annualReportStatusApi.transitionStage(reportId, newStage)` → `POST /annual-reports/{id}/transition` with `{ to_stage: StageKey }`. This endpoint does not exist — every card drag is a silent 404.

### Stage → Status mapping
Reverse of the Kanban view mapping in `query_service.py:125-134`:

| to_stage | target status |
|---|---|
| `material_collection` | `collecting_docs` |
| `in_progress` | `docs_complete` |
| `final_review` | `in_preparation` |
| `client_signature` | `pending_client` |
| `transmitted` | `submitted` |

### Files to change

**New file: `app/annual_reports/api/annual_report_kanban.py`** (~40 lines)
```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.schemas import AnnualReportDetailResponse
from app.annual_reports.services import AnnualReportService

router = APIRouter(
    prefix="/annual-reports",
    tags=["annual-reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)

STAGE_TO_STATUS = {
    "material_collection": "collecting_docs",
    "in_progress": "docs_complete",
    "final_review": "in_preparation",
    "client_signature": "pending_client",
    "transmitted": "submitted",
}

class StageTransitionRequest(BaseModel):
    to_stage: str

@router.post("/{report_id}/transition", response_model=AnnualReportDetailResponse)
def transition_stage(report_id: int, body: StageTransitionRequest, db: DBSession, user: CurrentUser):
    target_status = STAGE_TO_STATUS.get(body.to_stage)
    if not target_status:
        raise HTTPException(status_code=400, detail=f"Unknown stage: {body.to_stage}")
    service = AnnualReportService(db)
    return service.transition_status(
        report_id=report_id,
        new_status=target_status,
        changed_by=user.id,
        changed_by_name=user.full_name,
    )
```

**`app/annual_reports/api/__init__.py`**
- Import and export `annual_report_kanban`

**`app/main.py`**
- Include `annual_report_kanban.router` with prefix `/api/v1`

### Notes
- No migrations
- 1 new backend file
- `StageTransitionRequest` may already exist in schemas — if so, import from there instead

---

## TASK 4 — Add `GET /annual-reports/{id}/schedules` endpoint ✅
**Severity**: Critical | **Domain**: Annual Reports | **Side**: Backend

### Problem
Frontend calls `GET /annual-reports/{id}/schedules` explicitly. Backend `annual_report_schedule.py` only has `POST /schedules` and `POST /schedules/complete` — no GET. Returns 404.

### Files to change

**`app/annual_reports/api/annual_report_schedule.py`** (currently 34 lines)
- Add endpoint:
  ```python
  @router.get("/{report_id}/schedules", response_model=list[ScheduleEntryResponse])
  def list_schedules(report_id: int, db: DBSession, user: CurrentUser):
      from app.annual_reports.models.annual_report_schedule import AnnualReportSchedule
      schedules = db.query(AnnualReportSchedule).filter_by(annual_report_id=report_id).all()
      return [ScheduleEntryResponse.model_validate(s) for s in schedules]
  ```

### Reuse
- `ScheduleEntryResponse` already defined in `app/annual_reports/schemas/annual_report.py:66-76`
- `AnnualReportSchedule` ORM model already in `app/annual_reports/models/`

### Notes
- No migrations
- No new files
- File goes from 34 → ~48 lines

---

## TASK 5 — Wire `is_active` filter in users list ✅
**Severity**: Critical | **Domain**: Users | **Side**: Backend

### Problem
Frontend filter dropdown (כל המשתמשים / פעילים בלבד / לא פעילים) sends `is_active=true` or `is_active=false` as a query param. Backend `list_users` endpoint only accepts `page` and `page_size` — the param is silently dropped and all users are always returned.

### Files to change

**`app/users/repositories/user_repository.py`**
- Add `is_active: Optional[bool] = None` to `list()` signature
- Add `is_active: Optional[bool] = None` to `count()` signature
- In both: add `.filter(User.is_active == is_active)` when `is_active is not None`

**`app/users/services/user_management_service.py`**
- Add `is_active: Optional[bool] = None` to `list_users()` signature
- Pass `is_active=is_active` to the repository call

**`app/users/api/users.py`** (lines 35–44)
- Add `is_active: Optional[bool] = Query(None)` to the `list_users` endpoint
- Pass `is_active=is_active` to the service call

### Notes
- No migrations (filtering on existing `is_active` column)
- No new files
- 3 mechanical file edits

---

## TASK 6 — Fix `available_actions` TypeScript type ✅
**Severity**: Medium | **Domain**: Annual Reports | **Side**: Frontend

### Problem
Backend sends each action as `{ id, key, label, method, endpoint, payload?, confirm? }`.
Frontend types it as `{ action: string; label: string }[]`.
Any code reading `item.action` gets `undefined` (backend sends `key`).
Fields `id`, `method`, `endpoint`, `payload`, `confirm` are invisible to TypeScript.

### Files to change

**`src/api/annualReports.api.ts`** (line ~69)
- Replace the `available_actions` field type on `AnnualReportFull`:
  ```typescript
  available_actions?: {
    id: string;
    key: string;
    label: string;
    method: string;
    endpoint: string;
    payload?: Record<string, unknown>;
    confirm?: {
      title: string;
      message: string;
      confirm_label: string;
      cancel_label: string;
    };
  }[];
  ```
- Search for any component reading `item.action` and change to `item.key`

### Notes
- No backend changes
- No new files

---

## TASK 7 — Add `token` field to `LoginResponse` type ✅
**Severity**: Low | **Domain**: Auth | **Side**: Frontend

### Problem
Backend `LoginResponse` returns `{ token: str, user: UserResponse }` plus an HttpOnly cookie.
Frontend `LoginResponse` interface has no `token` field — the value is silently discarded.
Cookie-based auth works fine, but the type is incorrect.

### Files to change

**`src/api/auth.api.ts`**
- Add `token?: string` to the `LoginResponse` interface

### Notes
- No backend changes
- No behavioral change — cookie auth continues to work
- No new files

---

## TASK 8 — Wire charge cancel reason (API + UI) ✅
**Severity**: Low | **Domain**: Charges | **Side**: Frontend

### Problem
Backend `POST /charges/{id}/cancel` accepts `{ reason?: string }` (via `default_factory` so empty body is tolerated).
Frontend sends no body at all — cancel reason is permanently `null` in every record.
No UI input field exists for the user to enter a reason.

### Files to change

**`src/api/charges.api.ts`** (lines 86–91)
- Update the `cancel` function signature and body:
  ```typescript
  cancel: async (chargeId: number, reason?: string): Promise<ChargeAdvisorResponse> => {
    const response = await api.post<ChargeAdvisorResponse>(
      ENDPOINTS.chargeCancel(chargeId),
      reason ? { reason } : undefined,
    );
    return response.data;
  },
  ```

**`src/features/charges/components/ChargeDetailDrawer.tsx`**
- The drawer already uses a `ConfirmDialog` for the cancel action
- Add local state: `const [cancelReason, setCancelReason] = useState("")`
- Add an optional `<textarea>` inside the confirm dialog labelled `"סיבת ביטול (אופציונלי)"`
- Pass `cancelReason || undefined` to `chargesApi.cancel(id, reason)`

### Notes
- No backend changes
- No new files

---

## TASK 9 — Add `token_version` to `UserResponse` type ✅
**Severity**: Low | **Domain**: Users | **Side**: Frontend

### Problem
Backend `UserManagementResponse` schema includes `token_version: int`.
Frontend `UserResponse` interface omits it — the field is present in every API response but inaccessible to TypeScript.

### Files to change

**`src/api/users.api.ts`** (lines 8–17)
- Add `token_version: number` to the `UserResponse` interface

### Notes
- No backend changes
- No new files
- Internal security field — no UI display needed, just type completeness

---

## TASK 10 — Add binder history section to BinderDrawer ✅
**Severity**: Low | **Domain**: Binders | **Side**: Frontend

### Problem
`GET /binders/{id}/history` exists on the backend and returns full status change log.
`bindersApi.getHistory()` is defined in `binders.api.ts` but never called.
`BinderDrawer` has no history tab or section — the feature is completely invisible to users.

### Files to change

**`src/lib/queryKeys.ts`**
- Add to `QK.binders` (if not already present):
  ```typescript
  history: (id: number | string) => ["binders", "history", id] as const,
  ```

**New file: `src/features/binders/components/BinderHistorySection.tsx`**
- Props: `binderId: number`
- Fetch using `useQuery`:
  ```typescript
  const { data: history, isLoading } = useQuery({
    queryKey: QK.binders.history(binderId),
    queryFn: () => bindersApi.getHistory(binderId),
  });
  ```
- Render a `DrawerSection` titled `"היסטוריית שינויים"`
- Each `BinderHistoryEntry` has: `old_status`, `new_status`, `changed_by`, `changed_at`, `notes?`
- Display as a timeline list: `old_status → new_status`, formatted date, optional notes
- Follow the styling of existing timeline/history components in the codebase

**`src/features/binders/components/BinderDrawer.tsx`**
- In the `detail` mode block, after `<BinderDetailsPanel />`, add:
  ```tsx
  <BinderHistorySection binderId={binder.id} />
  ```

### Notes
- No backend changes
- 1 new frontend file (`BinderHistorySection.tsx`)

---

## TASK 11 — Embed annual report status history timeline ✅
**Severity**: Low | **Domain**: Annual Reports | **Side**: Frontend
**Prerequisite**: Task 1 must be completed first (backend `/history` endpoint)

### Problem
`StatusHistoryTimeline` component exists and is fully implemented.
`annualReportsApi.getHistory(reportId)` is defined.
Neither is called from any rendered component — status history is completely invisible to users.

### Files to change

**`src/lib/queryKeys.ts`**
- Add to `QK.tax.annualReports` (or equivalent):
  ```typescript
  statusHistory: (id: number | string) => ["tax", "annual-reports", "status-history", id] as const,
  ```

**`src/features/annualReports/components/AnnualReportOverviewSection.tsx`**
- Add query:
  ```typescript
  const { data: history } = useQuery({
    queryKey: QK.tax.annualReports.statusHistory(reportId),
    queryFn: () => annualReportsApi.getHistory(reportId),
    enabled: !!reportId,
  });
  ```
- Render after existing sections:
  ```tsx
  <StatusHistoryTimeline entries={history ?? []} />
  ```

### Notes
- No backend changes beyond Task 1
- No new files
- `StatusHistoryTimeline` component and `getHistory()` API function already exist

---

## Summary Table

| Task | Domain | Type | Severity | BE Files | FE Files | New Files |
|------|--------|------|----------|----------|----------|-----------|
| 1 | Annual Reports | Missing backend endpoint | **Critical** | 1 | 0 | 0 |
| 2 | Annual Reports | Missing backend endpoint + dead FE code | **Critical** | 2 | 1 | 0 |
| 3 | Annual Reports | Missing backend endpoint — Kanban broken | **Critical** | 3 | 0 | 1 BE |
| 4 | Annual Reports | Missing backend endpoint | **Critical** | 1 | 0 | 0 |
| 5 | Users | Silently ignored filter | **Critical** | 3 | 0 | 0 |
| 6 | Annual Reports | Wrong TypeScript type | Medium | 0 | 1 | 0 |
| 7 | Auth | Incomplete TypeScript type | Low | 0 | 1 | 0 |
| 8 | Charges | Missing UI + unused backend field | Low | 0 | 2 | 0 |
| 9 | Users | Incomplete TypeScript type | Low | 0 | 1 | 0 |
| 10 | Binders | Missing UI component | Low | 0 | 2 | 1 FE |
| 11 | Annual Reports | Missing UI component (needs Task 1) | Low | 0 | 2 | 0 |

**No Alembic migrations required for any task.**
All backend changes expose existing service/schema/model infrastructure via new HTTP routes or add filter params.
