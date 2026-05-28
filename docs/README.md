## Scope
This file owns only:
- Backend-local documentation ownership status.
- Pointers from old backend docs to the root project-wide docs layer.

This file must not contain:
- Project-wide agent behavior, frontend rules, cross-project decision policy, or domain documentation rewrites.

Source of truth: reference

# Backend Docs

Project-wide agent, architecture, workflow, and decision rules are canonical in the sibling docs repo:

- `../../docs/AGENTS.md`
- `../../docs/docs/agent/entry-point.md`
- `../../docs/docs/project/documentation-map.md`
- `../../docs/docs/architecture/`
- `../../docs/docs/workflow/`
- `../../docs/docs/adr/`

Backend-local docs in this directory are reference material unless a root `docs/` file explicitly delegates authority to them.

Do not add project-wide agent behavior, frontend rules, or cross-project decision policy under `backend/docs/`.
