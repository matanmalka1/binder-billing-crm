from datetime import datetime, timezone
from itertools import count

from app.businesses.models.business import Business
from app.businesses.models.business_tax_profile import VatType
from app.clients.models import Client
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.vat_reports.models.vat_enums import ExpenseCategory, InvoiceType
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository


_client_seq = count(1)


def _user(test_db) -> User:
    user = User(
        full_name="VAT Repo User",
        email="vat.repo@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _business(db) -> Business:
    idx = next(_client_seq)
    client = Client(full_name=f"VAT Repo Client {idx}", id_number=f"VRI{idx:03d}")
    db.add(client)
    db.commit()
    db.refresh(client)
    return db.get(Business, client.id)


def test_list_by_work_item_orders_and_filters_by_type(test_db):
    user = _user(test_db)
    business = _business(test_db)
    work_item_repo = VatWorkItemRepository(test_db)
    invoice_repo = VatInvoiceRepository(test_db)

    item = work_item_repo.create(
        business_id=business.id, period="2026-05", period_type=VatType.MONTHLY, created_by=user.id
    )
    other_item = work_item_repo.create(
        business_id=business.id, period="2026-06", period_type=VatType.MONTHLY, created_by=user.id
    )

    expense = invoice_repo.create(
        work_item_id=item.id,
        created_by=user.id,
        invoice_type=InvoiceType.EXPENSE,
        invoice_number="EXP-001",
        invoice_date=datetime(2026, 5, 1),
        counterparty_name="Vendor",
        counterparty_id="EXP-CP",
        net_amount=500.0,
        vat_amount=85.0,
        expense_category=ExpenseCategory.OFFICE,
    )
    income = invoice_repo.create(
        work_item_id=item.id,
        created_by=user.id,
        invoice_type=InvoiceType.INCOME,
        invoice_number="INC-001",
        invoice_date=datetime(2026, 5, 3),
        counterparty_name="Customer",
        net_amount=1000.0,
        vat_amount=170.0,
    )
    invoice_repo.create(
        work_item_id=other_item.id,
        created_by=user.id,
        invoice_type=InvoiceType.INCOME,
        invoice_number="INC-OTHER",
        invoice_date=datetime(2026, 5, 2),
        counterparty_name="Other",
        net_amount=200.0,
        vat_amount=34.0,
    )

    all_for_item = invoice_repo.list_by_work_item(item.id)
    assert [inv.id for inv in all_for_item] == [expense.id, income.id]

    income_only = invoice_repo.list_by_work_item(item.id, invoice_type=InvoiceType.INCOME)
    assert [inv.id for inv in income_only] == [income.id]



def test_sum_income_net_by_business_year_filters_by_business_year_and_income_only(test_db):
    user = _user(test_db)
    business = _business(test_db)
    other_business = _business(test_db)

    work_item_repo = VatWorkItemRepository(test_db)
    invoice_repo = VatInvoiceRepository(test_db)

    target_item = work_item_repo.create(
        business_id=business.id, period="2026-01", period_type=VatType.MONTHLY, created_by=user.id
    )
    previous_year_item = work_item_repo.create(
        business_id=business.id, period="2025-12", period_type=VatType.MONTHLY, created_by=user.id
    )
    other_business_item = work_item_repo.create(
        business_id=other_business.id, period="2026-02", period_type=VatType.MONTHLY, created_by=user.id
    )

    invoice_repo.create(
        work_item_id=target_item.id,
        created_by=user.id,
        invoice_type=InvoiceType.INCOME,
        invoice_number="INC-YEAR-1",
        invoice_date=datetime(2026, 1, 5),
        counterparty_name="Customer A",
        net_amount=1000.0,
        vat_amount=170.0,
    )
    invoice_repo.create(
        work_item_id=target_item.id,
        created_by=user.id,
        invoice_type=InvoiceType.EXPENSE,
        invoice_number="EXP-YEAR-IGNORED",
        invoice_date=datetime(2026, 1, 8),
        counterparty_name="Vendor A",
        net_amount=400.0,
        vat_amount=68.0,
        expense_category=ExpenseCategory.OFFICE,
    )
    invoice_repo.create(
        work_item_id=previous_year_item.id,
        created_by=user.id,
        invoice_type=InvoiceType.INCOME,
        invoice_number="INC-OTHER-YEAR",
        invoice_date=datetime(2025, 12, 25),
        counterparty_name="Customer B",
        net_amount=300.0,
        vat_amount=51.0,
    )
    invoice_repo.create(
        work_item_id=other_business_item.id,
        created_by=user.id,
        invoice_type=InvoiceType.INCOME,
        invoice_number="INC-OTHER-BUSINESS",
        invoice_date=datetime(2026, 2, 3),
        counterparty_name="Customer C",
        net_amount=700.0,
        vat_amount=119.0,
    )

    assert invoice_repo.sum_income_net_by_business_year(business.id, 2026) == 1000.0
    assert invoice_repo.sum_income_net_by_business_year(business.id, 2024) == 0.0


def test_sum_income_net_excludes_soft_deleted_work_items(test_db):
    user = _user(test_db)
    business = _business(test_db)

    work_item_repo = VatWorkItemRepository(test_db)
    invoice_repo = VatInvoiceRepository(test_db)

    active_item = work_item_repo.create(
        business_id=business.id, period="2026-03", period_type=VatType.MONTHLY, created_by=user.id
    )
    deleted_item = work_item_repo.create(
        business_id=business.id, period="2026-04", period_type=VatType.MONTHLY, created_by=user.id
    )

    invoice_repo.create(
        work_item_id=active_item.id,
        created_by=user.id,
        invoice_type=InvoiceType.INCOME,
        invoice_number="INC-ACTIVE",
        invoice_date=datetime(2026, 3, 1),
        counterparty_name="Customer A",
        net_amount=5000.0,
        vat_amount=850.0,
    )
    invoice_repo.create(
        work_item_id=deleted_item.id,
        created_by=user.id,
        invoice_type=InvoiceType.INCOME,
        invoice_number="INC-DELETED",
        invoice_date=datetime(2026, 4, 1),
        counterparty_name="Customer B",
        net_amount=9000.0,
        vat_amount=1530.0,
    )

    # Soft-delete the second work item directly
    deleted_item.deleted_at = datetime.now(timezone.utc)
    test_db.commit()

    # Only the active item's invoices should count toward the ceiling
    assert invoice_repo.sum_income_net_by_business_year(business.id, 2026) == 5000.0


def test_update_and_delete_return_falsy_for_missing_invoice(test_db):
    repo = VatInvoiceRepository(test_db)

    assert repo.update(999999, invoice_number="NOPE") is None
    assert repo.delete(999999) is False
