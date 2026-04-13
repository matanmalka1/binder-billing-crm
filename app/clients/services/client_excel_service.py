import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from sqlalchemy.orm import Session

from app.clients.models.client import Client
from app.clients.constants import (
    CLIENT_EXCEL_FREEZE_PANES,
    CLIENT_EXCEL_SHEET_TITLE,
    CLIENT_EXPORT_COLUMNS,
    CLIENT_TEMPLATE_COLUMNS,
    CLIENT_TEMPLATE_SAMPLE_ROW,
)
from app.utils.excel import adjust_column_widths, save_workbook_to_temp

if TYPE_CHECKING:
    from app.clients.services.client_service import ClientService


class ClientExcelService:
    """Helper for creating client Excel exports and templates."""

    def __init__(self, _db: Session):
        self.export_dir = Path(tempfile.gettempdir()) / "exports" / "clients"
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_clients(self, clients: Iterable[Client]) -> dict:
        """Create an Excel file containing the provided clients."""
        wb, ws = self._create_workbook_with_columns(CLIENT_EXPORT_COLUMNS)
        for row_index, client in enumerate(clients, start=2):
            for col_index, (attr, _) in enumerate(CLIENT_EXPORT_COLUMNS, start=1):
                ws.cell(row=row_index, column=col_index, value=self._value_from_client(client, attr))

        adjust_column_widths(ws)
        return save_workbook_to_temp(wb, prefix="clients_export", export_dir=self.export_dir)

    def generate_template(self) -> dict:
        """Create a client import template that includes helper headers."""
        wb, ws = self._create_workbook_with_columns(CLIENT_TEMPLATE_COLUMNS)
        for col_index, value in enumerate(CLIENT_TEMPLATE_SAMPLE_ROW, start=1):
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
        ws.title = CLIENT_EXCEL_SHEET_TITLE
        header_font = Font(bold=True)

        for index, (_, header) in enumerate(columns, start=1):
            cell = ws.cell(row=1, column=index, value=header)
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        ws.freeze_panes = CLIENT_EXCEL_FREEZE_PANES
        return wb, ws

    def import_clients_from_excel(
        self,
        workbook,
        client_service: "ClientService",
        actor_id: int | None = None,
    ) -> tuple[int, list[dict]]:
        """Parse workbook and create clients. Returns (created_count, errors)."""
        worksheet = workbook.active
        created = 0
        errors: list[dict] = []

        for row_index, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
            if not any(cell is not None and str(cell).strip() for cell in row):
                continue

            full_name = str(row[0]).strip() if len(row) > 0 and row[0] is not None else ""
            id_number = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            phone = str(row[2]).strip() if len(row) > 2 and row[2] is not None else None
            email = str(row[3]).strip() if len(row) > 3 and row[3] is not None else None

            if not (full_name and id_number):
                errors.append({"row": row_index, "error": "שם מלא ומספר מזהה הם שדות חובה"})
                continue

            try:
                client_service.create_client(
                    full_name=full_name,
                    id_number=id_number,
                    phone=phone,
                    email=email,
                    actor_id=actor_id,
                )
                created += 1
            except Exception as exc:
                errors.append({"row": row_index, "error": str(exc)})

        return created, errors

    def _value_from_client(self, client: Client, attr: str):
        value = getattr(client, attr, "")
        return value or ""
