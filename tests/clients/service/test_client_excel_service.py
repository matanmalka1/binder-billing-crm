import builtins

from openpyxl import Workbook

from app.clients.services.client_excel_service import ClientExcelService


def test_client_excel_import_skips_blank_and_collects_errors(test_db):
    service = ClientExcelService(test_db)
    wb = Workbook()
    ws = wb.active
    ws.append(["full_name", "id_number", "client_type", "phone", "email", "notes"])
    ws.append([None, None, None, None, None, None])  # blank row skipped
    ws.append(["", "", "", "", "", ""])  # required-fields error
    ws.append(["Good Name", "ID1", "company", "", "", ""])

    class _ClientSvc:
        def create_client(self, **kwargs):
            if kwargs["id_number"] == "ID1":
                raise RuntimeError("duplicate")

    created, errors = service.import_clients_from_excel(wb, _ClientSvc(), actor_id=1)
    assert created == 0
    assert len(errors) == 1


def test_client_excel_create_workbook_importerror(monkeypatch, test_db):
    service = ClientExcelService(test_db)
    original_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name == "openpyxl":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)
    try:
        service._create_workbook_with_columns([("a", "A")])
        raise AssertionError("expected ImportError")
    except ImportError:
        pass
