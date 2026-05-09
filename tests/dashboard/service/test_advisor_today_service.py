from datetime import date

from app.dashboard.services.advisor_today_service import AdvisorTodayService


def test_advisor_today_no_longer_returns_reminder_items(test_db):
    payload = AdvisorTodayService(test_db).build(date(2026, 4, 29))

    assert payload == {"deadline_items": []}
