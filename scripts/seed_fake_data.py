#!/usr/bin/env python3
"""Populate the local database with fake but coherent demo data."""

from __future__ import annotations

import argparse
import os
import random
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Ensure local scripts can run even when JWT_SECRET is not exported in shell.
os.environ.setdefault("JWT_SECRET", "dev-seed-secret")
os.environ.setdefault("APP_ENV", "development")

# Make `app` imports work when running as: python3 scripts/seed_fake_data.py
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.database import Base, SessionLocal, engine
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.users.models.user_audit_log import AuditAction, AuditStatus, UserAuditLog
from app.annual_reports.models.annual_report_model import AnnualReport
from app.annual_reports.models.annual_report_detail import AnnualReportDetail
from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportStatus,
    ClientTypeForReport,
    DeadlineType,
    ReportStage,
)
from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
from app.binders.models.binder import Binder, BinderStatus
from app.binders.models.binder_status_log import BinderStatusLog
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.clients.models.client import Client, ClientStatus, ClientType
from app.clients.models.client_tax_profile import ClientTaxProfile, VatType
from app.correspondence.models.correspondence import Correspondence, CorrespondenceType
from app.permanent_documents.models.permanent_document import PermanentDocument, DocumentType
from app.invoice.models.invoice import Invoice
from app.notification.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)
from app.reminders.models.reminder import Reminder, ReminderStatus, ReminderType
from app.tax_deadline.models.tax_deadline import TaxDeadline, DeadlineType as TaxDeadlineType
from app.users.models.user import User, UserRole


FIRST_NAMES = [
    "Noam",
    "Yael",
    "Avi",
    "Maya",
    "Eitan",
    "Shira",
    "Lior",
    "Tamar",
    "Gal",
    "Neta",
    "Yoni",
    "Dana",
    "Roni",
    "Amir",
]
LAST_NAMES = [
    "Cohen",
    "Levi",
    "Mizrahi",
    "Peretz",
    "Azoulay",
    "Biton",
    "Malka",
    "Friedman",
    "Bar",
    "Harel",
    "Shalev",
    "Katz",
]
COMPANY_WORDS = [
    "Or",
    "Keshet",
    "Magen",
    "Netzach",
    "Hadar",
    "Shafir",
    "Tal",
    "Rimon",
    "Geffen",
    "Negev",
]

# Bcrypt hash for "Password123!" so seeded users can authenticate in local flows.
DEFAULT_PASSWORD_HASH = "$2b$12$GCe3xb22PzzJ4b9/UJwbxeSpuz/v5Uc79Kiv7YCINfz5RDMf54.2a"


@dataclass
class SeedConfig:
    users: int
    clients: int
    min_binders_per_client: int
    max_binders_per_client: int
    min_charges_per_client: int
    max_charges_per_client: int
    annual_reports_per_client: int
    min_tax_deadlines_per_client: int
    max_tax_deadlines_per_client: int
    min_authority_contacts_per_client: int
    max_authority_contacts_per_client: int
    seed: int
    reset: bool


