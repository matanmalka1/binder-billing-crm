from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict

from sqlalchemy.orm import Session

from app.reports.services.export_excel import export_aging_report_to_excel
from app.reports.services.export_pdf import export_aging_report_to_pdf


class ExportService:
    """
    Report export service for Excel and PDF.

    Generates downloadable files from report data.
    """

    def __init__(self, db: Session):
        self.db = db
        export_base = Path(tempfile.gettempdir()) / "exports"
        export_base.mkdir(parents=True, exist_ok=True)
        self.export_dir = str(export_base)

    def export_aging_report_to_excel(self, report_data: dict) -> Dict[str, object]:
        """Export aging report to Excel format."""
        return export_aging_report_to_excel(report_data, self.export_dir)

    def export_aging_report_to_pdf(self, report_data: dict) -> Dict[str, object]:
        """Export aging report to PDF format."""
        return export_aging_report_to_pdf(report_data, self.export_dir)
