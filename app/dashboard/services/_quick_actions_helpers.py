"""Per-category builders for dashboard quick actions."""

from __future__ import annotations

from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository

CATEGORY_ORDER = {"annual_reports": 1, "binders": 2}


def _batch_client_names(db, client_record_ids: list[int]) -> dict[int, str | None]:
    if not client_record_ids:
        return {}
    unique_ids = list(set(client_record_ids))
    client_record_repo = ClientRecordRepository(db)
    legal_entity_repo = LegalEntityRepository(db)
    records = client_record_repo.list_by_ids(unique_ids)
    legal_entity_ids = list({r.legal_entity_id for r in records if r.legal_entity_id})
    entities = legal_entity_repo.list_by_ids(legal_entity_ids)
    entity_name_map = {e.id: e.official_name for e in entities}
    return {r.id: entity_name_map.get(r.legal_entity_id) for r in records}
