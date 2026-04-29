from datetime import date, datetime
from types import SimpleNamespace

from app.dashboard.services.dashboard_extended_builders import (
    ready_attention_item,
    unpaid_charge_attention_item,
)


def test_dashboard_extended_builders_return_expected_payload_shapes():
    binder = SimpleNamespace(
        id=10,
        client_record_id=20,
        binder_number="DB-100",
        period_start=date(2026, 3, 1),
    )
    business = SimpleNamespace(id=20, full_name="Dashboard Client", business_name="Dashboard Client")
    charge = SimpleNamespace(
        client_record_id=20,
        amount=123.45,
        charge_type="consultation_fee",
        description="פגישת ייעוץ | Dashboard Client | תקופה 2026-03",
        issued_at=datetime(2026, 3, 11, 9, 0),
        id=88,
        invoice=SimpleNamespace(id=1048),
        period="2026-03",
    )
    ready = ready_attention_item(binder, business)
    assert ready["item_type"] == "ready_for_pickup"
    assert "מוכן לאיסוף" in ready["description"]

    unpaid = unpaid_charge_attention_item(charge, business, reference_date=date(2026, 3, 16))
    assert unpaid["item_type"] == "unpaid_charge"
    assert unpaid["description"] == "Dashboard Client · ₪123.45 · באיחור 5 ימים"
    assert unpaid["charge_subject"] == "חשבונית #1048 · פגישת ייעוץ · תקופה 03/2026"
    assert unpaid["charge_date"] == date(2026, 3, 11)
    assert unpaid["charge_amount"] == "₪123.45"
    assert unpaid["charge_invoice_number"] == "1048"
    assert unpaid["charge_period"] == "2026-03"


def test_unpaid_charge_subject_removes_business_and_period_fragments():
    business = SimpleNamespace(id=20, business_name="מעבדת גל - פיתוח תוכנה")
    charge = SimpleNamespace(
        client_record_id=20,
        amount=1378.49,
        charge_type="vat_filing_fee",
        description="טיפול בדיווח מע\"מ תקופתי | מעבדת גל - פיתוח תוכנה | תקופה 2025-01",
        issued_at=datetime(2026, 4, 24, 9, 0),
        id=1048,
        invoice=None,
        period="2025-01",
    )

    unpaid = unpaid_charge_attention_item(charge, business, "מאיה כץ", date(2026, 4, 29))

    assert unpaid["client_name"] == "מאיה כץ"
    assert unpaid["business_name"] == "מעבדת גל - פיתוח תוכנה"
    assert unpaid["description"] == "מעבדת גל - פיתוח תוכנה · ₪1,378.49 · באיחור 5 ימים"
    assert unpaid["charge_subject"] == "חשבונית #1048 · טיפול בדיווח מע\"מ תקופתי · תקופה 01/2025"
    assert unpaid["charge_period"] == "2025-01"
