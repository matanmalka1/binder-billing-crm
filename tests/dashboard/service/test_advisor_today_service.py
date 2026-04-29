from datetime import date
from types import SimpleNamespace

from app.dashboard.services.advisor_today_service import AdvisorTodayService, _reminder_item
from app.reminders.models.reminder import ReminderType
from app.tax_deadline.models.tax_deadline import DeadlineType


def test_deadline_item_formats_aggregate_row(test_db):
    service = AdvisorTodayService(test_db)
    row = SimpleNamespace(
        first_id=7,
        deadline_type=DeadlineType.NATIONAL_INSURANCE,
        due_date=date(2026, 5, 15),
        period="2026-05",
        max_period="2026-05",
        tax_year=None,
        client_count=42,
    )

    item = service._deadline_item(row, date(2026, 4, 29))

    assert item == {
        "id": 7,
        "label": "ביטוח לאומי",
        "sublabel": "תשלום מקדמות עד 15/05/2026 · עוד 16 ימים",
        "description": "42 לקוחות רלוונטיים · תקופת מועד 05/2026",
        "href": "/tax/deadlines",
    }


def test_deadline_item_formats_annual_report_tax_year(test_db):
    service = AdvisorTodayService(test_db)
    row = SimpleNamespace(
        first_id=8,
        deadline_type=DeadlineType.ANNUAL_REPORT,
        due_date=date(2026, 5, 31),
        period=None,
        max_period=None,
        tax_year=2025,
        client_count=12,
    )

    item = service._deadline_item(row, date(2026, 5, 1))

    assert item["description"] == "12 לקוחות רלוונטיים · שנת מס 2025"


def test_reminder_item_uses_client_name_as_label_and_business_in_sublabel():
    reminder = SimpleNamespace(
        id=9,
        client_record_id=22,
        business_id=33,
        message="תזכורת: חשבונית #1722 לא שולמה 78 ימים",
    )

    item = _reminder_item(
        reminder,
        {
            "client_name": "מאיה כץ",
            "business_name": "מסלול ירוק - צילום ומדיה",
        },
    )

    assert item == {
        "id": 9,
        "label": "מאיה כץ",
        "sublabel": "מסלול ירוק - צילום ומדיה · חשבונית #1722 לא שולמה 78 ימים",
        "href": "/reminders",
    }


def test_reminder_items_excludes_unpaid_charge_duplicates(monkeypatch, test_db):
    service = AdvisorTodayService(test_db)
    reminders = [
        SimpleNamespace(
            id=1,
            client_record_id=10,
            business_id=20,
            reminder_type=ReminderType.UNPAID_CHARGE,
            message="תזכורת: חשבונית לא שולמה",
        ),
        SimpleNamespace(
            id=2,
            client_record_id=11,
            business_id=21,
            reminder_type=ReminderType.BINDER_IDLE,
            message="תזכורת: תיק לא טופל",
        ),
    ]
    monkeypatch.setattr(
        service.reminder_repo,
        "list_by_status",
        lambda *args, **kwargs: reminders,
    )
    monkeypatch.setattr(
        "app.dashboard.services.advisor_today_service.build_context_map",
        lambda db, business_repo, items, tax_deadline_repo: {
            item.id: {"client_name": "לקוח פעיל", "business_name": "עסק פעיל"}
            for item in items
        },
    )

    items = service._reminder_items(date(2026, 4, 29))

    assert [item["id"] for item in items] == [2]
