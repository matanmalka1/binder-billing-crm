"""VatWorkItemRepository — backward-compatible re-export.

This module is retained so existing imports continue to work.
The implementation is split into:
  - vat_work_item_query_repository.VatWorkItemQueryRepository  (read)
  - vat_work_item_write_repository.VatWorkItemWriteRepository  (write + audit)

New code should import from those modules directly.
VatWorkItemRepository is now an alias for VatWorkItemWriteRepository, which
exposes all read helpers via delegation to the query repository.
"""

from app.vat_reports.repositories.vat_work_item_query_repository import VatWorkItemQueryRepository
from app.vat_reports.repositories.vat_work_item_write_repository import VatWorkItemWriteRepository

# Alias so all existing `from ...vat_work_item_repository import VatWorkItemRepository` imports work.
VatWorkItemRepository = VatWorkItemWriteRepository

__all__ = [
    "VatWorkItemRepository",
    "VatWorkItemQueryRepository",
    "VatWorkItemWriteRepository",
]
