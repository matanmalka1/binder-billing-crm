from datetime import datetime
from unittest.mock import MagicMock

from app.vat_reports.models.vat_enums import InvoiceType, VatWorkItemStatus


def make_item(
    id: int = 1,
    client_id: int = 10,
    period: str = "2026-01",
    status: VatWorkItemStatus = VatWorkItemStatus.MATERIAL_RECEIVED,
    net_vat: float = 0,
):
    item = MagicMock()
    item.id = id
    item.client_id = client_id
    item.period = period
    item.status = status
    item.net_vat = net_vat
    return item


def make_invoice(
    id: int = 1,
    work_item_id: int = 1,
    invoice_type: InvoiceType = InvoiceType.INCOME,
    vat_amount: float = 170.0,
    invoice_date: datetime | None = None,
):
    inv = MagicMock()
    inv.id = id
    inv.work_item_id = work_item_id
    inv.invoice_type = invoice_type
    inv.invoice_number = "INV-001"
    inv.vat_amount = vat_amount
    inv.invoice_date = invoice_date or datetime(2026, 1, 15)
    return inv
