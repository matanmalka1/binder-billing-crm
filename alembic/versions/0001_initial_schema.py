"""initial_schema — full schema from current ORM models

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # If tables already exist, this DB was initialized outside Alembic — skip.
    from sqlalchemy import inspect as sa_inspect
    if "users" in sa_inspect(bind).get_table_names():
        return

    # Drop any pre-existing enum types so this migration is idempotent
    # (handles cases where a previous partial run created types but not tables)
    if not is_sqlite:
        for type_name in [
            "userrole", "auditaction", "auditstatus", "clienttype", "clientstatus",
            "vattype", "contacttype", "clienttypeforreport", "annualreportform",
            "annualreportstatus", "annualreportschedule", "reportstage", "deadlinetype",
            "bindertype", "binderstatus", "taxdeadlinetype", "taxdeadlinestatus",
            "urgencylevel", "chargetype", "chargestatus", "advancepaymentstatus",
            "remindertype", "reminderstatus", "correspondencetype", "incomesourcetype",
            "expensecategorytype", "signaturerequesttype", "signaturerequeststatus",
            "notificationtrigger", "notificationchannel", "notificationstatus",
            "notificationseverity", "vatworkitemstatus", "filingmethod", "invoicetype",
            "expensecategory", "vatratetype", "vatdocumenttype", "documenttype",
            "documentstatus",
        ]:
            bind.execute(sa.text(f"DROP TYPE IF EXISTS {type_name} CASCADE"))

    # ------------------------------------------------------------------ #
    # users                                                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("full_name", sa.String, nullable=False),
        sa.Column("email", sa.String, nullable=False),
        sa.Column("phone", sa.String, nullable=True),
        sa.Column("password_hash", sa.String, nullable=False),
        sa.Column(
            "role",
            sa.Enum("advisor", "secretary", name="userrole"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("token_version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("last_login_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ------------------------------------------------------------------ #
    # user_audit_logs                                                      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "user_audit_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "action",
            sa.Enum(
                "login_success", "login_failure", "logout",
                "user_created", "user_updated", "user_activated",
                "user_deactivated", "password_reset",
                name="auditaction",
            ),
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("target_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("email", sa.String, nullable=True),
        sa.Column(
            "status",
            sa.Enum("success", "failure", name="auditstatus"),
            nullable=False,
        ),
        sa.Column("reason", sa.String, nullable=True),
        sa.Column("metadata_json", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_user_audit_logs_action", "user_audit_logs", ["action"])
    op.create_index("ix_user_audit_logs_actor_user_id", "user_audit_logs", ["actor_user_id"])
    op.create_index("ix_user_audit_logs_target_user_id", "user_audit_logs", ["target_user_id"])
    op.create_index("ix_user_audit_logs_email", "user_audit_logs", ["email"])
    op.create_index("ix_user_audit_logs_status", "user_audit_logs", ["status"])
    op.create_index("ix_user_audit_logs_created_at", "user_audit_logs", ["created_at"])

    # ------------------------------------------------------------------ #
    # clients                                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("full_name", sa.String, nullable=False),
        sa.Column("id_number", sa.String, nullable=False),
        sa.Column(
            "client_type",
            sa.Enum("osek_patur", "osek_murshe", "company", "employee", name="clienttype"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("active", "frozen", "closed", name="clientstatus"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("primary_binder_number", sa.String, nullable=True),
        sa.Column("phone", sa.String, nullable=True),
        sa.Column("email", sa.String, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("address_street", sa.String, nullable=True),
        sa.Column("address_building_number", sa.String, nullable=True),
        sa.Column("address_apartment", sa.String, nullable=True),
        sa.Column("address_city", sa.String, nullable=True),
        sa.Column("address_zip_code", sa.String, nullable=True),
        sa.Column("opened_at", sa.Date, nullable=False),
        sa.Column("closed_at", sa.Date, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
        sa.Column("deleted_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.UniqueConstraint("primary_binder_number", name="uq_clients_primary_binder_number"),
    )
    # Partial unique index: one active client per id_number
    if is_sqlite:
        op.create_index("ix_clients_id_number_active", "clients", ["id_number"])
    else:
        op.execute(
            "CREATE UNIQUE INDEX ix_clients_id_number_active "
            "ON clients (id_number) WHERE deleted_at IS NULL"
        )

    # ------------------------------------------------------------------ #
    # client_tax_profiles                                                  #
    # ------------------------------------------------------------------ #
    op.create_table(
        "client_tax_profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "client_id",
            sa.Integer,
            sa.ForeignKey("clients.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "vat_type",
            sa.Enum("monthly", "bimonthly", "exempt", name="vattype"),
            nullable=True,
        ),
        sa.Column("business_type", sa.String, nullable=True),
        sa.Column("tax_year_start", sa.Integer, nullable=True),
        sa.Column("accountant_name", sa.String, nullable=True),
        sa.Column("advance_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_client_tax_profiles_client_id", "client_tax_profiles", ["client_id"])

    # ------------------------------------------------------------------ #
    # authority_contacts                                                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        "authority_contacts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column(
            "contact_type",
            sa.Enum(
                "assessing_officer", "vat_branch", "national_insurance", "other",
                name="contacttype",
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("office", sa.String, nullable=True),
        sa.Column("phone", sa.String, nullable=True),
        sa.Column("email", sa.String, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
        sa.Column("deleted_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_authority_contacts_client_id", "authority_contacts", ["client_id"])
    op.create_index("idx_authority_contact_type", "authority_contacts", ["contact_type"])

    # ------------------------------------------------------------------ #
    # annual_reports  (must precede binders, charges, etc.)               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "annual_reports",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_to", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("tax_year", sa.Integer, nullable=False),
        sa.Column(
            "client_type",
            sa.Enum(
                "individual", "self_employed", "corporation", "partnership",
                name="clienttypeforreport",
            ),
            nullable=False,
        ),
        sa.Column(
            "form_type",
            sa.Enum("form_1301", "form_1215", "form_6111", name="annualreportform"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "not_started", "collecting_docs", "docs_complete", "in_preparation",
                "pending_client", "submitted", "amended", "accepted",
                "assessment_issued", "objection_filed", "closed",
                name="annualreportstatus",
            ),
            nullable=False,
            server_default="not_started",
        ),
        sa.Column(
            "deadline_type",
            sa.Enum("vat", "advance_payment", "national_insurance", "annual_report", "other", name="deadlinetype"),
            nullable=False,
            server_default="vat",
        ),
        sa.Column("filing_deadline", sa.DateTime, nullable=True),
        sa.Column("custom_deadline_note", sa.String, nullable=True),
        sa.Column("submitted_at", sa.DateTime, nullable=True),
        sa.Column("ita_reference", sa.String, nullable=True),
        sa.Column("assessment_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("refund_due", sa.Numeric(14, 2), nullable=True),
        sa.Column("tax_due", sa.Numeric(14, 2), nullable=True),
        sa.Column("has_rental_income", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("has_capital_gains", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("has_foreign_income", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("has_depreciation", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("has_exempt_rental", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
        sa.Column("deleted_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_annual_reports_client_id", "annual_reports", ["client_id"])
    op.create_index(
        "idx_annual_report_client_year", "annual_reports", ["client_id", "tax_year"], unique=True
    )
    op.create_index("idx_annual_report_status", "annual_reports", ["status"])
    op.create_index("idx_annual_report_deadline", "annual_reports", ["filing_deadline"])
    op.create_index("idx_annual_report_assigned", "annual_reports", ["assigned_to"])

    # ------------------------------------------------------------------ #
    # binders                                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "binders",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("binder_number", sa.String, nullable=False),
        sa.Column(
            "binder_type",
            sa.Enum(
                "vat", "income_tax", "national_insurance", "capital_declaration",
                "annual_report", "salary", "bookkeeping", "other",
                name="bindertype",
            ),
            nullable=False,
        ),
        sa.Column("received_at", sa.Date, nullable=False),
        sa.Column("returned_at", sa.Date, nullable=True),
        sa.Column(
            "status",
            sa.Enum("in_office", "ready_for_pickup", "returned", name="binderstatus"),
            nullable=False,
            server_default="in_office",
        ),
        sa.Column("received_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("returned_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("pickup_person_name", sa.String, nullable=True),
        sa.Column("annual_report_id", sa.Integer, sa.ForeignKey("annual_reports.id"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
        sa.Column("deleted_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_binders_client_id", "binders", ["client_id"])
    op.create_index("ix_binders_annual_report_id", "binders", ["annual_report_id"])
    op.create_index("idx_binder_status", "binders", ["status"])
    op.create_index("idx_binder_received_at", "binders", ["received_at"])
    # Partial unique index on binder_number for non-returned binders
    if is_sqlite:
        op.execute(
            "CREATE UNIQUE INDEX idx_active_binder_unique ON binders (binder_number) "
            "WHERE status != 'returned'"
        )
    else:
        op.execute(
            "CREATE UNIQUE INDEX idx_active_binder_unique ON binders (binder_number) "
            "WHERE status != 'returned'"
        )

    # ------------------------------------------------------------------ #
    # binder_status_logs                                                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        "binder_status_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("binder_id", sa.Integer, sa.ForeignKey("binders.id"), nullable=False),
        sa.Column("old_status", sa.String, nullable=False),
        sa.Column("new_status", sa.String, nullable=False),
        sa.Column("changed_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("changed_at", sa.DateTime, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_binder_status_logs_binder_id", "binder_status_logs", ["binder_id"])

    # ------------------------------------------------------------------ #
    # binder_intakes                                                       #
    # ------------------------------------------------------------------ #
    op.create_table(
        "binder_intakes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("binder_id", sa.Integer, sa.ForeignKey("binders.id"), nullable=False),
        sa.Column("received_at", sa.Date, nullable=False),
        sa.Column("received_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_binder_intakes_binder_id", "binder_intakes", ["binder_id"])

    # ------------------------------------------------------------------ #
    # tax_deadlines                                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "tax_deadlines",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column(
            "deadline_type",
            sa.Enum(
                "vat", "advance_payment", "national_insurance", "annual_report", "other",
                name="taxdeadlinetype",
            ),
            nullable=False,
        ),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "completed", name="taxdeadlinestatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("payment_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ILS"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_tax_deadlines_client_id", "tax_deadlines", ["client_id"])
    op.create_index("ix_tax_deadlines_due_date", "tax_deadlines", ["due_date"])
    op.create_index("idx_tax_deadline_status", "tax_deadlines", ["status"])
    op.create_index("idx_tax_deadline_type", "tax_deadlines", ["deadline_type"])

    # ------------------------------------------------------------------ #
    # charges                                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "charges",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ILS"),
        sa.Column(
            "charge_type",
            sa.Enum("retainer", "one_time", name="chargetype"),
            nullable=False,
        ),
        sa.Column("period", sa.String(7), nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "issued", "paid", "canceled", name="chargestatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("issued_at", sa.DateTime, nullable=True),
        sa.Column("paid_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("issued_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("paid_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("canceled_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("canceled_at", sa.DateTime, nullable=True),
        sa.Column("cancellation_reason", sa.Text, nullable=True),
        sa.Column("annual_report_id", sa.Integer, sa.ForeignKey("annual_reports.id"), nullable=True),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
        sa.Column("deleted_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_charges_client_id", "charges", ["client_id"])
    op.create_index("ix_charges_annual_report_id", "charges", ["annual_report_id"])

    # ------------------------------------------------------------------ #
    # advance_payments                                                     #
    # ------------------------------------------------------------------ #
    op.create_table(
        "advance_payments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("tax_deadline_id", sa.Integer, sa.ForeignKey("tax_deadlines.id"), nullable=True),
        sa.Column("month", sa.Integer, nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("expected_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("paid_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "paid", "partial", "overdue", name="advancepaymentstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("annual_report_id", sa.Integer, sa.ForeignKey("annual_reports.id"), nullable=True),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint(
            "client_id", "year", "month",
            name="uq_advance_payment_client_year_month",
        ),
    )
    op.create_index("ix_advance_payments_client_id", "advance_payments", ["client_id"])
    op.create_index("ix_advance_payments_tax_deadline_id", "advance_payments", ["tax_deadline_id"])
    op.create_index("ix_advance_payments_annual_report_id", "advance_payments", ["annual_report_id"])
    op.create_index("idx_advance_payment_client_year", "advance_payments", ["client_id", "year"])
    op.create_index("idx_advance_payment_status", "advance_payments", ["status"])

    # ------------------------------------------------------------------ #
    # reminders                                                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column(
            "reminder_type",
            sa.Enum(
                "tax_deadline_approaching", "binder_idle", "unpaid_charge", "custom",
                name="remindertype",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "sent", "canceled", name="reminderstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("target_date", sa.Date, nullable=False),
        sa.Column("days_before", sa.Integer, nullable=False),
        sa.Column("send_on", sa.Date, nullable=False),
        sa.Column("binder_id", sa.Integer, sa.ForeignKey("binders.id"), nullable=True),
        sa.Column("charge_id", sa.Integer, sa.ForeignKey("charges.id"), nullable=True),
        sa.Column("tax_deadline_id", sa.Integer, sa.ForeignKey("tax_deadlines.id"), nullable=True),
        sa.Column("annual_report_id", sa.Integer, sa.ForeignKey("annual_reports.id"), nullable=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("sent_at", sa.DateTime, nullable=True),
        sa.Column("canceled_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_reminders_client_id", "reminders", ["client_id"])
    op.create_index("ix_reminders_target_date", "reminders", ["target_date"])
    op.create_index("ix_reminders_send_on", "reminders", ["send_on"])
    op.create_index("ix_reminders_binder_id", "reminders", ["binder_id"])
    op.create_index("ix_reminders_charge_id", "reminders", ["charge_id"])
    op.create_index("ix_reminders_tax_deadline_id", "reminders", ["tax_deadline_id"])
    op.create_index("ix_reminders_annual_report_id", "reminders", ["annual_report_id"])
    op.create_index("idx_reminder_status_send_on", "reminders", ["status", "send_on"])

    # ------------------------------------------------------------------ #
    # correspondence_entries                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "correspondence_entries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column(
            "contact_id",
            sa.Integer,
            sa.ForeignKey("authority_contacts.id"),
            nullable=True,
        ),
        sa.Column(
            "correspondence_type",
            sa.Enum("call", "letter", "email", "meeting", name="correspondencetype"),
            nullable=False,
        ),
        sa.Column("subject", sa.String, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("occurred_at", sa.DateTime, nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
        sa.Column("deleted_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_correspondence_entries_contact_id", "correspondence_entries", ["contact_id"])
    op.create_index("idx_correspondence_client", "correspondence_entries", ["client_id"])
    op.create_index("idx_correspondence_occurred", "correspondence_entries", ["occurred_at"])

    # ------------------------------------------------------------------ #
    # permanent_documents                                                  #
    # ------------------------------------------------------------------ #
    op.create_table(
        "permanent_documents",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("document_type", sa.String, nullable=False),
        sa.Column("storage_key", sa.String, nullable=False),
        sa.Column("tax_year", sa.SmallInteger, nullable=True),
        sa.Column("is_present", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("uploaded_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("superseded_by", sa.Integer, sa.ForeignKey("permanent_documents.id"), nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
        sa.Column("annual_report_id", sa.Integer, sa.ForeignKey("annual_reports.id"), nullable=True),
        sa.Column("original_filename", sa.String, nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("mime_type", sa.String, nullable=True),
        sa.Column("notes", sa.String, nullable=True),
        sa.Column("approved_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_permanent_documents_client_id", "permanent_documents", ["client_id"])
    op.create_index("ix_permanent_documents_tax_year", "permanent_documents", ["tax_year"])
    op.create_index(
        "ix_permanent_documents_client_type_year",
        "permanent_documents",
        ["client_id", "document_type", "tax_year"],
    )

    # ------------------------------------------------------------------ #
    # annual_report_details                                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        "annual_report_details",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "report_id",
            sa.Integer,
            sa.ForeignKey("annual_reports.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("tax_refund_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("tax_due_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("client_approved_at", sa.DateTime, nullable=True),
        sa.Column("credit_points", sa.Numeric(5, 2), nullable=True, server_default="2.25"),
        sa.Column("pension_credit_points", sa.Numeric(5, 2), nullable=True, server_default="0"),
        sa.Column("life_insurance_credit_points", sa.Numeric(5, 2), nullable=True, server_default="0"),
        sa.Column("tuition_credit_points", sa.Numeric(5, 2), nullable=True, server_default="0"),
        sa.Column("pension_contribution", sa.Numeric(12, 2), nullable=True, server_default="0"),
        sa.Column("donation_amount", sa.Numeric(12, 2), nullable=True, server_default="0"),
        sa.Column("other_credits", sa.Numeric(12, 2), nullable=True, server_default="0"),
        sa.Column("internal_notes", sa.Text, nullable=True),
        sa.Column("amendment_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # ------------------------------------------------------------------ #
    # annual_report_income_lines                                           #
    # ------------------------------------------------------------------ #
    op.create_table(
        "annual_report_income_lines",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("annual_report_id", sa.Integer, sa.ForeignKey("annual_reports.id"), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum(
                "business", "salary", "interest", "dividends", "capital_gains",
                "rental", "foreign", "pension", "other",
                name="incomesourcetype",
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "ix_annual_report_income_lines_annual_report_id",
        "annual_report_income_lines",
        ["annual_report_id"],
    )

    # ------------------------------------------------------------------ #
    # annual_report_expense_lines                                          #
    # ------------------------------------------------------------------ #
    op.create_table(
        "annual_report_expense_lines",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("annual_report_id", sa.Integer, sa.ForeignKey("annual_reports.id"), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "office_rent", "professional_services", "salaries", "depreciation",
                "vehicle", "marketing", "insurance", "communication",
                "travel", "training", "bank_fees", "other",
                name="expensecategorytype",
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("recognition_rate", sa.Numeric(5, 2), nullable=False, server_default="1.00"),
        sa.Column("supporting_document_ref", sa.String(255), nullable=True),
        sa.Column(
            "supporting_document_id",
            sa.Integer,
            sa.ForeignKey("permanent_documents.id"),
            nullable=True,
        ),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "ix_annual_report_expense_lines_annual_report_id",
        "annual_report_expense_lines",
        ["annual_report_id"],
    )
    op.create_index(
        "ix_annual_report_expense_lines_supporting_document_id",
        "annual_report_expense_lines",
        ["supporting_document_id"],
    )

    # ------------------------------------------------------------------ #
    # annual_report_annex_data                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "annual_report_annex_data",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("annual_report_id", sa.Integer, sa.ForeignKey("annual_reports.id"), nullable=False),
        sa.Column(
            "schedule",
            sa.Enum(
                "schedule_b", "schedule_bet", "schedule_gimmel",
                "schedule_dalet", "schedule_heh",
                name="annualreportschedule",
            ),
            nullable=False,
        ),
        sa.Column("line_number", sa.Integer, nullable=False),
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "ix_annual_report_annex_data_annual_report_id",
        "annual_report_annex_data",
        ["annual_report_id"],
    )

    # ------------------------------------------------------------------ #
    # annual_report_schedules                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "annual_report_schedules",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("annual_report_id", sa.Integer, sa.ForeignKey("annual_reports.id"), nullable=False),
        sa.Column(
            "schedule",
            sa.Enum(
                "schedule_b", "schedule_bet", "schedule_gimmel",
                "schedule_dalet", "schedule_heh",
                name="annualreportschedule",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_complete", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "ix_annual_report_schedules_annual_report_id",
        "annual_report_schedules",
        ["annual_report_id"],
    )

    # ------------------------------------------------------------------ #
    # annual_report_status_history                                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "annual_report_status_history",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("annual_report_id", sa.Integer, sa.ForeignKey("annual_reports.id"), nullable=False),
        sa.Column(
            "from_status",
            sa.Enum(
                "not_started", "collecting_docs", "docs_complete", "in_preparation",
                "pending_client", "submitted", "amended", "accepted",
                "assessment_issued", "objection_filed", "closed",
                name="annualreportstatus",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "to_status",
            sa.Enum(
                "not_started", "collecting_docs", "docs_complete", "in_preparation",
                "pending_client", "submitted", "amended", "accepted",
                "assessment_issued", "objection_filed", "closed",
                name="annualreportstatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("changed_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("changed_by_name", sa.String, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("occurred_at", sa.DateTime, nullable=False),
    )
    op.create_index(
        "ix_annual_report_status_history_annual_report_id",
        "annual_report_status_history",
        ["annual_report_id"],
    )

    # ------------------------------------------------------------------ #
    # signature_requests                                                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        "signature_requests",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("annual_report_id", sa.Integer, sa.ForeignKey("annual_reports.id"), nullable=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("permanent_documents.id"), nullable=True),
        sa.Column(
            "request_type",
            sa.Enum(
                "engagement_agreement", "annual_report_approval",
                "power_of_attorney", "vat_return_approval", "custom",
                name="signaturerequesttype",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("content_hash", sa.String, nullable=True),
        sa.Column("storage_key", sa.String, nullable=True),
        sa.Column("signer_name", sa.String, nullable=False),
        sa.Column("signer_email", sa.String, nullable=True),
        sa.Column("signer_phone", sa.String, nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "pending_signature", "signed", "declined", "expired", "canceled",
                name="signaturerequeststatus",
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("signing_token", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("sent_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("signed_at", sa.DateTime, nullable=True),
        sa.Column("declined_at", sa.DateTime, nullable=True),
        sa.Column("canceled_at", sa.DateTime, nullable=True),
        sa.Column("signer_ip_address", sa.String, nullable=True),
        sa.Column("signer_user_agent", sa.String, nullable=True),
        sa.Column("decline_reason", sa.Text, nullable=True),
        sa.Column("signed_document_key", sa.String, nullable=True),
    )
    op.create_index("ix_signature_requests_client_id", "signature_requests", ["client_id"])
    op.create_index("ix_signature_requests_signing_token", "signature_requests", ["signing_token"], unique=True)
    op.create_index("idx_sig_request_client", "signature_requests", ["client_id"])
    op.create_index("idx_sig_request_status", "signature_requests", ["status"])
    op.create_index("idx_sig_request_token", "signature_requests", ["signing_token"])
    op.create_index("idx_sig_request_annual_report", "signature_requests", ["annual_report_id"])

    # signature_audit_events
    op.create_table(
        "signature_audit_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "signature_request_id",
            sa.Integer,
            sa.ForeignKey("signature_requests.id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("actor_type", sa.String, nullable=False),
        sa.Column("actor_id", sa.Integer, nullable=True),
        sa.Column("actor_name", sa.String, nullable=True),
        sa.Column("ip_address", sa.String, nullable=True),
        sa.Column("user_agent", sa.String, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("occurred_at", sa.DateTime, nullable=False),
    )
    op.create_index(
        "ix_signature_audit_events_signature_request_id",
        "signature_audit_events",
        ["signature_request_id"],
    )
    op.create_index("idx_sig_audit_request", "signature_audit_events", ["signature_request_id"])
    op.create_index("idx_sig_audit_occurred", "signature_audit_events", ["occurred_at"])

    # ------------------------------------------------------------------ #
    # notifications                                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("binder_id", sa.Integer, sa.ForeignKey("binders.id"), nullable=True),
        sa.Column(
            "trigger",
            sa.Enum(
                "binder_received", "binder_ready_for_pickup", "manual_payment_reminder",
                name="notificationtrigger",
            ),
            nullable=False,
        ),
        sa.Column(
            "channel",
            sa.Enum("whatsapp", "email", name="notificationchannel"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "sent", "failed", name="notificationstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "severity",
            sa.Enum("info", "warning", "urgent", "critical", name="notificationseverity"),
            nullable=False,
            server_default="info",
        ),
        sa.Column("recipient", sa.String, nullable=False),
        sa.Column("content_snapshot", sa.Text, nullable=False),
        sa.Column("sent_at", sa.DateTime, nullable=True),
        sa.Column("failed_at", sa.DateTime, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("read_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("triggered_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_notifications_client_id", "notifications", ["client_id"])
    op.create_index("ix_notifications_binder_id", "notifications", ["binder_id"])

    # ------------------------------------------------------------------ #
    # invoices  (internal domain)                                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("charge_id", sa.Integer, sa.ForeignKey("charges.id"), nullable=False, unique=True),
        sa.Column("provider", sa.String, nullable=False),
        sa.Column("external_invoice_id", sa.String, nullable=False),
        sa.Column("document_url", sa.String, nullable=True),
        sa.Column("issued_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_invoices_charge_id", "invoices", ["charge_id"])

    # ------------------------------------------------------------------ #
    # vat_work_items                                                       #
    # ------------------------------------------------------------------ #
    op.create_table(
        "vat_work_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_to", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending_materials", "material_received", "data_entry_in_progress",
                "ready_for_review", "filed",
                name="vatworkitemstatus",
            ),
            nullable=False,
            server_default="material_received",
        ),
        sa.Column("pending_materials_note", sa.Text, nullable=True),
        sa.Column("total_output_vat", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_input_vat", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("net_vat", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("final_vat_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_overridden", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("override_justification", sa.Text, nullable=True),
        sa.Column(
            "filing_method",
            sa.Enum("manual", "online", name="filingmethod"),
            nullable=True,
        ),
        sa.Column("filed_at", sa.DateTime, nullable=True),
        sa.Column("filed_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("submission_reference", sa.String(100), nullable=True),
        sa.Column("is_amendment", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("amends_item_id", sa.Integer, sa.ForeignKey("vat_work_items.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("client_id", "period", name="uq_vat_work_item_client_period"),
    )
    op.create_index("ix_vat_work_items_client_id", "vat_work_items", ["client_id"])
    op.create_index("ix_vat_work_items_status", "vat_work_items", ["status"])

    # ------------------------------------------------------------------ #
    # vat_invoices                                                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "vat_invoices",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("work_item_id", sa.Integer, sa.ForeignKey("vat_work_items.id"), nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "invoice_type",
            sa.Enum("income", "expense", name="invoicetype"),
            nullable=False,
        ),
        sa.Column("invoice_number", sa.String, nullable=False),
        sa.Column("invoice_date", sa.DateTime, nullable=False),
        sa.Column("counterparty_name", sa.String, nullable=False),
        sa.Column("counterparty_id", sa.String, nullable=True),
        sa.Column("net_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("vat_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "expense_category",
            sa.Enum(
                "office", "travel", "professional_services", "equipment",
                "rent", "salary", "marketing", "vehicle", "entertainment",
                "gifts", "other",
                name="expensecategory",
            ),
            nullable=True,
        ),
        sa.Column(
            "rate_type",
            sa.Enum("standard", "exempt", "zero_rate", name="vatratetype"),
            nullable=False,
            server_default="standard",
        ),
        sa.Column("deduction_rate", sa.Numeric(5, 4), nullable=False, server_default="1.0000"),
        sa.Column(
            "document_type",
            sa.Enum(
                "tax_invoice", "transaction_invoice", "receipt",
                "consolidated", "self_invoice",
                name="vatdocumenttype",
            ),
            nullable=True,
        ),
        sa.Column("is_exceptional", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint(
            "work_item_id", "invoice_type", "invoice_number",
            name="uq_vat_invoice_item_type_number",
        ),
    )
    op.create_index("ix_vat_invoices_work_item_id", "vat_invoices", ["work_item_id"])
    op.create_index("ix_vat_invoices_work_item_type", "vat_invoices", ["work_item_id", "invoice_type"])

    # ------------------------------------------------------------------ #
    # vat_audit_logs                                                       #
    # ------------------------------------------------------------------ #
    op.create_table(
        "vat_audit_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("work_item_id", sa.Integer, sa.ForeignKey("vat_work_items.id"), nullable=False),
        sa.Column("performed_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("old_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("performed_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_vat_audit_logs_work_item_id", "vat_audit_logs", ["work_item_id"])


def downgrade() -> None:
    op.drop_table("vat_audit_logs")
    op.drop_index("ix_vat_invoices_work_item_type", table_name="vat_invoices")
    op.drop_index("ix_vat_invoices_work_item_id", table_name="vat_invoices")
    op.drop_table("vat_invoices")
    op.drop_index("ix_vat_work_items_status", table_name="vat_work_items")
    op.drop_index("ix_vat_work_items_client_id", table_name="vat_work_items")
    op.drop_table("vat_work_items")
    op.drop_table("invoices")
    op.drop_index("ix_notifications_binder_id", table_name="notifications")
    op.drop_index("ix_notifications_client_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("signature_audit_events")
    op.drop_table("signature_requests")
    op.drop_table("annual_report_status_history")
    op.drop_table("annual_report_schedules")
    op.drop_table("annual_report_annex_data")
    op.drop_table("annual_report_expense_lines")
    op.drop_table("annual_report_income_lines")
    op.drop_table("annual_report_details")
    op.drop_index("ix_permanent_documents_client_type_year", table_name="permanent_documents")
    op.drop_index("ix_permanent_documents_tax_year", table_name="permanent_documents")
    op.drop_index("ix_permanent_documents_client_id", table_name="permanent_documents")
    op.drop_table("permanent_documents")
    op.drop_table("correspondence_entries")
    op.drop_table("reminders")
    op.drop_table("advance_payments")
    op.drop_table("charges")
    op.drop_table("tax_deadlines")
    op.drop_table("binder_intakes")
    op.drop_table("binder_status_logs")
    op.drop_index("idx_active_binder_unique", table_name="binders")
    op.drop_index("idx_binder_received_at", table_name="binders")
    op.drop_index("idx_binder_status", table_name="binders")
    op.drop_index("ix_binders_annual_report_id", table_name="binders")
    op.drop_index("ix_binders_client_id", table_name="binders")
    op.drop_table("binders")
    op.drop_table("annual_reports")
    op.drop_table("authority_contacts")
    op.drop_table("client_tax_profiles")
    op.drop_index("ix_clients_id_number_active", table_name="clients")
    op.drop_table("clients")
    op.drop_table("user_audit_logs")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")