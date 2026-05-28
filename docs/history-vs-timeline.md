## Scope
This file owns only:
- Reference explanation of the conceptual distinction between timeline and audit trail.

This file must not contain:
- Current implemented behavior unless verified against the owning domain README.
- New product requirements.
- Canonical architecture rules.

Source of truth: reference

# History vs Timeline

## Timeline

Timeline is the operational client activity feed. It is optimized for staff workflow, scanning, filtering, and acting on important client activity.

## AuditTrail

AuditTrail is the accountability/change log: who changed what and when. It is the full source of truth for audited entity changes.

Do not dump all audit records into the timeline. The timeline may later include only selected high-value audit-derived events, but the audit trail remains the complete record.

Generic entity audit UI can later be reused for:

- `client`
- `business`
- `charge`
- `annual_report`
