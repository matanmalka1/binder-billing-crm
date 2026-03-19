import tempfile
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from sqlalchemy.orm import Session

from app.clients.models.client import Client
from app.businesses.models.business import BusinessType
from app.utils.excel import adjust_column_widths, save_workbook_to_temp

if TYPE_CHECKING:
    from app.clients.services.client_service import ClientService

_VALID_CLIENT_TYPES = {ct.value for ct in BusinessType}


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
            client_type = str(row[2]).strip().lower() if len(row) > 2 and row[2] is not None else ""
            phone = str(row[3]).strip() if len(row) > 3 and row[3] is not None else None
            email = str(row[4]).strip() if len(row) > 4 and row[4] is not None else None
            notes = str(row[5]).strip() if len(row) > 5 and row[5] is not None else None

            if not (full_name and id_number and client_type):
                errors.append({"row": row_index, "error": "שם מלא, מספר מזהה וסוג לקוח הם שדות חובה"})
                continue

            if client_type not in _VALID_CLIENT_TYPES:
                errors.append({
                    "row": row_index,
                    "error": (
                        f"סוג לקוח לא חוקי: '{client_type}'. "
                        f"ערכים מותרים: {', '.join(sorted(_VALID_CLIENT_TYPES))}"
                    ),
                })
                continue

            try:
                client_service.create_client(
                    full_name=full_name,
                    id_number=id_number,
                    client_type=client_type,
                    opened_at=date.today(),
                    phone=phone,
                    email=email,
                    notes=notes,
                    actor_id=actor_id,
                )
                created += 1
            except Exception as exc:
                errors.append({"row": row_index, "error": str(exc)})

        return created, errors

    def _value_from_client(self, client: Client, attr: str):
        value = getattr(client, attr, "")
        if attr in {"client_type", "status"} and value:
            return value.value
        if attr in {"opened_at", "closed_at"} and value:
            return value.isoformat()
        return value or ""