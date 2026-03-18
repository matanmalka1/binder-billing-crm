from app.reports.api import reports as reports_api


class _FakeExportService:
    def __init__(self, db):
        self.db = db

    def export_aging_report_to_excel(self, report):
        raise ImportError("xlsx backend missing")

    def export_aging_report_to_pdf(self, report):
        raise RuntimeError("pdf boom")


class _FakeAgingService:
    def __init__(self, db):
        self.db = db

    def generate_aging_report(self, as_of_date=None):
        return {"items": [], "summary": {}}


def test_export_aging_report_import_error_maps_to_500(client, advisor_headers, monkeypatch):
    monkeypatch.setattr(reports_api, "AgingReportService", _FakeAgingService)
    monkeypatch.setattr(reports_api, "ExportService", _FakeExportService)

    resp = client.get("/api/v1/reports/aging/export?format=excel", headers=advisor_headers)

    assert resp.status_code == 500
    assert "ספריית הייצוא אינה מותקנת" in resp.json()["detail"]


def test_export_aging_report_generic_error_maps_to_500(client, advisor_headers, monkeypatch):
    monkeypatch.setattr(reports_api, "AgingReportService", _FakeAgingService)
    monkeypatch.setattr(reports_api, "ExportService", _FakeExportService)

    resp = client.get("/api/v1/reports/aging/export?format=pdf", headers=advisor_headers)

    assert resp.status_code == 500
    assert "הייצוא נכשל" in resp.json()["detail"]
