from datetime import date
from types import SimpleNamespace

from app.dashboard.services.advisor_today_service import AdvisorTodayService, _reminder_item
from app.reminders.models.reminder import ReminderType


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


def test_reminder_items_returns_pending_reminders(monkeypatch, test_db):
    service = AdvisorTodayService(test_db)
    reminders = [
        SimpleNamespace(
            id=1,
            client_record_id=10,
            business_id=20,
            reminder_type=ReminderType.BINDER_IDLE,
            message="תזכורת: תיק לא טופל",
        ),
        SimpleNamespace(
            id=2,
            client_record_id=11,
            business_id=21,
            reminder_type=ReminderType.CUSTOM,
            message="תזכורת: בדיקה",
        ),
    ]
    monkeypatch.setattr(
        service.reminder_repo,
        "list_by_status",
        lambda *args, **kwargs: reminders,
    )
    monkeypatch.setattr(
        "app.dashboard.services.advisor_today_service.build_context_map",
        lambda db, business_repo, items: {
            item.id: {"client_name": "לקוח פעיל", "business_name": "עסק פעיל"}
            for item in items
        },
    )

    items = service._reminder_items(date(2026, 4, 29))

    assert {item["id"] for item in items} == {1, 2}
