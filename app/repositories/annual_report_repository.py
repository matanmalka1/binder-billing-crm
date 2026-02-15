from typing import Optional

from sqlalchemy.orm import Session

from app.models import AnnualReport, ReportStage


class AnnualReportRepository:
    """Data access layer for AnnualReport entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: int,
        tax_year: int,
        form_type: Optional[str] = None,
        due_date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AnnualReport:
        """Create new annual report."""
        report = AnnualReport(
            client_id=client_id,
            tax_year=tax_year,
            form_type=form_type,
            due_date=due_date,
            notes=notes,
            stage=ReportStage.MATERIAL_COLLECTION,
            status="not_started",
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_by_id(self, report_id: int) -> Optional[AnnualReport]:
        """Retrieve report by ID."""
        return self.db.query(AnnualReport).filter(AnnualReport.id == report_id).first()

    def get_by_client_year(self, client_id: int, tax_year: int) -> Optional[AnnualReport]:
        """Get report by client and tax year."""
        return (
            self.db.query(AnnualReport)
            .filter(
                AnnualReport.client_id == client_id,
                AnnualReport.tax_year == tax_year,
            )
            .first()
        )

    def list_by_stage(
        self,
        stage: ReportStage,
        page: int = 1,
        page_size: int = 20,
    ) -> list[AnnualReport]:
        """List reports by stage with pagination."""
        query = self.db.query(AnnualReport).filter(AnnualReport.stage == stage)
        offset = (page - 1) * page_size
        return query.order_by(AnnualReport.due_date).offset(offset).limit(page_size).all()

    def list_by_client(
        self,
        client_id: int,
        tax_year: Optional[int] = None,
    ) -> list[AnnualReport]:
        """List reports for a client."""
        query = self.db.query(AnnualReport).filter(AnnualReport.client_id == client_id)
        if tax_year:
            query = query.filter(AnnualReport.tax_year == tax_year)
        return query.order_by(AnnualReport.tax_year.desc()).all()

    def count_by_stage(self, stage: ReportStage) -> int:
        """Count reports by stage."""
        return self.db.query(AnnualReport).filter(AnnualReport.stage == stage).count()

    def update(self, report_id: int, **fields) -> Optional[AnnualReport]:
        """Update report fields."""
        report = self.get_by_id(report_id)
        if not report:
            return None

        for key, value in fields.items():
            if hasattr(report, key):
                setattr(report, key, value)

        self.db.commit()
        self.db.refresh(report)
        return report