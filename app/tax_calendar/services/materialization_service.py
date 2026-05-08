from __future__ import annotations

from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.enums import DeadlineRuleType as DRT, ObligationType
from app.core.exceptions import ConflictError
from app.tax_calendar.models.deadline_rule import DeadlineRule
from app.tax_calendar.models.tax_calendar_entry import TaxCalendarEntry
from app.tax_calendar.services.tax_calendar_entry_service import _resolve_rule, annual_due_date, periodic_due_date

_DEFAULT_RULES = {DRT.VAT_MONTHLY: (15, 1), DRT.VAT_BIMONTHLY: (15, 2), DRT.ADVANCE_MONTHLY: (15, 1), DRT.ADVANCE_BIMONTHLY: (15, 2), DRT.ANNUAL_REPORT: (31, 4)}
_PERIODIC_RULES = {(ObligationType.VAT, 1): DRT.VAT_MONTHLY, (ObligationType.VAT, 2): DRT.VAT_BIMONTHLY, (ObligationType.ADVANCE_PAYMENT, 1): DRT.ADVANCE_MONTHLY, (ObligationType.ADVANCE_PAYMENT, 2): DRT.ADVANCE_BIMONTHLY}


class TaxCalendarMaterializationService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_periodic_entry(self, obligation_type, period: str, period_months_count: int) -> TaxCalendarEntry:
        obligation_type = self._obligation(obligation_type)
        existing = self._find_periodic(obligation_type, period, period_months_count)
        if existing:
            return existing
        year = int(period[:4])
        month = int(period[5:7])
        rule_type = self._periodic_rule_type(obligation_type, period_months_count)
        rule = self._resolve_or_create_rule(rule_type, date(year, 1, 1))
        entry = TaxCalendarEntry(
            obligation_type=obligation_type, period=period, period_months_count=period_months_count,
            tax_year=year, due_date=periodic_due_date(rule, year, month), deadline_rule_id=rule.id,
        )
        return self._insert_or_refetch(entry, lambda: self._find_periodic(obligation_type, period, period_months_count))

    def ensure_annual_entry(self, tax_year: int) -> TaxCalendarEntry:
        existing = self._find_annual(tax_year)
        if existing:
            return existing
        rule = self._resolve_or_create_rule(DRT.ANNUAL_REPORT, date(tax_year + 1, 1, 1))
        entry = TaxCalendarEntry(
            obligation_type=ObligationType.ANNUAL_REPORT, period=None, period_months_count=None,
            tax_year=tax_year, due_date=annual_due_date(rule, tax_year), deadline_rule_id=rule.id,
        )
        return self._insert_or_refetch(entry, lambda: self._find_annual(tax_year))

    def link_vat_work_item(self, item):
        period_type = item.period_type.value if hasattr(item.period_type, "value") else item.period_type
        months = 2 if period_type == "bimonthly" else 1
        entry = self.ensure_periodic_entry(ObligationType.VAT, item.period, months)
        self._assign_entry(item, entry)
        if item.due_date_original is None:
            item.due_date_original = entry.due_date
        if item.due_date_effective is None:
            item.due_date_effective = entry.due_date
        self.db.flush()
        return item

    def link_advance_payment(self, payment):
        entry = self.ensure_periodic_entry(ObligationType.ADVANCE_PAYMENT, payment.period, payment.period_months_count)
        self._assign_entry(payment, entry)
        self.db.flush()
        return payment

    def link_annual_report(self, report):
        entry = self.ensure_annual_entry(report.tax_year)
        self._assign_entry(report, entry)
        self.db.flush()
        return report

    def _resolve_or_create_rule(self, rule_type, on_date: date) -> DeadlineRule:
        try:
            return _resolve_rule(self.db, rule_type=rule_type, on_date=on_date)
        except LookupError:
            day, offset = _DEFAULT_RULES[rule_type]
            rule = DeadlineRule(
                rule_type=rule_type, due_day_of_month=day, offset_months=offset,
                effective_from=date(2023, 1, 1), effective_to=None,
                description="Default tax calendar materialization rule",
            )
            return self._insert_or_refetch(rule, lambda: _resolve_rule(self.db, rule_type=rule_type, on_date=on_date))

    def _insert_or_refetch(self, entity, refetch):
        savepoint = self.db.begin_nested()
        try:
            self.db.add(entity)
            self.db.flush()
            savepoint.commit()
            return entity
        except IntegrityError:
            savepoint.rollback()
            existing = refetch()
            if existing:
                return existing
            raise

    def _find_periodic(self, obligation_type, period, months):
        obligation_type = self._obligation(obligation_type)
        return (
            self.db.query(TaxCalendarEntry)
            .filter(TaxCalendarEntry.obligation_type == obligation_type.value)
            .filter(TaxCalendarEntry.period == period)
            .filter(TaxCalendarEntry.period_months_count == months)
            .one_or_none()
        )

    def _find_annual(self, tax_year: int):
        return (
            self.db.query(TaxCalendarEntry)
            .filter(TaxCalendarEntry.obligation_type == ObligationType.ANNUAL_REPORT.value)
            .filter(TaxCalendarEntry.tax_year == tax_year)
            .one_or_none()
        )

    @staticmethod
    def _periodic_rule_type(obligation_type, months):
        obligation_type = TaxCalendarMaterializationService._obligation(obligation_type)
        return _PERIODIC_RULES[(obligation_type, months)]

    @staticmethod
    def _obligation(value):
        return value if isinstance(value, ObligationType) else ObligationType(value)

    @staticmethod
    def _assign_entry(entity, entry: TaxCalendarEntry) -> None:
        current = entity.tax_calendar_entry_id
        if current is None:
            entity.tax_calendar_entry_id = entry.id
            return
        if int(current) != int(entry.id):
            raise ConflictError("רשומת יומן המס אינה תואמת לחובה", "TAX_CALENDAR.LINK_CONFLICT")
