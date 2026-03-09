from datetime import date, datetime
from itertools import count

from app.clients.models import Client, ClientType
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


def _client(db) -> Client:
    idx = next(_client_seq)
    c = Client(
        full_name=f"VAT Repo Client {idx}",
        id_number=f"VRI{idx:03d}",
        client_type=ClientType.OSEK_MURSHE,
        opened_at=date.today(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_list_by_work_item_orders_and_filters_by_type(test_db):
    user = _user(test_db)
    client = _client(test_db)
    work_item_repo = VatWorkItemRepository(test_db)
    invoice_repo = VatInvoiceRepository(test_db)

    item = work_item_repo.create(client_id=client.id, period="2026-05", created_by=user.id)
    other_item = work_item_repo.create(client_id=client.id, period="2026-06", created_by=user.id)

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

