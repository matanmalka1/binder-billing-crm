from app.users.models.user import UserRole
from app.dashboard.services.dashboard_overview_service import DashboardOverviewService


def test_secretary_overview_returns_operational_subset(test_db):
    overview = DashboardOverviewService(test_db).get_overview(
        user_role=UserRole.SECRETARY
    )

    assert overview["is_empty"] is True
    assert overview["quick_actions"] == []
    assert overview["attention"]["items"] == []
    assert overview["open_charges_count"] == 0
    assert overview["open_charges_amount_ils"] is None
