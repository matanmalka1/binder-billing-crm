"""introduce businesses table and migrate all client_id references

Revision ID: e1f2a3b4c5d6
Revises: d1e2f3a4b5c6
Create Date: 2026-03-19 15:00:00.000000

Run:
- Upgrade:   APP_ENV=<env> ENV_FILE=<env_file> python3 -m alembic upgrade e1f2a3b4c5d6
- Downgrade: NOT SUPPORTED — restore from backup if needed.

Notes:
- יוצר טבלת businesses — כל לקוח קיים הופך לעסק אחד אוטומטית.
- יוצר טבלת business_tax_profiles — מחליפה את client_tax_profiles.
- יוצר טבלת authority_contact_links — קשר many-to-many בין איש קשר ללקוח/עסק.
- מוסיף business_id לכל הטבלאות העסקיות ומעביר ערכים מ-client_id.
- מוסיף scope ל-permanent_documents (client / business).
- מוסיף deleted_at/deleted_by לטבלאות שחסרות אותן.
- מעדכן unique constraints ל-business_id במקום client_id.
- PostgreSQL: מסיר שדות עסקיים מ-clients (client_type, status, וכו').
- SQLite: לא מסיר עמודות (לא נתמך) — שדות ישנים נשארים אך לא בשימוש.
- downgrade אינו נתמך — מורכבות גבוהה מדי, השתמש ב-backup.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _column_exists(conn, table: str, column: str) -> bool:
    inspector = inspect(conn)
    return any(c["name"] == column for c in inspector.get_columns(table))


def _index_exists(conn, table: str, index: str) -> bool:
    inspector = inspect(conn)
    return any(i["name"] == index for i in inspector.get_indexes(table))


def _constraint_exists(conn, table: str, constraint: str) -> bool:
    inspector = inspect(conn)
    try:
        return any(
            c["name"] == constraint
            for c in inspector.get_unique_constraints(table)
        )
    except Exception:
        return False


def upgrade() -> None:
    conn = op.get_bind()

    # ─── שלב 1: יצירת טבלת businesses ────────────────────────────────────────
    if not inspect(conn).has_table("businesses"):
     op.create_table(
        "businesses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("business_name", sa.String(), nullable=True),
        sa.Column(
            "business_type",
            sa.Enum(
                "osek_patur", "osek_murshe", "company", "employee",
                name="businesstype",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("active", "frozen", "closed", name="businessstatus"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("primary_binder_number", sa.String(), nullable=True, unique=True),
        sa.Column("opened_at", sa.Date(), nullable=False),
        sa.Column("closed_at", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("restored_at", sa.DateTime(), nullable=True),
        sa.Column("restored_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    if not _index_exists(conn, "businesses", "ix_business_client_id"):
        op.create_index("ix_business_client_id", "businesses", ["client_id"])
    if not _index_exists(conn, "businesses", "ix_business_status"):
        op.create_index("ix_business_status", "businesses", ["status"])

    # ─── שלב 2: העתקת נתונים מ-clients ל-businesses ──────────────────────────
    # כל לקוח קיים (כולל מחוקים) הופך לעסק אחד
    conn.execute(text("""
        INSERT INTO businesses (
            client_id, business_name, business_type, status,
            primary_binder_number, opened_at, closed_at,
            notes, created_by, created_at,
            deleted_at, deleted_by, restored_at, restored_by
        )
        SELECT
            id,
            NULL,
            client_type,
            status,
            primary_binder_number,
            opened_at,
            closed_at,
            notes,
            created_by,
            CURRENT_TIMESTAMP,
            deleted_at,
            deleted_by,
            restored_at,
            restored_by
        FROM clients
    """))

    # ─── שלב 3: יצירת טבלת business_tax_profiles ──────────────────────────────
    if not inspect(conn).has_table("business_tax_profiles"):
     op.create_table(
        "business_tax_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "business_id",
            sa.Integer(),
            sa.ForeignKey("businesses.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "vat_type",
            sa.Enum("monthly", "bimonthly", "exempt", name="vattype"),
            nullable=True,
        ),
        sa.Column("business_type", sa.String(), nullable=True),
        sa.Column("tax_year_start", sa.Integer(), nullable=True),
        sa.Column("accountant_name", sa.String(), nullable=True),
        sa.Column("advance_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_business_tax_profiles_business_id",
        "business_tax_profiles",
        ["business_id"],
        unique=True,
    )

    # העתקת client_tax_profiles ל-business_tax_profiles
    conn.execute(text("""
        INSERT INTO business_tax_profiles (
            business_id, vat_type, business_type,
            tax_year_start, accountant_name, advance_rate,
            created_at, updated_at
        )
        SELECT
            b.id,
            ctp.vat_type,
            ctp.business_type,
            ctp.tax_year_start,
            ctp.accountant_name,
            ctp.advance_rate,
            ctp.created_at,
            ctp.updated_at
        FROM client_tax_profiles ctp
        JOIN businesses b ON b.client_id = ctp.client_id
    """))

    # ─── שלב 4: יצירת טבלת authority_contact_links ────────────────────────────
    if not inspect(conn).has_table("authority_contact_links"):
     op.create_table(
        "authority_contact_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey("authority_contacts.id"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id"),
            nullable=False,
        ),
        sa.Column(
            "business_id",
            sa.Integer(),
            sa.ForeignKey("businesses.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_authority_contact_link_unique",
        "authority_contact_links",
        ["contact_id", "client_id", "business_id"],
        unique=True,
    )

    # העתקת קשרים קיימים מ-authority_contacts (היו ברמת לקוח)
    conn.execute(text("""
        INSERT INTO authority_contact_links (contact_id, client_id, business_id, created_at)
        SELECT ac.id, ac.client_id, NULL, CURRENT_TIMESTAMP
        FROM authority_contacts ac
        WHERE ac.deleted_at IS NULL
          AND ac.client_id IS NOT NULL
    """))

    # ─── שלב 5: הוספת business_id לכל הטבלאות העסקיות ───────────────────────
    tables_to_migrate = [
        "annual_reports",
        "vat_work_items",
        "charges",
        "advance_payments",
        "tax_deadlines",
        "binders",
        "correspondence_entries",
        "signature_requests",
        "notifications",
        "reminders",
        "permanent_documents",
    ]

    for table in tables_to_migrate:
        if not _column_exists(conn, table, "business_id"):
            with op.batch_alter_table(table) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "business_id",
                        sa.Integer(),
                        nullable=True,
                    )
                )

    # מילוי business_id לפי client_id
    for table in tables_to_migrate:
        conn.execute(text(f"""
            UPDATE {table}
            SET business_id = (
                SELECT b.id
                FROM businesses b
                WHERE b.client_id = {table}.client_id
                ORDER BY b.id
                LIMIT 1
            )
            WHERE business_id IS NULL
        """))

    # ─── שלב 6: הפיכת business_id ל-NOT NULL (מלבד permanent_documents) ──────
    # SQLite לא תומך ב-ALTER COLUMN — מדלגים
    if is_postgresql():
        for table in tables_to_migrate:
            if table != "permanent_documents":
                op.alter_column(table, "business_id", nullable=False)

    # ─── שלב 7: הוספת scope ל-permanent_documents ─────────────────────────────
    if not _column_exists(conn, "permanent_documents", "scope"):
        op.add_column(
            "permanent_documents",
            sa.Column(
                "scope",
                sa.Enum("client", "business", name="documentscope"),
                nullable=False,
                server_default="business",
            ),
        )

    # מסמכי זהות — scope=client, business_id=NULL
    conn.execute(text("""
        UPDATE permanent_documents
        SET scope = 'client', business_id = NULL
        WHERE document_type IN ('id_copy', 'power_of_attorney', 'engagement_agreement')
    """))

    # ─── שלב 8: עדכון Unique Constraints (PostgreSQL בלבד) ──────────────────
    if is_postgresql():
        if _index_exists(conn, "annual_reports", "idx_annual_report_client_year"):
            op.drop_index("idx_annual_report_client_year", table_name="annual_reports")

        if not _index_exists(conn, "annual_reports", "idx_annual_report_business_year"):
            op.create_index(
                "idx_annual_report_business_year",
                "annual_reports",
                ["business_id", "tax_year"],
                unique=True,
                postgresql_where=sa.text("deleted_at IS NULL"),
            )

        if _constraint_exists(conn, "vat_work_items", "uq_vat_work_item_client_period"):
            op.drop_constraint(
                "uq_vat_work_item_client_period",
                "vat_work_items",
                type_="unique",
            )
        if not _constraint_exists(conn, "vat_work_items", "uq_vat_work_item_business_period"):
            op.create_unique_constraint(
                "uq_vat_work_item_business_period",
                "vat_work_items",
                ["business_id", "period"],
            )

        if _constraint_exists(conn, "advance_payments", "uq_advance_payment_client_year_month"):
            op.drop_constraint(
                "uq_advance_payment_client_year_month",
                "advance_payments",
                type_="unique",
            )
        if not _constraint_exists(conn, "advance_payments", "uq_advance_payment_business_year_month"):
            op.create_unique_constraint(
                "uq_advance_payment_business_year_month",
                "advance_payments",
                ["business_id", "year", "month"],
            )

    # ─── שלב 9: הוספת deleted_at/deleted_by לטבלאות חסרות ───────────────────
    tables_missing_soft_delete = [
        "vat_work_items",
        "advance_payments",
        "tax_deadlines",
        "signature_requests",
        "reminders",
    ]

    for table in tables_missing_soft_delete:
        if not _column_exists(conn, table, "deleted_at"):
            op.add_column(table, sa.Column("deleted_at", sa.DateTime(), nullable=True))
        if not _column_exists(conn, table, "deleted_by"):
            with op.batch_alter_table(table) as batch_op:
                batch_op.add_column(
                    sa.Column("deleted_by", sa.Integer(), nullable=True)
                )

    # ─── שלב 10: הסרת שדות עסקיים מ-clients (PostgreSQL בלבד) ───────────────
    # SQLite לא תומך ב-DROP COLUMN — שדות נשארים אך אינם בשימוש
    if is_postgresql():
        for col in [
            "client_type", "status", "primary_binder_number",
            "opened_at", "closed_at", "notes",
        ]:
            if _column_exists(conn, "clients", col):
                op.drop_column("clients", col)

        # הסרת enum types ישנים שהועברו ל-businesses
        for type_name in ["clienttype", "clientstatus"]:
            conn.execute(sa.text(f"DROP TYPE IF EXISTS {type_name}"))


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade of migration e1f2a3b4c5d6 is not supported. "
        "This migration restructures core tables. Restore from backup if needed."
    )