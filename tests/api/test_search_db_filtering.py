from datetime import date

from app.clients.models.client import Client, ClientType
from app.binders.models.binder import Binder, BinderStatus, BinderType


def _make_client(db, full_name: str, id_number: str) -> Client:
    c = Client(
        full_name=full_name,
        id_number=id_number,
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _make_binder(db, client_id: int, binder_number: str, user_id: int) -> Binder:
    b = Binder(
        client_id=client_id,
        binder_number=binder_number,
        binder_type=BinderType.ANNUAL_REPORT,
        received_at=date.today(),
        received_by=user_id,
        status=BinderStatus.IN_OFFICE,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def test_search_clients_db_pagination(client, test_db, advisor_headers):
    """Page 2 should return correct offset results."""
    for i in range(5):
        _make_client(test_db, f"Paginate Client {i:02d}", f"PAG{i:07d}")

    r1 = client.get(
        "/api/v1/search?client_name=Paginate&page=1&page_size=3",
        headers=advisor_headers,
    )
    r2 = client.get(
        "/api/v1/search?client_name=Paginate&page=2&page_size=3",
        headers=advisor_headers,
    )

    assert r1.status_code == 200
    assert r2.status_code == 200
    d1 = r1.json()
    d2 = r2.json()

    assert d1["total"] == 5
    assert len(d1["results"]) == 3
    assert len(d2["results"]) == 2

    # Pages must not overlap
    ids_page1 = {r["client_id"] for r in d1["results"]}
    ids_page2 = {r["client_id"] for r in d2["results"]}
    assert ids_page1.isdisjoint(ids_page2)


def test_search_binder_number_filter(client, test_db, advisor_headers, test_user):
    """DB-level binder_number filter returns only matching binders."""
    c = _make_client(test_db, "Binder Filter Client", "BFC0000001")
    _make_binder(test_db, c.id, "ALPHA-001", test_user.id)
    _make_binder(test_db, c.id, "BETA-002", test_user.id)

    response = client.get(
        "/api/v1/search?binder_number=ALPHA",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    data = response.json()
    binder_results = [r for r in data["results"] if r["result_type"] == "binder"]
    assert len(binder_results) >= 1
    assert all("ALPHA" in r["binder_number"].upper() for r in binder_results)
