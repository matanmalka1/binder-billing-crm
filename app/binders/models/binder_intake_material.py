from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.enum_utils import pg_enum
from app.utils.time_utils import utcnow


class MaterialType(str, PyEnum):
    """Type of material received in the binder."""

    VAT = "vat"  # VAT filings (periodic)
    INCOME_TAX = "income_tax"  # Income tax advances and withholdings
    ANNUAL_REPORT = "annual_report"  # Annual report (1301/1214) and appendices
    SALARY = "salary"  # Payslips, form 102 reports, forms 161/106
    BOOKKEEPING = "bookkeeping"  # Invoices, receipts, bank and supplier statements
    NATIONAL_INSURANCE = "national_insurance"  # Claims, approvals, advance payment booklets
    CAPITAL_DECLARATION = "capital_declaration"  # Capital declaration
    PENSION_AND_INSURANCE = "pension_and_insurance"  # Consolidated pension/insurance reports
    CORPORATE_DOCS = "corporate_docs"  # Corporate documents (minutes, registration certificate)
    TAX_ASSESSMENT = "tax_assessment"  # Tax assessments and tax rulings
    OTHER = "other"  # Anything outside the defined categories


class BinderIntakeMaterial(Base):
    """
    A single item within a material intake event.
    Each item represents a specific material type for a specific business.
    For example: VAT invoices for the gardening business from January 2026.

    No file is attached, only a record of what was received.
    If an important file must be kept, use PermanentDocument.
    """

    __tablename__ = "binder_intake_materials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    intake_id: Mapped[int] = mapped_column(
        ForeignKey("binder_intakes.id"), nullable=False, index=True
    )

    # Which business the material belongs to (nullable for client-level generic material).
    business_id: Mapped[int | None] = mapped_column(
        ForeignKey("businesses.id"), nullable=True, index=True
    )

    # Material type.
    material_type: Mapped[MaterialType] = mapped_column(pg_enum(MaterialType), nullable=False)

    # Link to a specific annual report (nullable; only for annual_report material type).
    annual_report_id: Mapped[int | None] = mapped_column(
        ForeignKey("annual_reports.id"), nullable=True, index=True
    )

    # Link to a VAT reporting-period entity (nullable; only for vat material type).
    vat_report_id: Mapped[int | None] = mapped_column(
        ForeignKey("vat_work_items.id"), nullable=True, index=True
    )

    period_year: Mapped[int] = mapped_column(nullable=False)
    period_month_start: Mapped[int] = mapped_column(nullable=False)  # 1–12
    period_month_end: Mapped[int] = mapped_column(
        nullable=False
    )  # 1–12; equals period_month_start for monthly

    # Optional free-text note (not the period — use structured fields above for period).
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_intake_material_business", "business_id"),
        Index("idx_intake_material_type", "material_type"),
    )

    def __repr__(self):
        return (
            f"<BinderIntakeMaterial(id={self.id}, intake_id={self.intake_id}, "
            f"type='{self.material_type}', business_id={self.business_id})>"
        )
