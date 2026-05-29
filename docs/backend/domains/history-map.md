## Scope
This file owns only:
- Reference map of history, timeline, and audit surfaces across the frontend.

This file must not contain:
- Canonical product behavior.
- Current implemented behavior unless verified against the owning domain README.
- Canonical architecture rules.

Source of truth: reference

# Frontend History, Timeline, and Audit Map

Purpose: map current frontend usages before expanding generic audit UI. This is documentation only; no shared component work is included here.

Last backend endpoint check: 2026-05-29, against `backend/openapi.json` and routers under `backend/app/**/api`.

## Client Timeline

- Feature/domain: `timeline`, rendered from client details.
- Components: `ClientTimelineTab`, `TimelineCommandBar`, `TimelineCard`, `TimelineEventItem`.
- API endpoint: `GET /api/v1/clients/{clientId}/timeline`.
- Query key: `timelineQK.clientEvents(clientId, params)` -> `['timeline', 'client', clientId, 'events', params]`.
- Represents: business timeline / operational timeline across client-related events.
- Future sharing: keep separate. It has filtering, grouping, event actions, and timeline-specific metadata that differ from audit tables.
- Bad naming found: none. `timeline` / `ציר זמן` is accurate here.

## Client Generic Audit Trail

- Feature/domain: `clients`.
- Components: `ClientAuditTrailSection`, rendered from `ClientDetailsOverviewTab` when the active tab is `history`.
- API endpoint: `GET /api/v1/audit/client/{clientId}?limit=50&offset=0`, implemented by the generic route `GET /api/v1/audit/{entity_type}/{entity_id}`.
- Query key: `clientsQK.auditTrail(clientId, params)` -> `['clients', 'audit', clientId, params ?? null]`.
- Represents: audit trail for generic entity changes on a client record.
- Future sharing: can later share a generic audit table/formatter with other generic audit entities such as business, charge, and annual report after those UIs exist.
- Bad naming found: route/tab label uses `history` / `היסטוריה`, while API and hook correctly use `auditTrail`. Acceptable for user-facing Hebrew, but code should prefer `AuditTrail` for generic audit.

## VAT Work Item History

- Feature/domain: `vatReports`.
- Components: `VatHistoryTab`, `history.utils.ts`, `history.constants.ts`.
- API endpoint: `GET /api/v1/vat/work-items/{id}/audit?limit=50&offset=0`.
- Query key: `vatReportsQK.audit(id, params)` -> `['tax', 'vat-work-items', 'audit', id, params ?? null]`.
- Represents: VAT work-item audit trail, including status and invoice/data-entry events.
- Future sharing: can share table chrome and pagination patterns later, but should not merge data model or formatter with generic entity audit. VAT has its own audit endpoint and domain-specific payload formatter.
- Bad naming found: UI/file names say `History`, while API/query names say `audit`. This is user-friendly but ambiguous in code.

## Annual Report Status History

- Feature/domain: `annualReports`.
- Components: `StatusHistoryTimeline`, used in `AnnualReportOverviewSection`.
- API endpoint: `GET /api/v1/annual-reports/{id}/history`.
- Query key: `annualReportsQK.statusHistory(id)` -> `['tax', 'annual-reports', 'status-history', id]`.
- Represents: status history only, not full audit.
- Future sharing: keep separate from generic audit. It is a status-transition timeline with badges and notes, not a field-level audit table.
- Bad naming found: endpoint/API method `getHistory` is broad; query key `statusHistory` is clearer.

## Annual Report Filing Timeline

- Feature/domain: `annualReports`.
- Components: `FilingTimelineTab`, `TimelineEvent`, `UpcomingDeadlinesList`, helper `buildTimelineEvents`.
- API endpoint: no dedicated history endpoint; uses annual report data already loaded in the panel/client annual reports flow.
- Query key: no dedicated timeline/history query key.
- Represents: filing lifecycle/timeline view derived from annual report records and deadlines.
- Future sharing: keep separate. This is derived UI state, not an audit trail.
- Bad naming found: component `TimelineEvent` lives under `statusTransition` but is also used for filing timeline display. That name/location is broader than status transitions and may be confusing later.

## Annual Report Report History Table