class Seeder:
    def __init__(self, cfg: SeedConfig):
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)

    def run(self) -> None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            if self.cfg.reset:
                self._reset(db)

            users = self._create_users(db)
            clients = self._create_clients(db)
            binders = self._create_binders(db, clients, users)
            charges = self._create_charges(db, clients)
            self._create_invoices(db, charges)
            deadlines = self._create_tax_deadlines(db, clients)
            reports = self._create_annual_reports(db, clients, users)
            self._create_authority_contacts(db, clients)
            self._create_client_tax_profiles(db, clients)
            self._create_correspondence(db, clients, users)
            self._create_annual_report_details(db, reports)
            advance_payments = self._create_advance_payments(db, clients, deadlines)
            self._create_notifications(db, clients, binders)
            self._create_reminders(db, clients, binders, charges, deadlines)
            self._create_documents(db, clients, users)
            self._create_binder_logs(db, binders, users)
            self._create_user_audit_logs(db, users)

            db.commit()
            self._print_counts(db)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _reset(self, db) -> None:
        for model in [
            UserAuditLog,
            BinderStatusLog,
            Notification,
            Reminder,
            AdvancePayment,
            PermanentDocument,
            Invoice,
            TaxDeadline,
            AnnualReportDetail,
            AuthorityContact,
            Correspondence,
            AnnualReport,
            ClientTaxProfile,
            Charge,
            Binder,
            Client,
            User,
        ]:
            db.query(model).delete()
        db.commit()

    def _full_name(self) -> str:
        return f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}"

    def _create_users(self, db):
        users = []
        for i in range(self.cfg.users):
            role = UserRole.ADVISOR if i % 3 == 0 else UserRole.SECRETARY
            user = User(
                full_name=self._full_name(),
                email=f"user{i + 1}@example.com",
                phone=f"05{self.rng.randint(10000000, 99999999)}",
                password_hash=DEFAULT_PASSWORD_HASH,
                role=role,
                is_active=self.rng.random() > 0.1,
                token_version=0,
                created_at=datetime.now(UTC) - timedelta(days=self.rng.randint(10, 300)),
                last_login_at=datetime.now(UTC) - timedelta(days=self.rng.randint(0, 30)),
            )
            db.add(user)
            users.append(user)
        db.flush()
        return users

    def _create_clients(self, db):
        clients = []
        for i in range(self.cfg.clients):
            open_days_ago = self.rng.randint(20, 1100)
            opened_at = date.today() - timedelta(days=open_days_ago)
            status = self.rng.choices(
                [ClientStatus.ACTIVE, ClientStatus.FROZEN, ClientStatus.CLOSED],
                weights=[80, 12, 8],
                k=1,
            )[0]
            closed_at = None
            if status == ClientStatus.CLOSED:
                closed_at = opened_at + timedelta(days=self.rng.randint(30, 800))
                if closed_at > date.today():
                    closed_at = date.today() - timedelta(days=self.rng.randint(1, 15))

            client_type = self.rng.choice(list(ClientType))
            if client_type == ClientType.COMPANY:
                full_name = (
                    f"{self.rng.choice(COMPANY_WORDS)} {self.rng.choice(COMPANY_WORDS)} Ltd"
                )
            else:
                full_name = self._full_name()

            client = Client(
                full_name=full_name,
                id_number=f"{self.rng.randint(100000000, 999999999)}",
                client_type=client_type,
                status=status,
                primary_binder_number=f"PB-{50000 + i}",
                phone=f"05{self.rng.randint(10000000, 99999999)}",
                email=f"client{i + 1}@example.com",
                notes=self.rng.choice(["", "VIP", "Prefers WhatsApp", "Monthly follow-up"]),
                opened_at=opened_at,
                closed_at=closed_at,
            )
            db.add(client)
            clients.append(client)
        db.flush()
        return clients

    def _create_binders(self, db, clients, users):
        binders = []
        binder_serial = 10000
        for client in clients:
            num = self.rng.randint(
                self.cfg.min_binders_per_client,
                self.cfg.max_binders_per_client,
            )
            for _ in range(num):
                received_days_ago = self.rng.randint(0, 120)
                received_at = date.today() - timedelta(days=received_days_ago)
                expected_return_at = received_at + timedelta(days=self.rng.randint(7, 30))

                if self.rng.random() < 0.4:
                    status = BinderStatus.RETURNED
                    returned_at = min(
                        date.today(),
                        expected_return_at + timedelta(days=self.rng.randint(-2, 8)),
                    )
                else:
                    if expected_return_at < date.today():
                        status = self.rng.choice([BinderStatus.OVERDUE, BinderStatus.READY_FOR_PICKUP])
                    else:
                        status = self.rng.choice([BinderStatus.IN_OFFICE, BinderStatus.READY_FOR_PICKUP])
                    returned_at = None

                binder = Binder(
                    client_id=client.id,
                    binder_number=f"B-{binder_serial}",
                    received_at=received_at,
                    expected_return_at=expected_return_at,
                    returned_at=returned_at,
                    status=status,
                    received_by=self.rng.choice(users).id,
                    returned_by=self.rng.choice(users).id if status == BinderStatus.RETURNED else None,
                    pickup_person_name=(self._full_name() if status == BinderStatus.RETURNED else None),
                    notes=self.rng.choice(["", "Urgent handling", "Client requested callback"]),
                )
                binder_serial += 1
                db.add(binder)
                binders.append(binder)
        db.flush()
        return binders

    def _create_charges(self, db, clients):
        charges = []
        for client in clients:
            num = self.rng.randint(
                self.cfg.min_charges_per_client,
                self.cfg.max_charges_per_client,
            )
            for _ in range(num):
                status = self.rng.choices(
                    [ChargeStatus.DRAFT, ChargeStatus.ISSUED, ChargeStatus.PAID, ChargeStatus.CANCELED],
                    weights=[20, 30, 40, 10],
                    k=1,
                )[0]
                created_at = datetime.now(UTC) - timedelta(days=self.rng.randint(0, 240))
                issued_at = None
                paid_at = None
                if status in (ChargeStatus.ISSUED, ChargeStatus.PAID):
                    issued_at = created_at + timedelta(days=self.rng.randint(0, 6))
                if status == ChargeStatus.PAID:
                    paid_at = issued_at + timedelta(days=self.rng.randint(0, 20))

                charge_type = self.rng.choice(list(ChargeType))
                period = None
                if charge_type == ChargeType.RETAINER:
                    month = self.rng.randint(1, 12)
                    year = date.today().year - self.rng.randint(0, 1)
                    period = f"{year}-{month:02d}"

                amount = Decimal(str(round(self.rng.uniform(250, 7500), 2)))
                charge = Charge(
                    client_id=client.id,
                    amount=amount,
                    currency="ILS",
                    charge_type=charge_type,
                    period=period,
                    status=status,
                    created_at=created_at,
                    issued_at=issued_at,
                    paid_at=paid_at,
                )
                db.add(charge)
                charges.append(charge)
        db.flush()
        return charges

    def _create_invoices(self, db, charges):
        invoice_serial = 70000
        for charge in charges:
            if charge.status not in (ChargeStatus.ISSUED, ChargeStatus.PAID):
                continue
            invoice = Invoice(
                charge_id=charge.id,
                provider="demo-provider",
                external_invoice_id=f"INV-{invoice_serial}",
                document_url=f"https://example.local/invoices/INV-{invoice_serial}.pdf",
                issued_at=charge.issued_at or charge.created_at,
                created_at=charge.created_at,
            )
            invoice_serial += 1
            db.add(invoice)
        db.flush()

    def _create_notifications(self, db, clients, binders):
        for binder in binders:
            if self.rng.random() > 0.65:
                continue
            client = clients[binder.client_id - 1]
            is_email = self.rng.random() < 0.35
            channel = NotificationChannel.EMAIL if is_email else NotificationChannel.WHATSAPP
            recipient = client.email if is_email else (client.phone or "0500000000")

            if binder.status == BinderStatus.OVERDUE:
                trigger = NotificationTrigger.BINDER_OVERDUE
            elif binder.status == BinderStatus.READY_FOR_PICKUP:
                trigger = NotificationTrigger.BINDER_READY_FOR_PICKUP
            else:
                trigger = self.rng.choice(
                    [
                        NotificationTrigger.BINDER_RECEIVED,
                        NotificationTrigger.BINDER_APPROACHING_SLA,
                    ]
                )

            status = self.rng.choices(
                [NotificationStatus.SENT, NotificationStatus.PENDING, NotificationStatus.FAILED],
                weights=[75, 18, 7],
                k=1,
            )[0]
            sent_at = datetime.now(UTC) - timedelta(days=self.rng.randint(0, 50)) if status == NotificationStatus.SENT else None
            failed_at = datetime.now(UTC) - timedelta(days=self.rng.randint(0, 50)) if status == NotificationStatus.FAILED else None

            notification = Notification(
                client_id=client.id,
                binder_id=binder.id,
                trigger=trigger,
                channel=channel,
                status=status,
                recipient=recipient,
                content_snapshot=f"Automated message for binder {binder.binder_number}",
                sent_at=sent_at,
                failed_at=failed_at,
                error_message=("provider_timeout" if status == NotificationStatus.FAILED else None),
                created_at=datetime.now(UTC) - timedelta(days=self.rng.randint(0, 60)),
            )
            db.add(notification)
        db.flush()

    def _create_tax_deadlines(self, db, clients):
        deadlines = []
        today = date.today()
        for client in clients:
            num = self.rng.randint(
                self.cfg.min_tax_deadlines_per_client,
                self.cfg.max_tax_deadlines_per_client,
            )
            for _ in range(num):
                due_offset = self.rng.randint(-30, 60)
                due_date = today + timedelta(days=due_offset)
                status = "completed" if due_date < today and self.rng.random() < 0.5 else "pending"
                completed_at = (
                    datetime.now(UTC) - timedelta(days=self.rng.randint(1, 30))
                    if status == "completed"
                    else None
                )
                payment_amount = Decimal(str(round(self.rng.uniform(500, 15000), 2)))
                deadline_type = self.rng.choice(list(TaxDeadlineType))
                description = f"{deadline_type.value.replace('_', ' ').title()} reminder"
                deadline = TaxDeadline(
                    client_id=client.id,
                    deadline_type=deadline_type,
                    due_date=due_date,
                    status=status,
                    payment_amount=payment_amount,
                    currency="ILS",
                    description=description,
                    created_at=datetime.now(UTC) - timedelta(days=self.rng.randint(0, 120)),
                    completed_at=completed_at,
                )
                db.add(deadline)
                deadlines.append(deadline)
        db.flush()
        return deadlines

    def _create_advance_payments(self, db, clients, deadlines):
        payments = []
        deadlines_by_client_month = {}
        for dl in deadlines:
            key = (dl.client_id, dl.due_date.year, dl.due_date.month)
            deadlines_by_client_month[key] = dl

        for client in clients:
            year = date.today().year
            months = self.rng.sample(range(1, 13), k=self.rng.randint(3, 7))
            for month in months:
                due_date = date(year, month, self.rng.randint(10, 28))
                deadline = deadlines_by_client_month.get((client.id, year, month))
                status = self.rng.choice(list(AdvancePaymentStatus))
                expected_amount = Decimal(str(round(self.rng.uniform(500, 6000), 2)))
                paid_amount = None
                if status in (AdvancePaymentStatus.PAID, AdvancePaymentStatus.PARTIAL):
                    paid_amount = Decimal(str(round(self.rng.uniform(200, float(expected_amount)), 2)))

                payment = AdvancePayment(
                    client_id=client.id,
                    tax_deadline_id=deadline.id if deadline else None,
                    month=month,
                    year=year,
                    expected_amount=expected_amount,
                    paid_amount=paid_amount,
                    status=status,
                    due_date=due_date,
                    created_at=datetime.now(UTC) - timedelta(days=self.rng.randint(0, 200)),
                    updated_at=None,
                )
                db.add(payment)
                payments.append(payment)
        db.flush()
        return payments

    def _create_annual_reports(self, db, clients, users):
        reports = []
        current_year = date.today().year
        available_years = list(range(current_year - 3, current_year + 1))
        for client in clients:
            years = self.rng.sample(
                available_years,
                k=min(self.cfg.annual_reports_per_client, len(available_years)),
            )
            for year in years:
                # Map client type to report type/form
                if client.client_type == ClientType.COMPANY:
                    client_type_for_report = ClientTypeForReport.CORPORATION
                    form_type = AnnualReportForm.FORM_6111
                elif client.client_type in (ClientType.OSEK_PATUR, ClientType.OSEK_MURSHE):
                    client_type_for_report = ClientTypeForReport.SELF_EMPLOYED
                    form_type = AnnualReportForm.FORM_1215
                else:
                    client_type_for_report = ClientTypeForReport.INDIVIDUAL
                    form_type = AnnualReportForm.FORM_1301

                status = self.rng.choice(list(AnnualReportStatus))
                filing_deadline = datetime(
                    year,
                    self.rng.randint(5, 12),
                    self.rng.randint(1, 28),
                    tzinfo=UTC,
                )
                submitted_at = (
                    datetime.now(UTC) - timedelta(days=self.rng.randint(1, 120))
                    if status in (AnnualReportStatus.SUBMITTED, AnnualReportStatus.ACCEPTED, AnnualReportStatus.ASSESSMENT_ISSUED, AnnualReportStatus.CLOSED)
                    else None
                )

                report = AnnualReport(
                    client_id=client.id,
                    tax_year=year,
                    client_type=client_type_for_report,
                    form_type=form_type,
                    status=status,
                    deadline_type=self.rng.choice(list(DeadlineType)),
                    filing_deadline=filing_deadline,
                    custom_deadline_note=None,
                    submitted_at=submitted_at,
                    ita_reference=None,
                    assessment_amount=None,
                    refund_due=None,
                    tax_due=None,
                    has_rental_income=self.rng.random() < 0.3,
                    has_capital_gains=self.rng.random() < 0.25,
                    has_foreign_income=self.rng.random() < 0.2,
                    has_depreciation=self.rng.random() < 0.2,
                    has_exempt_rental=self.rng.random() < 0.15,
                    notes=self.rng.choice(["", "Needs review", "Client signature pending"]),
                    created_at=datetime.now(UTC) - timedelta(days=self.rng.randint(0, 400)),
                    updated_at=datetime.now(UTC) - timedelta(days=self.rng.randint(0, 60)),
                    created_by=self.rng.choice([u.id for u in users if u.role == UserRole.ADVISOR]),
                    assigned_to=self.rng.choice([u.id for u in users if u.role == UserRole.ADVISOR]),
                )
                db.add(report)
                reports.append(report)
        db.flush()
        return reports

    def _create_annual_report_details(self, db, reports):
        for report in reports:
            # 60% of reports get an attached detail row
            if self.rng.random() > 0.6:
                continue

            tax_refund_amount = None
            tax_due_amount = None
            # 50/50 chance of refund vs due when present
            if self.rng.random() < 0.5:
                tax_refund_amount = Decimal(str(round(self.rng.uniform(500, 5000), 2)))
            else:
                tax_due_amount = Decimal(str(round(self.rng.uniform(500, 7500), 2)))

            detail = AnnualReportDetail(
                report_id=report.id,
                tax_refund_amount=tax_refund_amount,
                tax_due_amount=tax_due_amount,
                client_approved_at=(
                    datetime.now(UTC) - timedelta(days=self.rng.randint(1, 120))
                    if self.rng.random() < 0.5
                    else None
                ),
                internal_notes=self.rng.choice([
                    None,
                    "Pending client confirmation",
                    "Include revised payroll figures",
                    "Double-check VAT inputs",
                ]),
            )
            db.add(detail)
        db.flush()

    def _create_authority_contacts(self, db, clients):
        contacts = []
        for client in clients:
            num = self.rng.randint(
                self.cfg.min_authority_contacts_per_client,
                self.cfg.max_authority_contacts_per_client,
            )
            for idx in range(num):
                contact = AuthorityContact(
                    client_id=client.id,
                    contact_type=self.rng.choice(list(ContactType)),
                    name=self._full_name(),
                    office=self.rng.choice(["Tel Aviv", "Jerusalem", "Haifa", "Beer Sheva"]),
                    phone=f"07{self.rng.randint(10000000, 99999999)}",
                    email=f"contact{client.id}-{idx}@authority.example",
                    notes=self.rng.choice(["", "Preferred via WhatsApp", "Banking contact"]),
                    created_at=datetime.now(UTC) - timedelta(days=self.rng.randint(0, 300)),
                    updated_at=datetime.now(UTC) - timedelta(days=self.rng.randint(0, 90)),
                )
                db.add(contact)
                contacts.append(contact)
        db.flush()
        return contacts

    def _create_client_tax_profiles(self, db, clients):
        for client in clients:
            # 70% of clients get a tax profile
            if self.rng.random() > 0.7:
                continue

            profile = ClientTaxProfile(
                client_id=client.id,
                vat_type=self.rng.choice(list(VatType)),
                business_type=self.rng.choice([
                    None,
                    "self_employed",
                    "company",
                    "non_profit",
                ]),
                tax_year_start=self.rng.choice([1, 4, 7, 10, None]),
                accountant_name=self.rng.choice([
                    None,
                    "Green & Co.",
                    "TaxWise",
                    "Levi Accounting",
                ]),
                created_at=datetime.now(UTC) - timedelta(days=self.rng.randint(0, 200)),
            )
            db.add(profile)
        db.flush()

    def _create_correspondence(self, db, clients, users):
        for client in clients:
            # 50% of clients get between 1-5 correspondence entries
            if self.rng.random() > 0.5:
                continue

            num_entries = self.rng.randint(1, 5)
            for _ in range(num_entries):
                occurred_at = datetime.now(UTC) - timedelta(days=self.rng.randint(0, 120))
                entry = Correspondence(
                    client_id=client.id,
                    contact_id=None,
                    correspondence_type=self.rng.choice(list(CorrespondenceType)),
                    subject=self.rng.choice([
                        "Discussed tax payment plan",
                        "Submitted missing documents",
                        "Scheduled meeting with authority",
                        "Client requested clarification",
                    ]),
                    notes=self.rng.choice([
                        None,
                        "Follow up next week",
                        "Email summary sent",
                        "Awaiting response",
                    ]),
                    occurred_at=occurred_at,
                    created_by=self.rng.choice(users).id,
                    created_at=occurred_at,
                )
                db.add(entry)
        db.flush()

    def _create_reminders(self, db, clients, binders, charges, deadlines):
        """Seed proactive reminders based on existing entities."""
        reminders = []
        today = date.today()
        binders_by_client = {}
        for binder in binders:
            binders_by_client.setdefault(binder.client_id, []).append(binder)
        charges_by_client = {}
        for charge in charges:
            charges_by_client.setdefault(charge.client_id, []).append(charge)
        deadlines_by_client = {}
        for deadline in deadlines:
            deadlines_by_client.setdefault(deadline.client_id, []).append(deadline)

        for client in clients:
            client_binders = binders_by_client.get(client.id, [])
            client_charges = charges_by_client.get(client.id, [])
            client_deadlines = deadlines_by_client.get(client.id, [])

            # Tax deadline reminder for upcoming pending deadline
            pending_deadlines = [
                dl for dl in client_deadlines if dl.status == "pending"
            ]
            if pending_deadlines:
                deadline = self.rng.choice(pending_deadlines)
                days_before = 7
                send_on = max(today, deadline.due_date - timedelta(days=days_before))
                reminder = Reminder(
                    client_id=client.id,
                    reminder_type=ReminderType.TAX_DEADLINE_APPROACHING,
                    status=ReminderStatus.PENDING,
                    target_date=deadline.due_date,
                    days_before=days_before,
                    send_on=send_on,
                    tax_deadline_id=deadline.id,
                    message=f"תזכורת: מועדי מס מתקרבים ({deadline.deadline_type.name})",
                )
                db.add(reminder)
                reminders.append(reminder)

            # Idle binder reminder for binders not returned
            idle_binders = [
                b for b in client_binders if b.status != BinderStatus.RETURNED
            ]
            if idle_binders:
                binder = self.rng.choice(idle_binders)
                days_idle = max(14, (today - binder.received_at).days)
                reminder = Reminder(
                    client_id=client.id,
                    reminder_type=ReminderType.BINDER_IDLE,
                    status=ReminderStatus.PENDING,
                    target_date=today,
                    days_before=0,
                    send_on=today,
                    binder_id=binder.id,
                    message=f"תזכורת: תיק {binder.binder_number} לא טופל {days_idle} ימים",
                )
                db.add(reminder)
                reminders.append(reminder)

            # Unpaid charge reminders for issued, unpaid charges older than 30 days
            unpaid_charges = [
                c for c in client_charges
                if c.status == ChargeStatus.ISSUED
                and c.issued_at
                and (today - c.issued_at.date()).days >= 30
            ]
            if unpaid_charges:
                charge = self.rng.choice(unpaid_charges)
                days_unpaid = (today - charge.issued_at.date()).days
                reminder = Reminder(
                    client_id=client.id,
                    reminder_type=ReminderType.UNPAID_CHARGE,
                    status=ReminderStatus.PENDING,
                    target_date=today,
                    days_before=0,
                    send_on=today,
                    charge_id=charge.id,
                    message=f"תזכורת: חשבונית #{charge.id} לא שולמה {days_unpaid} ימים",
                )
                db.add(reminder)
                reminders.append(reminder)

        db.flush()
        return reminders

    def _create_documents(self, db, clients, users):
        for client in clients:
            docs = [DocumentType.ID_COPY, DocumentType.POWER_OF_ATTORNEY]
            if self.rng.random() < 0.8:
                docs.append(DocumentType.ENGAGEMENT_AGREEMENT)
            for doc_type in docs:
                document = PermanentDocument(
                    client_id=client.id,
                    document_type=doc_type,
                    storage_key=(
                        f"clients/{client.id}/"
                        f"{doc_type.value}_{self.rng.randint(1000, 9999)}.pdf"
                    ),
                    is_present=self.rng.random() > 0.05,
                    uploaded_by=self.rng.choice(users).id,
                    uploaded_at=datetime.now(UTC) - timedelta(days=self.rng.randint(0, 500)),
                )
                db.add(document)
        db.flush()

    def _create_binder_logs(self, db, binders, users):
        for binder in binders:
            logs = []
            logs.append(("none", BinderStatus.IN_OFFICE.value, "Binder intake"))
            if binder.status == BinderStatus.READY_FOR_PICKUP:
                logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.READY_FOR_PICKUP.value, "Processing complete"))
            elif binder.status == BinderStatus.OVERDUE:
                logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.OVERDUE.value, "SLA breach"))
            elif binder.status == BinderStatus.RETURNED:
                logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.READY_FOR_PICKUP.value, "Ready for pickup"))
                logs.append((BinderStatus.READY_FOR_PICKUP.value, BinderStatus.RETURNED.value, "Picked up"))

            for old_status, new_status, note in logs:
                log = BinderStatusLog(
                    binder_id=binder.id,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=self.rng.choice(users).id,
                    changed_at=datetime.now(UTC) - timedelta(days=self.rng.randint(0, 120)),
                    notes=note,
                )
                db.add(log)
        db.flush()

    def _create_user_audit_logs(self, db, users):
        for user in users:
            success_log = UserAuditLog(
                action=AuditAction.LOGIN_SUCCESS,
                actor_user_id=user.id,
                target_user_id=user.id,
                email=user.email,
                status=AuditStatus.SUCCESS,
                reason=None,
                metadata_json='{"source":"seed"}',
                created_at=datetime.now(UTC) - timedelta(days=self.rng.randint(0, 30)),
            )
            db.add(success_log)

            if self.rng.random() < 0.3:
                fail_log = UserAuditLog(
                    action=AuditAction.LOGIN_FAILURE,
                    actor_user_id=None,
                    target_user_id=user.id,
                    email=user.email,
                    status=AuditStatus.FAILURE,
                    reason="invalid_password",
                    metadata_json='{"source":"seed"}',
                    created_at=datetime.now(UTC) - timedelta(days=self.rng.randint(0, 30)),
                )
                db.add(fail_log)
        db.flush()

    def _print_counts(self, db):
        counts = {
            "users": db.query(User).count(),
            "clients": db.query(Client).count(),
            "binders": db.query(Binder).count(),
            "charges": db.query(Charge).count(),
            "invoices": db.query(Invoice).count(),
            "tax_deadlines": db.query(TaxDeadline).count(),
            "annual_reports": db.query(AnnualReport).count(),
            "annual_report_details": db.query(AnnualReportDetail).count(),
            "authority_contacts": db.query(AuthorityContact).count(),
            "client_tax_profiles": db.query(ClientTaxProfile).count(),
            "correspondence_entries": db.query(Correspondence).count(),
            "notifications": db.query(Notification).count(),
            "permanent_documents": db.query(PermanentDocument).count(),
            "binder_status_logs": db.query(BinderStatusLog).count(),
            "advance_payments": db.query(AdvancePayment).count(),
            "user_audit_logs": db.query(UserAuditLog).count(),
            "reminders": db.query(Reminder).count(),
        }
        print("Seeding completed. Current row counts:")
        for key, value in counts.items():
            print(f"- {key}: {value}")


