from datetime import date, datetime
from types import SimpleNamespace

from app.dashboard.services.dashboard_extended_service import DashboardExtendedService
from app.users.models.user import UserRole


def test_get_attention_data_returns_empty_for_non_advisor(test_db):
    service = DashboardExtendedService(test_db)

    data = service.get_attention_data(
        user_role=None, reference_date=date(2026, 3, 10)
    )
    assert data["items"] == []


def test_get_attention_data_advisor_skips_unmapped_charge_clients(
    test_db,
):
    service = DashboardExtendedService(test_db)
    service.charge_repo = SimpleNamespace(
        list_charges=lambda **kwargs: [
            SimpleNamespace(business_id=999, client_record_id=999, id=1, amount=10)
        ]
    )
    service.business_repo = SimpleNamespace(list_by_ids=lambda ids: [])

    data = service.get_attention_data(
        user_role=UserRole.ADVISOR, reference_date=date(2026, 3, 10)
    )
    assert data["items"] == []


def test_get_attention_data_advisor_appends_unpaid_charge_item(test_db):
    service = DashboardExtendedService(test_db)
    mapped_charge_business = SimpleNamespace(id=77, business_name="Charge Business")
    charge = SimpleNamespace(
        id=4,
        client_record_id=88,
        business_id=77,
        amount=300,
        charge_type="monthly_retainer",
        description=None,
        issued_at=datetime(2026, 3, 12, 10, 30),
        invoice=None,
        period="2026-02",
    )
    client_record = SimpleNamespace(id=88, legal_entity_id=99)
    legal_entity = SimpleNamespace(id=99, official_name="Legal Client")

    service.charge_repo = SimpleNamespace(list_charges=lambda **kwargs: [charge])
    service.business_repo = SimpleNamespace(
        list_by_ids=lambda ids: [mapped_charge_business]
    )
    service.client_record_repo = SimpleNamespace(
        list_by_ids=lambda ids: [client_record]
    )
    service.legal_entity_repo = SimpleNamespace(
        list_by_ids=lambda ids: [legal_entity]
    )

    data = service.get_attention_data(
        user_role=UserRole.ADVISOR, reference_date=date(2026, 3, 10)
    )
    items = data["items"]

    assert len(items) == 1
    assert items[0]["item_type"] == "unpaid_charge"
    assert items[0]["charge_id"] == 4
    assert items[0]["client_name"] == "Legal Client"
    assert items[0]["description"] == "Charge Business · ₪300 · לתשלום היום"
    assert items[0]["charge_subject"] == "חשבונית #4 · ריטיינר חודשי · תקופה 02/2026"
    assert items[0]["charge_date"] == date(2026, 3, 12)
    assert items[0]["charge_amount"] == "₪300"
    assert items[0]["charge_invoice_number"] == "4"
    assert items[0]["charge_period"] == "2026-02"


def test_get_attention_data_advisor_includes_client_level_charge(test_db):
    service = DashboardExtendedService(test_db)
    charge = SimpleNamespace(
        id=5,
        client_record_id=89,
        business_id=None,
        amount=450,
        charge_type="consultation_fee",
        description=None,
        issued_at=datetime(2026, 3, 1, 10, 30),
        invoice=None,
        period=None,
    )
    client_record = SimpleNamespace(id=89, legal_entity_id=100)
    legal_entity = SimpleNamespace(id=100, official_name="Client Level")

    service.charge_repo = SimpleNamespace(list_charges=lambda **kwargs: [charge])
    service.business_repo = SimpleNamespace(list_by_ids=lambda ids: [])
    service.client_record_repo = SimpleNamespace(
        list_by_ids=lambda ids: [client_record]
    )
    service.legal_entity_repo = SimpleNamespace(
        list_by_ids=lambda ids: [legal_entity]
    )

    data = service.get_attention_data(
        user_role=UserRole.ADVISOR, reference_date=date(2026, 3, 10)
    )
    items = data["items"]

    assert len(items) == 1
    assert items[0]["item_type"] == "unpaid_charge"
    assert items[0]["charge_id"] == 5
    assert items[0]["business_id"] is None
    assert items[0]["client_id"] == 89
    assert items[0]["client_name"] == "Client Level"
    assert items[0]["business_name"] == "Client Level"
    assert items[0]["description"] == "₪450 · באיחור 9 ימים"
