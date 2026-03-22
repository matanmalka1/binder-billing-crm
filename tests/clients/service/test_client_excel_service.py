import builtins
from pathlib import Path

from openpyxl import Workbook, load_workbook

from app.clients.models.client import Client, IdNumberType
from app.clients.services.client_excel_service import ClientExcelService


def test_client_excel_import_skips_blank_and_collects_errors(test_db):
    service = ClientExcelService(test_db)
    wb = Workbook()
    ws = wb.active
    ws.append(["full_name", "id_number", "phone", "email"])
    ws.append([None, None, None, None])
    ws.append(["", "", "", ""])
    ws.append(["Good Name", "ID1", "", ""])

    class _ClientSvc:
        def create_client(self, **kwargs):
            if kwargs["id_number"] == "ID1":
                raise RuntimeError("duplicate")

    created, errors = service.import_clients_from_excel(wb, _ClientSvc(), actor_id=1)

    assert created == 0
    assert len(errors) == 1
    assert errors[0]["row"] == 4


def test_client_excel_import_collects_required_field_errors(test_db):
    service = ClientExcelService(test_db)
    wb = Workbook()
    ws = wb.active
    ws.append(["full_name", "id_number", "phone", "email"])
    ws.append(["Missing ID", "", "", ""])
    ws.append(["", "760000001", "", ""])

    class _ClientSvc:
        def create_client(self, **_kwargs):
            raise AssertionError("create_client should not be called for invalid rows")

    created, errors = service.import_clients_from_excel(wb, _ClientSvc(), actor_id=1)

    assert created == 0
    assert len(errors) == 2
    assert {err["row"] for err in errors} == {2, 3}


def test_client_excel_export_and_template_generate_files(test_db):
    service = ClientExcelService(test_db)

    crm_client = Client(
        full_name="Excel Name",
        id_number="750000001",
        id_number_type=IdNumberType.CORPORATION,
        phone="0501234567",
        email="excel@test.com",
    )
    test_db.add(crm_client)
    test_db.commit()
    test_db.refresh(crm_client)

    exported = service.export_clients([crm_client])
    template = service.generate_template()

    assert Path(exported["filepath"]).exists()
    assert exported["filename"].endswith(".xlsx")

    wb = load_workbook(exported["filepath"])
    ws = wb.active
    assert ws.cell(row=1, column=2).value == "Full Name"
    assert ws.cell(row=2, column=2).value == "Excel Name"

    assert Path(template["filepath"]).exists()
    template_wb = load_workbook(template["filepath"])
    template_ws = template_wb.active
    assert template_ws.cell(row=1, column=1).value == "Full Name"
    assert template_ws.cell(row=2, column=1).value == "יוסי כהן"


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
