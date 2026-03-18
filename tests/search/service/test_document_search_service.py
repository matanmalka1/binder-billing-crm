from types import SimpleNamespace

from app.search.services.document_search_service import DocumentSearchService


def test_document_search_builds_results_and_caches_client_lookup(test_db):
    docs = [
        SimpleNamespace(
            id=1,
            client_id=10,
            document_type="id_copy",
            original_filename="id.pdf",
            tax_year=2026,
            status="active",
        ),
        SimpleNamespace(
            id=2,
            client_id=10,
            document_type="power_of_attorney",
            original_filename="poa.pdf",
            tax_year=2026,
            status="active",
        ),
        SimpleNamespace(
            id=3,
            client_id=11,
            document_type="engagement_agreement",
            original_filename="ea.pdf",
            tax_year=2025,
            status="archived",
        ),
    ]

    calls = {"count": 0}

    def _get_client(client_id):
        calls["count"] += 1
        if client_id == 10:
            return SimpleNamespace(full_name="Client Ten")
        return None

    svc = DocumentSearchService(test_db)
    svc.doc_repo = SimpleNamespace(search_by_query=lambda query, limit: docs)
    svc.client_repo = SimpleNamespace(get_by_id=_get_client)

    results = svc.search_documents("doc")
    assert len(results) == 3
    assert results[0]["client_name"] == "Client Ten"
    assert results[1]["client_name"] == "Client Ten"
    assert results[2]["client_name"] == "Unknown"
    assert calls["count"] == 2

