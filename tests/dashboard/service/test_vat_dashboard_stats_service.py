from datetime import date
from types import SimpleNamespace

from app.common.enums import VatType
from app.dashboard.services.vat_dashboard_stats_service import VatDashboardStatsService


def _service(test_db, required: int, submitted: int) -> VatDashboardStatsService:
    service = VatDashboardStatsService(test_db)
    service.client_repo = SimpleNamespace(count_active_by_vat_type=lambda _vat_type: required)
    service.vat_repo = SimpleNamespace(
        count_filed_by_period_type=lambda _period, _vat_type: submitted
    )
    return service


def test_vat_status_label_marks_overdue_period(test_db):
    stat = _service(test_db, required=2, submitted=1)._build_stat(
        VatType.MONTHLY,
        "2026-03",
        "מרץ 2026",
        date(2026, 4, 30),
    )

    assert stat["status_label"] == "מועד הגשה עבר"
    assert stat["pending"] == 1


def test_vat_status_label_marks_completed_period(test_db):
    stat = _service(test_db, required=2, submitted=2)._build_stat(
        VatType.MONTHLY,
        "2026-03",
        "מרץ 2026",
        date(2026, 4, 30),
    )

    assert stat["status_label"] == "הושלמה"
