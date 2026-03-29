"""Period options logic for VAT work item creation UI."""

from datetime import date
from typing import Optional

from app.core.exceptions import AppError, NotFoundError
from app.businesses.models.business_tax_profile import VatType
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.repositories.business_tax_profile_repository import BusinessTaxProfileRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository


def _period_label(period_type: VatType, year: int, month: int) -> str:
    if period_type == VatType.BIMONTHLY:
        return f"{year}-{month:02d}/{year}-{month + 1:02d}"
    return f"{year}-{month:02d}"


def get_period_options(
    work_item_repo: VatWorkItemRepository,
    business_repo: BusinessRepository,
    *,
    business_id: int,
    tax_profile_repo: Optional[BusinessTaxProfileRepository] = None,
    year: Optional[int] = None,
):
    """Return period options for UI selection based on business VAT frequency."""
    business = business_repo.get_by_id(business_id)
    if not business:
        raise NotFoundError(f"עסק {business_id} לא נמצא", "VAT.NOT_FOUND")

    selected_year = year or date.today().year

    profile = tax_profile_repo.get_by_business_id(business_id) if tax_profile_repo else None
    period_type = profile.vat_type if (profile and profile.vat_type) else VatType.MONTHLY
    if period_type == VatType.EXEMPT:
        raise AppError(
            "עסק זה פטור ממע\"מ ולא ניתן לפתוח עבורו דוח",
            "VAT.CLIENT_EXEMPT",
        )

    start_months = range(1, 12, 2) if period_type == VatType.BIMONTHLY else range(1, 13)
    year_prefix = f"{selected_year}-"
    opened_periods = {
        i.period for i in work_item_repo.list_by_business(business_id) if i.period.startswith(year_prefix)
    }
    options = []
    for month in start_months:
        period = f"{selected_year}-{month:02d}"
        options.append(
            {
                "period": period,
                "label": _period_label(period_type, selected_year, month),
                "start_month": month,
                "end_month": month + 1 if period_type == VatType.BIMONTHLY else month,
                "is_opened": period in opened_periods,
            }
        )

    return {
        "business_id": business_id,
        "year": selected_year,
        "period_type": period_type,
        "options": options,
    }
