from __future__ import annotations

import random
from typing import Dict

from app.advance_payments.models.advance_payment import AdvancePayment
from app.annual_reports.models.annual_report_detail import AnnualReportDetail
from app.annual_reports.models.annual_report_model import AnnualReport
from app.authority_contact.models.authority_contact import AuthorityContact
from app.binders.models.binder import Binder
from app.binders.models.binder_status_log import BinderStatusLog
from app.charge.models.charge import Charge
from app.clients.models.client import Client
from app.clients.models.client_tax_profile import ClientTaxProfile
from app.correspondence.models.correspondence import Correspondence
from app.database import Base, SessionLocal, engine
from app.invoice.models.invoice import Invoice
from app.notification.models.notification import Notification
from app.permanent_documents.models.permanent_document import PermanentDocument
from app.reminders.models.reminder import Reminder
from app.tax_deadline.models.tax_deadline import TaxDeadline
from app.users.models.user import User
from app.users.models.user_audit_log import UserAuditLog

from .config import SeedConfig
from .domains import binders, charges, clients, contacts, documents, notifications, reminders, reports, taxes, users


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

            seeded_users = users.create_users(db, self.rng, self.cfg)
            seeded_clients = clients.create_clients(db, self.rng, self.cfg)
            seeded_binders = binders.create_binders(db, self.rng, self.cfg, seeded_clients, seeded_users)
            seeded_charges = charges.create_charges(db, self.rng, self.cfg, seeded_clients)
            charges.create_invoices(db, seeded_charges)
            seeded_deadlines = taxes.create_tax_deadlines(db, self.rng, self.cfg, seeded_clients)
            seeded_reports = reports.create_annual_reports(db, self.rng, self.cfg, seeded_clients, seeded_users)
            contacts.create_authority_contacts(db, self.rng, self.cfg, seeded_clients)
            contacts.create_client_tax_profiles(db, self.rng, seeded_clients)
            contacts.create_correspondence(db, self.rng, seeded_clients, seeded_users)
            reports.create_annual_report_details(db, self.rng, seeded_reports)
            taxes.create_advance_payments(db, self.rng, seeded_clients, seeded_deadlines)
            notifications.create_notifications(db, self.rng, seeded_clients, seeded_binders)
            reminders.create_reminders(db, self.rng, seeded_clients, seeded_binders, seeded_charges, seeded_deadlines)
            documents.create_documents(db, self.rng, seeded_clients, seeded_users)
            binders.create_binder_logs(db, self.rng, seeded_binders, seeded_users)
            users.create_user_audit_logs(db, self.rng, seeded_users)

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

    def _print_counts(self, db) -> None:
        counts: Dict[str, int] = {
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
