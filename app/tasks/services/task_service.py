from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.annual_reports.models.annual_report_model import AnnualReport
from app.charge.models.charge import Charge, ChargeStatus
from app.charge.services.constants import UNPAID_CHARGE_TASK_THRESHOLD_DAYS
from app.clients.repositories.active_client_scope import scope_to_active_clients
from app.reminders.models.reminder import ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.services.reminder_context import build_context_map
from app.businesses.repositories.business_repository import BusinessRepository
from app.tasks.schemas.task import DeadlineTask, TaskType, TaskUrgency, UnifiedItem
from app.tax_deadline.models.tax_deadline import TaxDeadline, TaxDeadlineStatus
from app.utils.time_utils import israel_today
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.repositories.vat_compliance_repository import VatComplianceRepository

_UPCOMING_WINDOW_DAYS = 14
_APPROACHING_DAYS = 7

_DONE_ANNUAL_STATUSES = {
    AnnualReportStatus.CLOSED,
    AnnualReportStatus.CANCELED,
    AnnualReportStatus.ACCEPTED,
}


def _urgency(due_date: date, today: date) -> TaskUrgency:
    days = (due_date - today).days
    if days < 0:
        return TaskUrgency.OVERDUE
    if days <= _APPROACHING_DAYS:
        return TaskUrgency.APPROACHING
    return TaskUrgency.UPCOMING


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.today = israel_today()

    def get_tasks(
        self,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> List[DeadlineTask]:
        tasks: List[DeadlineTask] = []
        tasks.extend(self._tax_deadline_tasks(client_record_id))
        tasks.extend(self._vat_filing_tasks(client_record_id))
        tasks.extend(self._annual_report_tasks(client_record_id))
        tasks.extend(self._advance_payment_tasks(client_record_id))
        tasks.extend(self._unpaid_charge_tasks(client_record_id, business_id))
        tasks.sort(key=lambda t: t.due_date)
        return tasks

    def get_unified(
        self,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> List[UnifiedItem]:
        unified: List[UnifiedItem] = [_task_to_unified(t) for t in self.get_tasks(client_record_id, business_id)]

        reminder_repo = ReminderRepository(self.db)
        business_repo = BusinessRepository(self.db)
        if client_record_id is not None:
            reminders = reminder_repo.list_by_client_record(client_record_id, page=1, page_size=200)
        elif business_id is not None:
            reminders = reminder_repo.list_by_business(business_id, page=1, page_size=200)
        else:
            reminders = reminder_repo.list_by_status(ReminderStatus.PENDING, page=1, page_size=200)

        context = build_context_map(self.db, business_repo, reminders)
        for r in reminders:
            ctx = context.get(r.id, {})
            unified.append(UnifiedItem(
                item_type="reminder",
                source_type=r.reminder_type.value,
                source_id=r.id,
                label=ctx.get("client_name") or f"לקוח #{r.client_record_id}",
                due_date=r.target_date,
                urgency=_urgency(r.target_date, self.today).value,
                client_record_id=r.client_record_id,
                business_id=r.business_id,
            ))

        unified.sort(key=lambda x: x.due_date)
        return unified

    def _tax_deadline_tasks(self, client_record_id: Optional[int]) -> List[DeadlineTask]:
        cutoff = self.today + timedelta(days=_UPCOMING_WINDOW_DAYS)
        query = (
            scope_to_active_clients(self.db.query(TaxDeadline), TaxDeadline)
            .filter(
                TaxDeadline.deleted_at.is_(None),
                TaxDeadline.status == TaxDeadlineStatus.PENDING,
                TaxDeadline.due_date <= cutoff,
            )
        )
        if client_record_id is not None:
            query = query.filter(TaxDeadline.client_record_id == client_record_id)
        return [
            DeadlineTask(
                source_type=TaskType.TAX_DEADLINE,
                source_id=td.id,
                label=f"מועד מס: {td.period or td.deadline_type.value}",
                due_date=td.due_date,
                urgency=_urgency(td.due_date, self.today),
                client_record_id=td.client_record_id,
            )
            for td in query.all()
        ]

    def _vat_filing_tasks(self, client_record_id: Optional[int]) -> List[DeadlineTask]:
        tasks = []
        for row in VatComplianceRepository(self.db).get_overdue_unfiled(self.today):
            if client_record_id is not None and row.client_record_id != client_record_id:
                continue
            vat_item = (
                self.db.query(VatWorkItem)
                .filter(
                    VatWorkItem.client_record_id == row.client_record_id,
                    VatWorkItem.period == row.period,
                    VatWorkItem.status != VatWorkItemStatus.FILED,
                    VatWorkItem.deleted_at.is_(None),
                )
                .first()
            )
            if not vat_item:
                continue
            due_date = date(int(row.period[:4]), int(row.period[5:7]), 19)
            tasks.append(DeadlineTask(
                source_type=TaskType.VAT_FILING,
                source_id=vat_item.id,
                label=f'מע"מ לא הוגש: {row.period}',
                due_date=due_date,
                urgency=_urgency(due_date, self.today),
                client_record_id=row.client_record_id,
            ))
        return tasks

    def _annual_report_tasks(self, client_record_id: Optional[int]) -> List[DeadlineTask]:
        cutoff = self.today + timedelta(days=_UPCOMING_WINDOW_DAYS)
        query = (
            scope_to_active_clients(self.db.query(AnnualReport), AnnualReport)
            .filter(
                AnnualReport.deleted_at.is_(None),
                AnnualReport.filing_deadline.isnot(None),
                AnnualReport.filing_deadline <= cutoff,
                AnnualReport.status.notin_([s.value for s in _DONE_ANNUAL_STATUSES]),
            )
        )
        if client_record_id is not None:
            query = query.filter(AnnualReport.client_record_id == client_record_id)
        return [
            DeadlineTask(
                source_type=TaskType.ANNUAL_REPORT,
                source_id=report.id,
                label=f"דוח שנתי {report.tax_year}",
                due_date=report.filing_deadline.date() if hasattr(report.filing_deadline, "date") else report.filing_deadline,
                urgency=_urgency(
                    report.filing_deadline.date() if hasattr(report.filing_deadline, "date") else report.filing_deadline,
                    self.today,
                ),
                client_record_id=report.client_record_id,
            )
            for report in query.all()
        ]

    def _advance_payment_tasks(self, client_record_id: Optional[int]) -> List[DeadlineTask]:
        cutoff = self.today + timedelta(days=_UPCOMING_WINDOW_DAYS)
        query = (
            scope_to_active_clients(self.db.query(AdvancePayment), AdvancePayment)
            .filter(
                AdvancePayment.deleted_at.is_(None),
                AdvancePayment.status.in_([AdvancePaymentStatus.PENDING, AdvancePaymentStatus.OVERDUE]),
                AdvancePayment.due_date <= cutoff,
            )
        )
        if client_record_id is not None:
            query = query.filter(AdvancePayment.client_record_id == client_record_id)
        return [
            DeadlineTask(
                source_type=TaskType.ADVANCE_PAYMENT,
                source_id=ap.id,
                label=f"מקדמה: {ap.period}",
                due_date=ap.due_date,
                urgency=_urgency(ap.due_date, self.today),
                client_record_id=ap.client_record_id,
            )
            for ap in query.all()
        ]

    def _unpaid_charge_tasks(
        self, client_record_id: Optional[int], business_id: Optional[int]
    ) -> List[DeadlineTask]:
        threshold = self.today - timedelta(days=UNPAID_CHARGE_TASK_THRESHOLD_DAYS)
        query = (
            scope_to_active_clients(self.db.query(Charge), Charge)
            .filter(
                Charge.deleted_at.is_(None),
                Charge.status == ChargeStatus.ISSUED,
                Charge.issued_at.isnot(None),
                Charge.issued_at <= threshold,
            )
        )
        if client_record_id is not None:
            query = query.filter(Charge.client_record_id == client_record_id)
        if business_id is not None:
            query = query.filter(Charge.business_id == business_id)
        return [
            DeadlineTask(
                source_type=TaskType.UNPAID_CHARGE,
                source_id=charge.id,
                label=f"חיוב לא שולם",
                due_date=charge.issued_at.date() + timedelta(days=UNPAID_CHARGE_TASK_THRESHOLD_DAYS),
                urgency=TaskUrgency.OVERDUE,
                client_record_id=charge.client_record_id,
                business_id=charge.business_id,
            )
            for charge in query.all()
        ]


def _task_to_unified(task: DeadlineTask) -> UnifiedItem:
    return UnifiedItem(
        item_type="task",
        source_type=task.source_type.value,
        source_id=task.source_id,
        label=task.label,
        due_date=task.due_date,
        urgency=task.urgency.value,
        client_record_id=task.client_record_id,
        business_id=task.business_id,
    )
