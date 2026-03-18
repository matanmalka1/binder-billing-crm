from pathlib import Path
import builtins
import tempfile

from openpyxl import Workbook

from app.utils.excel import adjust_column_widths, make_header_row, save_workbook_to_temp


def test_adjust_column_widths_and_make_header_row_apply_styles():
    wb = Workbook()
    ws = wb.active
    make_header_row(ws, ["A", "Long Header"], row=1)
    ws.append(["short", "very long value here"])

    adjust_column_widths(ws, min_width=5, max_width=40, padding=1)

    assert ws.cell(row=1, column=1).value == "A"
    assert ws.cell(row=1, column=1).font.bold is True
    assert ws.column_dimensions["B"].width >= ws.column_dimensions["A"].width


def test_save_workbook_to_temp_returns_metadata(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["x"])

    payload = save_workbook_to_temp(
        wb,
        prefix="unit_excel",
        export_dir=tmp_path,
        extra_meta={"format": "excel"},
    )

    assert payload["format"] == "excel"
    assert payload["filename"].startswith("unit_excel_")
    assert Path(payload["filepath"]).exists()


def test_adjust_and_header_helpers_tolerate_missing_openpyxl(monkeypatch):
    original_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name.startswith("openpyxl"):
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)

    class _WS:
        def iter_cols(self):
            return []

    ws = _WS()
    adjust_column_widths(ws)  # no raise
    make_header_row(ws, ["A"])  # no raise


def test_save_workbook_to_temp_uses_default_subdir():
    wb = Workbook()
    ws = wb.active
    ws.append(["x"])
    payload = save_workbook_to_temp(wb, prefix="default_subdir_case")
    assert payload["filepath"].startswith(str(Path(tempfile.gettempdir()) / "exports"))
