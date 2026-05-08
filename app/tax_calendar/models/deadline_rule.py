"""DeadlineRule — versioned regulatory rule for TaxCalendar due dates.

Lookup engine only — versioned via effective_from/effective_to so that historic
calculations remain stable when the law changes. Maps to an ObligationType:

    vat_monthly       → VAT
    vat_bimonthly     → VAT
    advance_monthly   → ADVANCE_PAYMENT
    advance_bimonthly → ADVANCE_PAYMENT
    annual_report     → ANNUAL_REPORT

# INV-11: DeadlineRule overlap is enforced in the service layer, not by DB constraint.
"""

from sqlalchemy import CheckConstraint, Column, Date, DateTime, Index, Integer, String

from app.common.enums import DeadlineRuleType
from app.database import Base
from app.utils.enum_utils import pg_enum
from app.utils.time_utils import utcnow


class DeadlineRule(Base):
    """Regulatory rule for computing a TaxCalendar due date."""

    __tablename__ = "deadline_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)

    rule_type = Column(pg_enum(DeadlineRuleType), nullable=False, index=True)

    due_day_of_month = Column(Integer, nullable=False)
    offset_months    = Column(Integer, nullable=False, default=0, server_default="0")

    effective_from = Column(Date, nullable=False)
    effective_to   = Column(Date, nullable=True)

    description = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_deadline_rule_effective_range",
        ),
        CheckConstraint(
            "due_day_of_month BETWEEN 1 AND 31",
            name="ck_deadline_rule_due_day_range",
        ),
        CheckConstraint(
            "offset_months >= 0",
            name="ck_deadline_rule_offset_months_non_negative",
        ),
        Index("idx_deadline_rule_type_effective", "rule_type", "effective_from"),
    )

    def __repr__(self) -> str:
        return (
            f"<DeadlineRule(id={self.id}, type='{self.rule_type}', "
            f"day={self.due_day_of_month}, offset={self.offset_months}, "
            f"from={self.effective_from}, to={self.effective_to})>"
        )