def parse_args() -> SeedConfig:
    parser = argparse.ArgumentParser(description="Seed local DB with fake demo data")
    parser.add_argument("--users", type=int, default=8, help="Number of users")
    parser.add_argument("--clients", type=int, default=40, help="Number of clients")
    parser.add_argument("--min-binders-per-client", type=int, default=1)
    parser.add_argument("--max-binders-per-client", type=int, default=3)
    parser.add_argument("--min-charges-per-client", type=int, default=1)
    parser.add_argument("--max-charges-per-client", type=int, default=4)
    parser.add_argument(
        "--annual-reports-per-client",
        type=int,
        default=2,
        help="How many annual reports to seed per client",
    )
    parser.add_argument(
        "--min-tax-deadlines-per-client",
        type=int,
        default=2,
        help="Minimum tax deadlines seeded per client",
    )
    parser.add_argument(
        "--max-tax-deadlines-per-client",
        type=int,
        default=5,
        help="Maximum tax deadlines seeded per client",
    )
    parser.add_argument(
        "--min-authority-contacts-per-client",
        type=int,
        default=1,
        help="Minimum authority contacts per client",
    )
    parser.add_argument(
        "--max-authority-contacts-per-client",
        type=int,
        default=3,
        help="Maximum authority contacts per client",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--reset", action="store_true", help="Delete existing rows before seeding")

    args = parser.parse_args()
    if args.min_binders_per_client > args.max_binders_per_client:
        raise ValueError("min-binders-per-client cannot be greater than max-binders-per-client")
    if args.min_charges_per_client > args.max_charges_per_client:
        raise ValueError("min-charges-per-client cannot be greater than max-charges-per-client")
    if args.min_tax_deadlines_per_client > args.max_tax_deadlines_per_client:
        raise ValueError(
            "min-tax-deadlines-per-client cannot be greater than max-tax-deadlines-per-client"
        )
    if args.min_authority_contacts_per_client > args.max_authority_contacts_per_client:
        raise ValueError(
            "min-authority-contacts-per-client cannot be greater than max-authority-contacts-per-client"
        )

    return SeedConfig(
        users=args.users,
        clients=args.clients,
        min_binders_per_client=args.min_binders_per_client,
        max_binders_per_client=args.max_binders_per_client,
        min_charges_per_client=args.min_charges_per_client,
        max_charges_per_client=args.max_charges_per_client,
        annual_reports_per_client=args.annual_reports_per_client,
        min_tax_deadlines_per_client=args.min_tax_deadlines_per_client,
        max_tax_deadlines_per_client=args.max_tax_deadlines_per_client,
        min_authority_contacts_per_client=args.min_authority_contacts_per_client,
        max_authority_contacts_per_client=args.max_authority_contacts_per_client,
        seed=args.seed,
        reset=args.reset,
    )


def main() -> None:
    cfg = parse_args()
    Seeder(cfg).run()


if __name__ == "__main__":
    main()
