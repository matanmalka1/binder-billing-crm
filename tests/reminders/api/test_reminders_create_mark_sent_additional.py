from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from app.binders.models.binder import Binder, BinderStatus
from app.businesses.models.business import Business, BusinessStatus
from app.common.enums import EntityType
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.clients.models.client import Client
from app.reminders.api import routes_create
from app.reminders.models.reminder import ReminderStatus, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository


def _client(db) -> Client:
    crm_client = Client(
        full_name="Reminder API Additional Client",
        id_number="RMA001",
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def _business(db, client_id: int, user_id: int) -> Business:
    business = Business(
        client_id=client_id,
        status=BusinessStatus.ACTIVE,
        opened_at=date.today(),
        created_by=user_id,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def test_create_binder_idle_and_unpaid_charge_missing_ids_return_400(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)

    idle = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "binder_idle",
            "target_date": date.today().isoformat(),
            "days_before": 3,
        },
    )
    assert idle.status_code == 422

    unpaid = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "unpaid_charge",
            "target_date": date.today().isoformat(),
            "days_before": 3,
        },
    )
    assert unpaid.status_code == 422


def test_mark_sent_endpoint_updates_pending_reminder(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)
    reminder = ReminderRepository(test_db).create(
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="send me",
    )

    resp = client.post(f"/api/v1/reminders/{reminder.id}/mark-sent", headers=advisor_headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"


def test_create_tax_deadline_missing_id_returns_422(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)
    resp = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "tax_deadline_approaching",
            "target_date": date.today().isoformat(),
            "days_before": 2,
        },
    )
    assert resp.status_code == 422
    assert any("tax_deadline_id" in err["msg"] for err in resp.json()["detail"])


def test_create_custom_branch_direct(monkeypatch):
    called: dict = {}

    class _Svc:
        def __init__(self, db):
            self.db = db

        def create_custom_reminder(self, **kwargs):
            called.update(kwargs)
            return SimpleNamespace(
                id=123,
                business_id=kwargs["business_id"],
                business_name=None,
                reminder_type=ReminderType.CUSTOM,
                status="pending",
                target_date=kwargs["target_date"],
                days_before=kwargs["days_before"],
                send_on=kwargs["target_date"],
                message=kwargs["message"],
                binder_id=None,
                charge_id=None,
                tax_deadline_id=None,
                annual_report_id=None,
                advance_payment_id=None,
                created_at=datetime.now(UTC),
                created_by=kwargs["created_by"],
                sent_at=None,
                canceled_at=None,
                canceled_by=None,
            )

    monkeypatch.setattr(routes_create, "ReminderService", _Svc)
    request = SimpleNamespace(
        business_id=1,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=1,
        message="x",
        binder_id=None,
        charge_id=None,
        tax_deadline_id=None,
        annual_report_id=None,
        advance_payment_id=None,
    )
    user = SimpleNamespace(id=1)

    result = routes_create.create_reminder(request=request, db=object(), user=user)
    assert result.business_id == 1
    assert called["created_by"] == user.id


