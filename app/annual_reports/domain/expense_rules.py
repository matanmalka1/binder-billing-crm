from decimal import Decimal

from app.annual_reports.models.annual_report_expense_line import ExpenseCategoryType

# Statutory partial recognition rates — Income Tax Regulations.
# Vehicle: 75% deductible; Telephone/communication: 80%.
STATUTORY_RECOGNITION_RATES: dict[ExpenseCategoryType, Decimal] = {
    ExpenseCategoryType.VEHICLE: Decimal("0.75"),
    ExpenseCategoryType.COMMUNICATION: Decimal("0.80"),
}

DEFAULT_RECOGNITION_RATE = Decimal("1.00")


def default_recognition_rate(category: ExpenseCategoryType) -> Decimal:
    return STATUTORY_RECOGNITION_RATES.get(category, DEFAULT_RECOGNITION_RATE)