- Feature/domain: `annualReports`.
- Components: `ReportHistoryTable`, used in `AnnualReportOverviewSection`.
- API endpoint: `GET /api/v1/clients/{clientId}/annual-reports`.
- Query key: `annualReportsQK.forClient(clientId)` -> `['tax', 'annual-reports', 'client', clientId]`.
- Represents: previous/current annual report records for a client, not audit.
- Future sharing: keep separate from audit and status history.
- Bad naming found: `ReportHistoryTable` means historical annual reports, not change history. Consider `ClientAnnualReportsHistoryTable` or `ClientReportYearsTable` later.

## Binder Lifecycle History

- Feature/domain: `binders`.
- Components: `BinderHistorySection`, rendered in `BinderDetailDrawer`; `BinderIntakesSection` also uses a generic visual `Timeline` for intake entries but is not an audit/history endpoint.
- API endpoint: `GET /api/v1/binders/{binderId}/history`.
- Query key: `bindersQK.history(binderId)` -> `['binders', 'history', binderId]`.
- Represents: binder lifecycle/status history.
- Future sharing: can share a visual status-transition timeline component later with annual report status history, but should not merge with legal/generic audit trails.
- Bad naming found: `history` is acceptable for binder lifecycle, but it should not be treated as generic audit.

## User Admin Audit Logs

- Feature/domain: `users`.
- Components: `AuditLogsDrawer`, opened from `UsersPage`.
- API endpoint: `GET /api/v1/users/audit-logs`.
- Query key: `usersQK.auditLogs(params)` -> `['users', 'audit-logs', params]`.
- Represents: user admin/auth audit, including login/logout/user management actions.
- Future sharing: do not merge with entity audit. It is security/admin audit with different filtering, actor, status, and risk semantics.
- Bad naming found: none. `AuditLogsDrawer` is accurate.

## Signature Request Legal Audit

- Feature/domain: `signatureRequests`.
- Components: `SignatureRequestAuditDrawer`, opened from `SignatureRequestsCard` and `SignatureRequestsDashboardPanel`.
- API endpoint used by drawer: `GET /api/v1/signature-requests/{id}` with embedded `audit_trail`.
- No standalone signature-request audit endpoint exists in current backend/OpenAPI.
- Query key used by drawer: `signatureRequestsQK.detail(id)` -> `['signature-requests', 'detail', id]`.
- Query key for standalone audit endpoint: none; no standalone backend endpoint exists.
- Represents: legal signature audit trail for signing lifecycle events.
- Future sharing: do not merge with generic audit. Signature audit is legal evidence and has signer/system actor semantics.
- Bad naming found: a standalone `getAuditTrail` frontend helper would be stale unless paired with a backend endpoint. The current backend contract exposes signature audit through detail.

## Recommendations

### What Should Remain Separate

- Client business timeline: operational/event timeline with actions and filters.
- Annual report filing timeline: derived lifecycle/deadline visualization.
- Annual report report history table: list of report years, not audit.
- User admin audit logs: security/admin audit.
- Signature request legal audit: legal evidence trail.

### What Can Share UI Later

- Generic entity audit tables for `client`, `business`, `charge`, and `annual_report` can share a table shell, pagination controls, action labels, field-label mapping, and JSON diff formatting.
- VAT audit and generic entity audit can share only low-level presentation pieces, such as paginated audit table layout, if the formatters stay domain-specific.
- Binder lifecycle history and annual report status history can potentially share a status-transition timeline component.

### What Should Not Be Merged

- Do not merge timeline with audit trail. Timeline is an operational product view; audit is an accountability record.
- Do not merge signature legal audit into generic audit UI.
- Do not merge user admin audit into entity audit.
- Do not treat annual report report history as audit history.

### Suggested Naming Convention

- Use `AuditTrail` for immutable event logs that record who changed what and when.
- Use `StatusHistory` for status transition records only.
- Use `Timeline` for operational or derived chronological product views.
- Use `ReportHistory` only when it means historical report records across years; prefer more explicit names such as `ClientReportYearsTable` if renaming later.
- Keep user-facing Hebrew labels flexible (`היסטוריה`, `ציר זמן`), but keep code names precise.
