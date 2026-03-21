from __future__ import annotations

from typing import Dict, Iterable

from sqlalchemy import func, select


class SeedCoverageValidator:
    def __init__(self, cfg):
        self.cfg = cfg

    def assert_seed_coverage(self, db, counts: Dict[str, int]) -> None:
        # Imported lazily to keep module import light and avoid mapper ordering issues.
        from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
        from app.annual_reports.models.annual_report_annex_data import AnnualReportAnnexData
        from app.annual_reports.models.annual_report_credit_point_reason import AnnualReportCreditPoint
        from app.annual_reports.models.annual_report_enums import AnnualReportSchedule, AnnualReportStatus
        from app.annual_reports.models.annual_report_expense_line import AnnualReportExpenseLine
        from app.annual_reports.models.annual_report_income_line import AnnualReportIncomeLine
        from app.annual_reports.models.annual_report_model import AnnualReport
        from app.annual_reports.models.annual_report_schedule_entry import AnnualReportScheduleEntry
        from app.annual_reports.models.annual_report_status_history import AnnualReportStatusHistory
        from app.authority_contact.models.authority_contact import AuthorityContact
        from app.binders.models.binder import Binder, BinderStatus
        from app.binders.models.binder_intake import BinderIntake
        from app.binders.models.binder_intake_material import BinderIntakeMaterial
        from app.businesses.models.business import Business
        from app.businesses.models.business_tax_profile import BusinessTaxProfile
        from app.charge.models.charge import Charge, ChargeStatus
        from app.clients.models.client import Client
        from app.notification.models.notification import Notification, NotificationChannel, NotificationStatus
        from app.permanent_documents.models.permanent_document import PermanentDocument
        from app.reminders.models.reminder import Reminder, ReminderType
        from app.signature_requests.models.signature_request import (
            SignatureAuditEvent,
            SignatureRequest,
            SignatureRequestStatus,
            SignatureRequestType,
        )
        from app.tax_deadline.models.tax_deadline import DeadlineType as TaxDeadlineType
        from app.tax_deadline.models.tax_deadline import TaxDeadline, TaxDeadlineStatus
        from app.users.models.user import User
        from app.vat_reports.models.vat_enums import InvoiceType as VatInvoiceType
        from app.vat_reports.models.vat_enums import VatWorkItemStatus
        from app.vat_reports.models.vat_invoice import VatInvoice
        from app.vat_reports.models.vat_work_item import VatWorkItem

        errors: list[str] = []

        expected_reports_per_client = min(self.cfg.annual_reports_per_client, 4)
        expected_reports = self.cfg.clients * expected_reports_per_client
        expected_signature_requests = self.cfg.clients * self.cfg.signature_requests_per_client
        expected_schedule_entries = expected_reports * len(AnnualReportSchedule)

        self._expect_exact_count(errors, counts, "users", self.cfg.users)
        self._expect_exact_count(errors, counts, "clients", self.cfg.clients)
        self._expect_exact_count(errors, counts, "annual_reports", expected_reports)
        self._expect_exact_count(errors, counts, "signature_requests", expected_signature_requests)
        self._expect_exact_count(errors, counts, "annual_report_schedules", expected_schedule_entries)

        self._expect_min_count(errors, counts, "permanent_documents", self.cfg.clients * 2)
        self._expect_min_count(errors, counts, "user_audit_logs", self.cfg.users)
        self._expect_min_count(errors, counts, "annual_report_income_lines", expected_reports)
        self._expect_min_count(errors, counts, "annual_report_expense_lines", expected_reports)
        self._expect_min_count(errors, counts, "annual_report_annex_data", expected_reports)
        self._expect_min_count(errors, counts, "annual_report_status_history", expected_reports)
        self._expect_min_count(errors, counts, "annual_report_credit_points", expected_reports)
        self._expect_min_count(errors, counts, "business_tax_profiles", self.cfg.clients)
        self._expect_min_count(errors, counts, "binder_intake_materials", self.cfg.clients)

        client_ids = [client_id for (client_id,) in db.execute(select(Client.id)).all()]
        if len(client_ids) != self.cfg.clients:
            errors.append(
                f"expected {self.cfg.clients} clients for coverage checks, found {len(client_ids)}"
            )
        business_rows = db.execute(select(Business.id, Business.client_id)).all()
        business_client_map = {int(business_id): int(client_id) for business_id, client_id in business_rows}
        if len(business_client_map) < len(client_ids):
            errors.append(
                f"business coverage mismatch: expected at least {len(client_ids)} businesses, got {len(business_client_map)}"
            )
        business_ids = list(business_client_map.keys())

        self._assert_per_client_bounds(
            errors,
            label="binders/client",
            client_ids=client_ids,
            per_client_counts=self._count_by_fk(db, Binder, Binder.client_id),
            minimum=self.cfg.min_binders_per_client,
            maximum=self.cfg.max_binders_per_client,
        )
        self._assert_per_client_bounds(
            errors,
            label="charges/client",
            client_ids=client_ids,
            per_client_counts=self._count_by_business_fk(db, Charge.business_id, business_client_map),
            minimum=self.cfg.min_charges_per_client,
            maximum=self.cfg.max_charges_per_client,
        )
        self._assert_per_client_bounds(
            errors,
            label="tax_deadlines/client",
            client_ids=client_ids,
            per_client_counts=self._count_by_business_fk(db, TaxDeadline.business_id, business_client_map),
            minimum=self.cfg.min_tax_deadlines_per_client,
            maximum=self.cfg.max_tax_deadlines_per_client,
        )
        self._assert_per_client_bounds(
            errors,
            label="authority_contacts/client",
            client_ids=client_ids,
            per_client_counts=self._count_by_business_fk(db, AuthorityContact.business_id, business_client_map),
            minimum=self.cfg.min_authority_contacts_per_client,
            maximum=self.cfg.max_authority_contacts_per_client,
        )
        self._assert_per_client_bounds(
            errors,
            label="vat_work_items/client",
            client_ids=client_ids,
            per_client_counts=self._count_by_business_fk(db, VatWorkItem.business_id, business_client_map),
            minimum=self.cfg.min_vat_work_items_per_client,
            maximum=self.cfg.max_vat_work_items_per_client,
        )
        self._assert_per_client_bounds(
            errors,
            label="annual_reports/client",
            client_ids=client_ids,
            per_client_counts=self._count_by_business_fk(db, AnnualReport.business_id, business_client_map),
            minimum=expected_reports_per_client,
            maximum=expected_reports_per_client,
        )
        self._assert_per_client_bounds(
            errors,
            label="signature_requests/client",
            client_ids=client_ids,
            per_client_counts=self._count_by_business_fk(db, SignatureRequest.business_id, business_client_map),
            minimum=self.cfg.signature_requests_per_client,
            maximum=self.cfg.signature_requests_per_client,
        )
        self._assert_per_client_bounds(
            errors,
            label="permanent_documents/client",
            client_ids=client_ids,
            per_client_counts=self._count_by_fk(db, PermanentDocument, PermanentDocument.client_id),
            minimum=2,
            maximum=3,
        )
        self._assert_per_client_bounds(
            errors,
            label="advance_payments/client",
            client_ids=client_ids,
            per_client_counts=self._count_by_business_fk(db, AdvancePayment.business_id, business_client_map),
            minimum=3,
            maximum=7,
        )

        issued_or_paid_count = int(
            db.execute(
                select(func.count())
                .select_from(Charge)
                .where(Charge.status.in_([ChargeStatus.ISSUED, ChargeStatus.PAID]))
            ).scalar_one()
        )
        invoice_count = counts.get("invoices", 0)
        if invoice_count != issued_or_paid_count:
            errors.append(
                f"invoices mismatch: expected {issued_or_paid_count} (issued/paid charges), got {invoice_count}"
            )

        report_ids = [report_id for (report_id,) in db.execute(select(AnnualReport.id)).all()]
        schedule_counts = self._count_by_fk(db, AnnualReportScheduleEntry, AnnualReportScheduleEntry.annual_report_id)
        expected_schedule_count_per_report = len(AnnualReportSchedule)
        self._assert_fk_presence(
            errors,
            label="annual_report_schedules/report",
            parent_ids=report_ids,
            fk_counts=schedule_counts,
            minimum=expected_schedule_count_per_report,
            maximum=expected_schedule_count_per_report,
        )
        self._assert_fk_presence(
            errors,
            label="annual_report_income_lines/report",
            parent_ids=report_ids,
            fk_counts=self._count_by_fk(db, AnnualReportIncomeLine, AnnualReportIncomeLine.annual_report_id),
            minimum=1,
        )
        self._assert_fk_presence(
            errors,
            label="annual_report_expense_lines/report",
            parent_ids=report_ids,
            fk_counts=self._count_by_fk(db, AnnualReportExpenseLine, AnnualReportExpenseLine.annual_report_id),
            minimum=1,
        )
        self._assert_fk_presence(
            errors,
            label="annual_report_annex_data/report",
            parent_ids=report_ids,
            fk_counts=self._count_by_fk(db, AnnualReportAnnexData, AnnualReportAnnexData.annual_report_id),
            minimum=1,
        )
        self._assert_fk_presence(
            errors,
            label="annual_report_status_history/report",
            parent_ids=report_ids,
            fk_counts=self._count_by_fk(db, AnnualReportStatusHistory, AnnualReportStatusHistory.annual_report_id),
            minimum=1,
        )
        self._assert_fk_presence(
            errors,
            label="annual_report_credit_points/report",
            parent_ids=report_ids,
            fk_counts=self._count_by_fk(db, AnnualReportCreditPoint, AnnualReportCreditPoint.annual_report_id),
            minimum=1,
        )
        self._assert_fk_presence(
            errors,
            label="business_tax_profiles/business",
            parent_ids=business_ids,
            fk_counts=self._count_by_fk(db, BusinessTaxProfile, BusinessTaxProfile.business_id),
            minimum=1,
            maximum=1,
        )
        intake_ids = [intake_id for (intake_id,) in db.execute(select(BinderIntake.id)).all()]
        self._assert_fk_presence(
            errors,
            label="binder_intake_materials/intake",
            parent_ids=intake_ids,
            fk_counts=self._count_by_fk(db, BinderIntakeMaterial, BinderIntakeMaterial.intake_id),
            minimum=1,
        )

        signature_request_ids = [
            request_id for (request_id,) in db.execute(select(SignatureRequest.id)).all()
        ]
        self._assert_fk_presence(
            errors,
            label="signature_audit_events/request",
            parent_ids=signature_request_ids,
            fk_counts=self._count_by_fk(
                db,
                SignatureAuditEvent,
                SignatureAuditEvent.signature_request_id,
            ),
            minimum=1,
        )
        sent_without_sent_at = int(
            db.execute(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.status == NotificationStatus.SENT,
                    Notification.sent_at.is_(None),
                )
            ).scalar_one()
        )
        failed_without_failed_at = int(
            db.execute(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.status == NotificationStatus.FAILED,
                    Notification.failed_at.is_(None),
                )
            ).scalar_one()
        )
        if sent_without_sent_at:
            errors.append(f"notifications with SENT status and missing sent_at: {sent_without_sent_at}")
        if failed_without_failed_at:
            errors.append(f"notifications with FAILED status and missing failed_at: {failed_without_failed_at}")

        for reminder_type, required_fk, label in [
            (ReminderType.TAX_DEADLINE_APPROACHING, Reminder.tax_deadline_id, "tax_deadline_id"),
            (ReminderType.BINDER_IDLE, Reminder.binder_id, "binder_id"),
            (ReminderType.UNPAID_CHARGE, Reminder.charge_id, "charge_id"),
        ]:
            missing_fk_count = int(
                db.execute(
                    select(func.count())
                    .select_from(Reminder)
                    .where(
                        Reminder.reminder_type == reminder_type,
                        required_fk.is_(None),
                    )
                ).scalar_one()
            )
            if missing_fk_count:
                errors.append(
                    f"reminders of type {reminder_type.value} missing {label}: {missing_fk_count}"
                )

        self._assert_ascii_email_column(errors, "users.email", db.execute(select(User.id, User.email)).all())
        self._assert_ascii_email_column(errors, "clients.email", db.execute(select(Client.id, Client.email)).all())
        self._assert_ascii_email_column(
            errors,
            "authority_contacts.email",
            db.execute(select(AuthorityContact.id, AuthorityContact.email)).all(),
        )
        self._assert_ascii_email_column(
            errors,
            "signature_requests.signer_email",
            db.execute(select(SignatureRequest.id, SignatureRequest.signer_email)).all(),
        )

        self._assert_enum_coverage(
            errors,
            label="binders.status",
            db=db,
            column=Binder.status,
            expected=[item for item in BinderStatus],
            row_count=counts.get("binders", 0),
        )
        self._assert_enum_coverage(
            errors,
            label="charges.status",
            db=db,
            column=Charge.status,
            expected=[item for item in ChargeStatus],
            row_count=counts.get("charges", 0),
        )
        self._assert_enum_coverage(
            errors,
            label="notifications.status",
            db=db,
            column=Notification.status,
            expected=[item for item in NotificationStatus],
            row_count=counts.get("notifications", 0),
        )
        self._assert_enum_coverage(
            errors,
            label="notifications.channel",
            db=db,
            column=Notification.channel,
            expected=[item for item in NotificationChannel],
            row_count=counts.get("notifications", 0),
        )
        self._assert_enum_coverage(
            errors,
            label="tax_deadlines.status",
            db=db,
            column=TaxDeadline.status,
            expected=[item for item in TaxDeadlineStatus],
            row_count=counts.get("tax_deadlines", 0),
        )
        self._assert_enum_coverage(
            errors,
            label="tax_deadlines.deadline_type",
            db=db,
            column=TaxDeadline.deadline_type,
            expected=[item for item in TaxDeadlineType],
            row_count=counts.get("tax_deadlines", 0),
        )
        self._assert_enum_coverage(
            errors,
            label="annual_reports.status",
            db=db,
            column=AnnualReport.status,
            expected=[item for item in AnnualReportStatus],
            row_count=counts.get("annual_reports", 0),
        )
        self._assert_enum_coverage(
            errors,
            label="vat_work_items.status",
            db=db,
            column=VatWorkItem.status,
            expected=[item for item in VatWorkItemStatus],
            row_count=counts.get("vat_work_items", 0),
        )
        self._assert_enum_coverage(
            errors,
            label="signature_requests.status",
            db=db,
            column=SignatureRequest.status,
            expected=[item for item in SignatureRequestStatus],
            row_count=counts.get("signature_requests", 0),
        )
        self._assert_enum_coverage(
            errors,
            label="signature_requests.request_type",
            db=db,
            column=SignatureRequest.request_type,
            expected=[item for item in SignatureRequestType],
            row_count=counts.get("signature_requests", 0),
        )
        self._assert_enum_coverage(
            errors,
            label="advance_payments.status",
            db=db,
            column=AdvancePayment.status,
            expected=[item for item in AdvancePaymentStatus],
            row_count=counts.get("advance_payments", 0),
        )
        self._assert_enum_coverage(
            errors,
            label="vat_invoices.invoice_type",
            db=db,
            column=VatInvoice.invoice_type,
            expected=[item for item in VatInvoiceType],
            row_count=counts.get("vat_invoices", 0),
        )
        self._assert_enum_coverage(
            errors,
            label="reminders.reminder_type(core)",
            db=db,
            column=Reminder.reminder_type,
            expected=[
                ReminderType.TAX_DEADLINE_APPROACHING,
                ReminderType.BINDER_IDLE,
                ReminderType.UNPAID_CHARGE,
            ],
            row_count=counts.get("reminders", 0),
        )

        if errors:
            raise RuntimeError("Seed coverage validation failed:\n- " + "\n- ".join(errors))

    @staticmethod
    def _expect_exact_count(errors: list[str], counts: Dict[str, int], table_name: str, expected: int) -> None:
        actual = counts.get(table_name, 0)
        if actual != expected:
            errors.append(f"{table_name}: expected {expected}, got {actual}")

    @staticmethod
    def _expect_min_count(errors: list[str], counts: Dict[str, int], table_name: str, expected_minimum: int) -> None:
        actual = counts.get(table_name, 0)
        if actual < expected_minimum:
            errors.append(f"{table_name}: expected at least {expected_minimum}, got {actual}")

    @staticmethod
    def _count_by_fk(db, model, fk_column) -> Dict[int, int]:
        rows = db.execute(
            select(fk_column, func.count())
            .group_by(fk_column)
        ).all()
        return {int(fk_id): int(count) for fk_id, count in rows if fk_id is not None}

    @staticmethod
    def _count_by_business_fk(db, business_fk_column, business_client_map: Dict[int, int]) -> Dict[int, int]:
        per_business_rows = db.execute(
            select(business_fk_column, func.count())
            .group_by(business_fk_column)
        ).all()
        per_client: Dict[int, int] = {}
        for business_id, count in per_business_rows:
            if business_id is None:
                continue
            client_id = business_client_map.get(int(business_id))
            if client_id is None:
                continue
            per_client[client_id] = per_client.get(client_id, 0) + int(count)
        return per_client

    @staticmethod
    def _assert_per_client_bounds(
        errors: list[str],
        label: str,
        client_ids: Iterable[int],
        per_client_counts: Dict[int, int],
        minimum: int,
        maximum: int | None = None,
    ) -> None:
        invalid: list[tuple[int, int]] = []
        for client_id in client_ids:
            count = per_client_counts.get(client_id, 0)
            if count < minimum:
                invalid.append((client_id, count))
                continue
            if maximum is not None and count > maximum:
                invalid.append((client_id, count))
        if invalid:
            preview = ", ".join(f"{client_id}:{count}" for client_id, count in invalid[:8])
            suffix = "..." if len(invalid) > 8 else ""
            max_msg = f" and <= {maximum}" if maximum is not None else ""
            errors.append(
                f"{label}: {len(invalid)} client(s) outside expected range >= {minimum}{max_msg} "
                f"(sample: {preview}{suffix})"
            )

    @staticmethod
    def _assert_fk_presence(
        errors: list[str],
        label: str,
        parent_ids: Iterable[int],
        fk_counts: Dict[int, int],
        minimum: int,
        maximum: int | None = None,
    ) -> None:
        invalid: list[tuple[int, int]] = []
        for parent_id in parent_ids:
            count = fk_counts.get(parent_id, 0)
            if count < minimum:
                invalid.append((parent_id, count))
                continue
            if maximum is not None and count > maximum:
                invalid.append((parent_id, count))
        if invalid:
            preview = ", ".join(f"{parent_id}:{count}" for parent_id, count in invalid[:8])
            suffix = "..." if len(invalid) > 8 else ""
            max_msg = f" and <= {maximum}" if maximum is not None else ""
            errors.append(
                f"{label}: {len(invalid)} record(s) outside expected range >= {minimum}{max_msg} "
                f"(sample: {preview}{suffix})"
            )

    @staticmethod
    def _assert_ascii_email_column(errors: list[str], label: str, rows) -> None:
        invalid = [
            (row_id, value)
            for row_id, value in rows
            if value and isinstance(value, str) and not value.isascii()
        ]
        if invalid:
            preview = ", ".join(f"{row_id}:{value}" for row_id, value in invalid[:5])
            suffix = "..." if len(invalid) > 5 else ""
            errors.append(f"{label} contains non-ASCII values (sample: {preview}{suffix})")

    @staticmethod
    def _assert_enum_coverage(errors: list[str], label: str, db, column, expected, row_count: int) -> None:
        # If there are fewer rows than expected values, don't force full coverage.
        if row_count < len(expected):
            return
        present = {value for (value,) in db.execute(select(column).distinct()).all() if value is not None}
        expected_set = set(expected)
        missing = sorted(item.value for item in expected_set - present)
        if missing:
            errors.append(f"{label} missing values: {', '.join(missing)}")
