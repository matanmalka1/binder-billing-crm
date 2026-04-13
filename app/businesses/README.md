# Businesses Module

> Last aligned: 2026-04-11

`businesses` is now an operational domain, not the primary tax-entity domain.

- `Client` is the legal/tax identity.
- `Business` is a business activity under a client.
- Tax-entity fields such as VAT reporting frequency, advance rate, and fiscal-year configuration now live on `clients`.

## Current Scope

This module is responsible for:

- Creating and listing businesses under a client
- Updating business identity/status
- Soft delete and restore
- Sole-trader consistency rules (`osek_patur` vs `osek_murshe`)
- Business lifecycle guards used by downstream domains
- Client status-card aggregation that still needs business-scoped data

This module is not responsible for:

- Client tax-profile CRUD
- Standalone `/api/v1/businesses/*` CRUD routes
- `BusinessTaxProfile` management

## Active API

Mounted under `/api/v1`.

### Client-scoped business routes

- `POST /clients/{client_id}/businesses`
- `GET /clients/{client_id}/businesses`
- `GET /clients/{client_id}/businesses/{business_id}`
- `PATCH /clients/{client_id}/businesses/{business_id}`
- `DELETE /clients/{client_id}/businesses/{business_id}`
- `POST /clients/{client_id}/businesses/{business_id}/restore`

### Client status card

The status-card endpoint is client-scoped and mounted from the `clients` API:

- `GET /clients/{client_id}/status-card`

Implementation currently lives in `app/businesses/services/status_card_service.py`
for historical reasons, but the response itself is client-scoped and does not require
or expose a synthetic `business_id`.

## Core Rules

### Sole-trader exclusivity

A single client cannot mix:

- `osek_patur`
- `osek_murshe`

Multiple businesses of the same sole-trader type are allowed.

### Lifecycle blocking

Downstream create flows should use `business_guards`:

- `active` => allowed
- `frozen` => blocked
- `closed` => blocked

### Soft delete semantics

Repository default reads exclude soft-deleted rows.
Restore sets status back to `active`.

## Main Files

- Model: `app/businesses/models/business.py`
- Repository: `app/businesses/repositories/business_repository.py`
- API: `app/businesses/api/client_businesses_router.py`
- Service: `app/businesses/services/business_service.py`
- Guards: `app/businesses/services/business_guards.py`
- Lifecycle: `app/businesses/services/business_lifecycle_service.py`
- Status card: `app/businesses/services/status_card_service.py`

## Domain Direction

This domain is mid-refactor.

- Keep new business APIs client-scoped.
- Prefer `client_id` for new tax-entity flows.
- Avoid reintroducing standalone `/businesses/{id}` CRUD endpoints.