@pytest.mark.parametrize(
    ("reminder_type", "expected_method", "linked_field"),
    [
        (ReminderType.VAT_FILING, "create_vat_filing_reminder", "tax_deadline_id"),
        (ReminderType.ANNUAL_REPORT_DEADLINE, "create_annual_report_deadline_reminder", "annual_report_id"),
        (ReminderType.ADVANCE_PAYMENT_DUE, "create_advance_payment_due_reminder", "advance_payment_id"),
        (ReminderType.DOCUMENT_MISSING, "create_document_missing_reminder", None),
    ],
)
def test_create_reminder_routes_to_extended_service_methods(monkeypatch, reminder_type, expected_method, linked_field):
    called: dict = {}

    def _build_reminder(kwargs):
        return SimpleNamespace(
            id=321,
            business_id=kwargs["business_id"],
            business_name=None,
            reminder_type=reminder_type,
            status=ReminderStatus.PENDING,
            target_date=kwargs["target_date"],
            days_before=kwargs["days_before"],
            send_on=kwargs["target_date"],
            message=kwargs.get("message") or "auto-msg",
            binder_id=kwargs.get("binder_id"),
            charge_id=kwargs.get("charge_id"),
            tax_deadline_id=kwargs.get("tax_deadline_id"),
            annual_report_id=kwargs.get("annual_report_id"),
            advance_payment_id=kwargs.get("advance_payment_id"),
            created_at=datetime.now(UTC),
            created_by=kwargs.get("created_by"),
            sent_at=None,
            canceled_at=None,
            canceled_by=None,
        )

    class _Svc:
        def __init__(self, db):
            self.db = db

        def _call(self, method_name, **kwargs):
            called["method"] = method_name
            called["kwargs"] = kwargs
            return _build_reminder(kwargs)

        def create_vat_filing_reminder(self, **kwargs):
            return self._call("create_vat_filing_reminder", **kwargs)

        def create_annual_report_deadline_reminder(self, **kwargs):
            return self._call("create_annual_report_deadline_reminder", **kwargs)

        def create_advance_payment_due_reminder(self, **kwargs):
            return self._call("create_advance_payment_due_reminder", **kwargs)

        def create_document_missing_reminder(self, **kwargs):
            return self._call("create_document_missing_reminder", **kwargs)

    monkeypatch.setattr(routes_create, "ReminderService", _Svc)
    request_kwargs = dict(
        business_id=1,
        reminder_type=reminder_type,
        target_date=date.today(),
        days_before=2,
        message="msg",
        binder_id=None,
        charge_id=None,
        tax_deadline_id=None,
        annual_report_id=None,
        advance_payment_id=None,
    )
    if linked_field:
        request_kwargs[linked_field] = 77
    request = SimpleNamespace(**request_kwargs)
    user = SimpleNamespace(id=9)

    result = routes_create.create_reminder(request=request, db=object(), user=user)
    assert result.business_id == 1
    assert called["method"] == expected_method
    assert called["kwargs"]["created_by"] == user.id


def test_create_binder_idle_and_unpaid_charge_and_custom_success(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)
    binder = Binder(
        client_id=crm_client.id,
        binder_number="RMA-B",
        period_start=date.today(),
        status=BinderStatus.IN_OFFICE,
        created_by=test_user.id,
    )
    charge = Charge(
        client_id=crm_client.id,
        business_id=business.id,
        amount=10,
        charge_type=ChargeType.OTHER,
        status=ChargeStatus.ISSUED,
    )
    test_db.add_all([binder, charge])
    test_db.commit()
    test_db.refresh(binder)
    test_db.refresh(charge)

    idle = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "binder_idle",
            "target_date": date.today().isoformat(),
            "days_before": 2,
            "binder_id": binder.id,
            "message": "idle",
        },
    )
    assert idle.status_code == 201

    unpaid = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "unpaid_charge",
            "target_date": date.today().isoformat(),
            "days_before": 3,
            "charge_id": charge.id,
            "message": "unpaid",
        },
    )
    assert unpaid.status_code == 201

    custom = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "custom",
            "target_date": date.today().isoformat(),
            "days_before": 0,
            "message": "custom-ok",
        },
    )
    assert custom.status_code == 201


def test_create_annual_report_and_advance_payment_missing_ids_return_422(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)

    annual = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "annual_report_deadline",
            "target_date": date.today().isoformat(),
            "days_before": 3,
        },
    )
    assert annual.status_code == 422
    assert any("annual_report_id" in err["msg"] for err in annual.json()["detail"])

    advance = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "advance_payment_due",
            "target_date": date.today().isoformat(),
            "days_before": 3,
        },
    )
    assert advance.status_code == 422
    assert any("advance_payment_id" in err["msg"] for err in advance.json()["detail"])
