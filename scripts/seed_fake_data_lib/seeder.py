from __future__ import annotations

import importlib
import random
from pathlib import Path
from typing import Dict

from sqlalchemy import func, inspect, select

from app.database import Base, SessionLocal, engine

from .config import SeedConfig
from .coverage import SeedCoverageValidator
from .domains import (
    binders,
    charges,
    clients,
    contacts,
    documents,
    notifications,
    reminders,
    reports,
    signature_requests,
    taxes,
    users,
    vat,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = PROJECT_ROOT / "app"


def _import_all_model_modules() -> None:
    """Import all model modules so Base.metadata includes every table."""
    for model_file in APP_DIR.glob("*/models/*.py"):
        if model_file.name.startswith("__"):
            continue
        module = ".".join(model_file.relative_to(PROJECT_ROOT).with_suffix("").parts)
        importlib.import_module(module)


def _ensure_schema_ready() -> None:
    """
    Seeder must run on a migrated schema.

    We do not auto-create tables here; run Alembic before seeding.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = {table.name for table in Base.metadata.sorted_tables}
    missing = sorted(expected_tables - existing_tables)
    if missing:
        preview = ", ".join(missing[:8])
        suffix = "..." if len(missing) > 8 else ""
        raise RuntimeError(
            "Database schema is not ready for seeding. Missing tables: "
            f"{preview}{suffix}. Run `alembic upgrade head` first."
        )

    missing_columns: dict[str, list[str]] = {}
    for table in Base.metadata.sorted_tables:
        existing_columns = {col["name"] for col in inspector.get_columns(table.name)}
        expected_columns = {col.name for col in table.columns}
        table_missing_columns = sorted(expected_columns - existing_columns)
        if table_missing_columns:
            missing_columns[table.name] = table_missing_columns

    if missing_columns:
        preview_items: list[str] = []
        for table_name, cols in missing_columns.items():
            preview_items.append(f"{table_name}({', '.join(cols[:4])})")
            if len(preview_items) >= 6:
                break
        suffix = "..." if len(missing_columns) > 6 else ""
        raise RuntimeError(
            "Database schema is not ready for seeding. Missing columns: "
            + "; ".join(preview_items)
            + suffix
            + ". Run `alembic upgrade head` first."
        )


class Seeder:
    def __init__(self, cfg: SeedConfig):
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)
        self.coverage_validator = SeedCoverageValidator(cfg)

    def run(self) -> None:
        _import_all_model_modules()
        _ensure_schema_ready()
        db = SessionLocal()
        try:
            if self.cfg.reset:
                self._reset(db)

            seeded_users = users.create_users(db, self.rng, self.cfg)
            seeded_clients = clients.create_clients(db, self.rng, self.cfg)
            seeded_businesses = clients.create_businesses(db, self.rng, seeded_clients, seeded_users)
            clients.create_business_tax_profiles(db, self.rng, seeded_businesses)
            seeded_binders = binders.create_binders(db, self.rng, self.cfg, seeded_businesses, seeded_users)
            binder_intakes = binders.create_binder_intakes(db, seeded_binders)
            seeded_charges = charges.create_charges(db, self.rng, self.cfg, seeded_businesses, seeded_users)
            charges.create_invoices(db, seeded_charges)
            seeded_deadlines = taxes.create_tax_deadlines(db, self.rng, self.cfg, seeded_businesses, seeded_users)
            seeded_reports = reports.create_annual_reports(db, self.rng, self.cfg, seeded_businesses, seeded_users)
            contacts_seeded = contacts.create_authority_contacts(
                db, self.rng, self.cfg, seeded_clients, seeded_businesses
            )
            contacts.create_correspondence(db, self.rng, seeded_businesses, seeded_users, contacts_seeded)
            reports.create_annual_report_details(db, self.rng, seeded_reports)
            reports.create_annual_report_income_lines(db, self.rng, seeded_reports)
            reports.create_annual_report_expense_lines(db, self.rng, seeded_reports)
            reports.create_annual_report_annex_data(db, self.rng, seeded_reports)
            reports.create_annual_report_schedule_entries(db, self.rng, seeded_reports, seeded_users)
            reports.create_annual_report_credit_points(db, self.rng, seeded_reports)
            reports.create_annual_report_status_history(db, self.rng, seeded_reports, seeded_users)
            taxes.create_advance_payments(db, self.rng, seeded_businesses, seeded_deadlines)
            notifications.create_notifications(db, self.rng, seeded_clients, seeded_businesses, seeded_binders)
            reminders.create_reminders(db, self.rng, seeded_businesses, seeded_binders, seeded_charges, seeded_deadlines)
            seeded_documents = documents.create_documents(db, self.rng, seeded_clients, seeded_businesses, seeded_users)
            binders.create_binder_intake_materials(
                db,
                self.rng,
                seeded_binders,
                seeded_businesses,
                seeded_reports,
                binder_intakes,
            )
            binders.create_binder_logs(db, self.rng, seeded_binders, seeded_users)
            users.create_user_audit_logs(db, self.rng, seeded_users)
            notifications.create_notifications(db, self.rng, seeded_clients, seeded_businesses, seeded_binders, seeded_users)
            vat_work_items = vat.create_vat_work_items(db, self.rng, self.cfg, seeded_businesses, seeded_users)
            vat.create_vat_invoices(db, self.rng, self.cfg, vat_work_items, seeded_users)
            vat.create_vat_audit_logs(db, self.rng, vat_work_items, seeded_users)
            signature_requests_seeded = signature_requests.create_signature_requests(
                db,
                self.rng,
                self.cfg,
                seeded_businesses,
                seeded_clients,
                seeded_users,
                seeded_reports,
                seeded_documents,
            )
            signature_requests.create_signature_audit_events(db, self.rng, signature_requests_seeded)

            db.commit()
            counts = self._collect_counts(db)
            self._assert_full_seed(counts)
            self.coverage_validator.assert_seed_coverage(db, counts)
            self._print_counts(counts)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _reset(self, db) -> None:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()

    def _collect_counts(self, db) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for table in Base.metadata.sorted_tables:
            counts[table.name] = int(db.execute(select(func.count()).select_from(table)).scalar_one())
        return counts

    def _assert_full_seed(self, counts: Dict[str, int]) -> None:
        empty_tables = [table for table, count in counts.items() if count == 0]
        if empty_tables:
            raise RuntimeError(
                "Full-seed validation failed. Empty tables after seeding: "
                + ", ".join(empty_tables)
            )

    def _print_counts(self, counts: Dict[str, int]) -> None:
        print("Seeding completed. Current row counts:")
        for key, value in counts.items():
            print(f"- {key}: {value}")
