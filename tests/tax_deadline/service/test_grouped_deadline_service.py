from datetime import date

from app.common.enums import VatType
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.services.grouped_deadline_service import GroupedDeadlineService
from app.vat_reports.models.vat_work_item import VatWorkItem
from tests.tax_deadline.factories import create_business


def test_grouped_vat_periods_preserve_period_months_count(test_db, test_user):
    business = create_business(test_db, name_prefix="Grouped VAT")
    monthly_item = VatWorkItem(
        client_record_id=business.client_id,
        created_by=test_user.id,
        period="2026-04",
        period_type=VatType.MONTHLY,
    )
    bimonthly_item = VatWorkItem(
        client_record_id=business.client_id,
        created_by=test_user.id,
        period="2026-03",
        period_type=VatType.BIMONTHLY,
    )
    test_db.add_all([monthly_item, bimonthly_item])
    test_db.flush()

    repo = TaxDeadlineRepository(test_db)
    due_date = date(2026, 5, 15)
    march_deadline = repo.create(
        client_record_id=business.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=due_date,
        period="2026-03",
    )
    april_deadline = repo.create(
        client_record_id=business.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=due_date,
        period="2026-04",
    )
    march_deadline.vat_work_item_id = bimonthly_item.id
    april_deadline.vat_work_item_id = monthly_item.id
    test_db.flush()

    response = GroupedDeadlineService(test_db).list_groups(
        deadline_type=DeadlineType.VAT,
        due_from=due_date,
        due_to=due_date,
    )

    assert response.total_groups == 1
    assert [
        (period.period, period.period_months_count)
        for period in sorted(response.groups[0].periods, key=lambda p: p.period)
    ] == [("2026-03", 2), ("2026-04", 1)]
