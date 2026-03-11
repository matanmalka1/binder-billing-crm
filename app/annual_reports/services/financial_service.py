"""Public annual report financial service facade."""

from app.annual_reports.services.financial_base_service import FinancialBaseService
from app.annual_reports.services.financial_crud_service import FinancialCrudMixin
from app.annual_reports.services.financial_tax_service import FinancialTaxMixin


class AnnualReportFinancialService(FinancialCrudMixin, FinancialTaxMixin, FinancialBaseService):
    """Backward-compatible service combining CRUD, tax, and readiness logic."""


__all__ = ["AnnualReportFinancialService"]
