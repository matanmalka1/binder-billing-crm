from app.annual_reports.schemas.annual_report_responses import SeasonSummaryResponse
from app.annual_reports.services.season_years import get_filing_season_year
from .base import AnnualReportBaseService


class AnnualReportSeasonService(AnnualReportBaseService):
    def get_season_summary_response(self, tax_year: int) -> SeasonSummaryResponse:
        summary = self.repo.get_season_summary(tax_year)
        overdue_count = len(self.repo.list_overdue(tax_year=tax_year))
        total = summary.get("total", 0)
        done = (
            summary.get("submitted", 0)
            + summary.get("accepted", 0)
            + summary.get("closed", 0)
        )
        completion_rate = round(done / total * 100, 1) if total > 0 else 0.0
        return SeasonSummaryResponse(
            tax_year=tax_year,
            filing_season_year=get_filing_season_year(tax_year),
            total=total,
            not_started=summary.get("not_started", 0),
            collecting_docs=summary.get("collecting_docs", 0),
            docs_complete=summary.get("docs_complete", 0),
            in_preparation=summary.get("in_preparation", 0),
            pending_client=summary.get("pending_client", 0),
            submitted=summary.get("submitted", 0),
            accepted=summary.get("accepted", 0),
            assessment_issued=summary.get("assessment_issued", 0),
            objection_filed=summary.get("objection_filed", 0),
            closed=summary.get("closed", 0),
            completion_rate=completion_rate,
            overdue_count=overdue_count,
        )


__all__ = ["AnnualReportSeasonService"]
