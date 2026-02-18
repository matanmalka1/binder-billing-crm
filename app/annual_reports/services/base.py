from app.annual_reports.models import AnnualReport


class AnnualReportBaseService:
    """Shared helpers for annual report service mixins."""

    repo: any  # set by concrete service

    def _get_or_raise(self, report_id: int) -> AnnualReport:
        report = self.repo.get_by_id(report_id)
        if not report:
            raise ValueError(f"Annual report {report_id} not found")
        return report
