import tempfile
from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session

from app.clients.models.client import Client
from app.utils.excel import adjust_column_widths, save_workbook_to_temp


class ClientExcelService:
    """Helper for creating client Excel exports and templates."""

    EXPORT_COLUMNS = [
        ("id", "ID"),
        ("full_name", "Full Name"),
        ("id_number", "ID Number"),
        ("client_type", "Client Type"),
        ("status", "Status"),
        ("primary_binder_number", "Primary Binder #"),
        ("phone", "Phone"),
        ("email", "Email"),
        ("opened_at", "Opened At"),
        ("closed_at", "Closed At"),
        ("notes", "Notes"),
    ]

    TEMPLATE_COLUMNS = [
        ("full_name", "Full Name"),
        ("id_number", "ID Number"),
        ("client_type", "Client Type"),
        ("phone", "Phone (optional)"),
        ("email", "Email (optional)"),
    ]

    def __init__(self, db: Session):
        self.db = db
        self.export_dir = Path(tempfile.gettempdir()) / "exports" / "clients"
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_clients(self, clients: Iterable[Client]) -> dict:
        """Create an Excel file containing the provided clients."""
        wb, ws = self._create_workbook_with_columns(self.EXPORT_COLUMNS)
        for row_index, client in enumerate(clients, start=2):
            for col_index, (attr, _) in enumerate(self.EXPORT_COLUMNS, start=1):
                ws.cell(row=row_index, column=col_index, value=self._value_from_client(client, attr))

        adjust_column_widths(ws)
        return save_workbook_to_temp(wb, prefix="clients_export", export_dir=self.export_dir)

    def generate_template(self) -> dict:
        """Create a client import template that includes helper headers."""
        wb, ws = self._create_workbook_with_columns(self.TEMPLATE_COLUMNS)
        sample_row = ["יוסי כהן", "123456789", "osek_patur", "0501234567", "yossi@example.com"]
        for col_index, value in enumerate(sample_row, start=1):
            ws.cell(row=2, column=col_index, value=value)

        adjust_column_widths(ws)
        return save_workbook_to_temp(wb, prefix="clients_template", export_dir=self.export_dir)

    def _create_workbook_with_columns(self, columns: list[tuple[str, str]]):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font
        except ImportError as exc:
            raise ImportError("הספרייה openpyxl נדרשת לצורך ייצוא לקוחות לאקסל") from exc

        wb = Workbook()
        ws = wb.active
        ws.title = "Clients"
        header_font = Font(bold=True)

        for index, (_, header) in enumerate(columns, start=1):
            cell = ws.cell(row=1, column=index, value=header)
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        ws.freeze_panes = "A2"
        return wb, ws

    def _value_from_client(self, client: Client, attr: str):
        value = getattr(client, attr, "")
        if attr in {"client_type", "status"} and value:
            return value.value
        if attr in {"opened_at", "closed_at"} and value:
            return value.isoformat()
        return value or ""
