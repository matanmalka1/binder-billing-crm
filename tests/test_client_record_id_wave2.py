from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _make_client(db, id_number: str = "C201"):
    from app.common.enums import VatType

    client = Client(
        full_name="Wave 2 Client",
        id_number=id_number,
        vat_reporting_frequency=VatType.MONTHLY,
    )
    db.add(client)
    db.flush()
    return client


def _make_client_record(db, client_id: int):
    from app.clients.models.legal_entity import LegalEntity
    from app.common.enums import IdNumberType

    legal = LegalEntity(id_number=f"LE-{client_id}", id_number_type=IdNumberType.INDIVIDUAL)
    db.add(legal)
    db.flush()
    record = ClientRecord(id=client_id, legal_entity_id=legal.id)
    db.add(record)
    db.flush()
    return record


def _make_user(db):
    user = User(
        full_name="Tester",
        email=f"t{datetime.now().timestamp()}@t.com",
        password_hash=AuthService.hash_password("x"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _make_business(db, client_id: int):
    from app.businesses.models.business import Business, BusinessStatus

    business = Business(
        client_id=client_id,
        business_name=f"Biz-{client_id}",
        status=BusinessStatus.ACTIVE,
        opened_at=date.today(),
    )
    db.add(business)
    db.flush()
    return business


class TestO1Reminder:
    def test_repo_list_by_client_record(self, db):
        from app.reminders.models.reminder import Reminder, ReminderStatus, ReminderType
        from app.reminders.repositories.reminder_repository import ReminderRepository

        client = _make_client(db)
        record = _make_client_record(db, client.id)
        db.add(Reminder(
            client_id=client.id,
            client_record_id=record.id,
            reminder_type=ReminderType.CUSTOM,
            status=ReminderStatus.PENDING,
            target_date=date(2024, 1, 20),
            days_before=2,
            send_on=date(2024, 1, 18),
            message="test",
        ))
        db.flush()

        items = ReminderRepository(db).list_by_client_record(record.id)
        assert len(items) == 1
        assert items[0].client_record_id == record.id

    def test_service_resolves_client_record_id_from_client_id(self, db):
        from app.reminders.services.factory import create_tax_deadline_reminder
        from app.reminders.repositories.reminder_repository import ReminderRepository
        from app.clients.repositories.client_repository import ClientRepository
        from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
        from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline

        client = _make_client(db, "C202")
        record = _make_client_record(db, client.id)
        deadline = TaxDeadline(client_id=client.id, deadline_type=DeadlineType.VAT, due_date=date(2024, 2, 15))
        db.add(deadline)
        db.flush()

        reminder = create_tax_deadline_reminder(
            ReminderRepository(db),
            ClientRepository(db),
            TaxDeadlineRepository(db),
            client_id=client.id,
            tax_deadline_id=deadline.id,
            target_date=date(2024, 2, 15),
            days_before=3,
        )
        assert reminder.client_record_id == record.id

    def test_fallback_when_no_client_record(self, db):
        from app.reminders.services.factory import create_tax_deadline_reminder
        from app.reminders.repositories.reminder_repository import ReminderRepository
        from app.clients.repositories.client_repository import ClientRepository
        from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
        from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline

        client = _make_client(db, "C203")
        deadline = TaxDeadline(client_id=client.id, deadline_type=DeadlineType.VAT, due_date=date(2024, 3, 15))
        db.add(deadline)
        db.flush()

        reminder = create_tax_deadline_reminder(
            ReminderRepository(db),
            ClientRepository(db),
            TaxDeadlineRepository(db),
            client_id=client.id,
            tax_deadline_id=deadline.id,
            target_date=date(2024, 3, 15),
            days_before=3,
        )
        assert reminder.client_record_id is None


class TestO2Charge:
    def test_repo_list_by_client_record(self, db):
        from app.charge.models.charge import Charge, ChargeStatus
        from app.charge.repositories.charge_repository import ChargeRepository

        client = _make_client(db, "C204")
        record = _make_client_record(db, client.id)
        db.add(Charge(
            client_id=client.id,
            client_record_id=record.id,
            charge_type="other",
            status=ChargeStatus.DRAFT,
            amount=100,
        ))
        db.flush()

        items = ChargeRepository(db).list_charges_by_client_record(record.id)
        assert len(items) == 1
        assert items[0].client_record_id == record.id

    def test_service_resolves_client_record_id_from_client_id(self, db):
        from app.charge.services.billing_service import BillingService

        client = _make_client(db, "C205")
        record = _make_client_record(db, client.id)

        charge = BillingService(db).create_charge(client_id=client.id, amount=120, charge_type="other")
        assert charge.client_record_id == record.id

    def test_fallback_when_no_client_record(self, db):
        from app.charge.services.billing_service import BillingService

        client = _make_client(db, "C206")
        charge = BillingService(db).create_charge(client_id=client.id, amount=120, charge_type="other")
        assert charge.client_record_id is None


class TestO3Notification:
    def test_repo_list_by_client_record(self, db):
        from app.notification.models.notification import (
            Notification, NotificationChannel, NotificationSeverity, NotificationStatus, NotificationTrigger,
        )
        from app.notification.repositories.notification_repository import NotificationRepository

        client = _make_client(db, "C207")
        record = _make_client_record(db, client.id)
        db.add(Notification(
            client_id=client.id,
            client_record_id=record.id,
            trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
            channel=NotificationChannel.EMAIL,
            severity=NotificationSeverity.INFO,
            recipient="x@test.com",
            content_snapshot="body",
            status=NotificationStatus.PENDING,
        ))
        db.flush()

        items = NotificationRepository(db).list_by_client_record(record.id)
        assert len(items) == 1
        assert items[0].client_record_id == record.id

    def test_service_resolves_client_record_id_from_client_id(self, db, monkeypatch):
        from app.notification.services.notification_send_service import NotificationSendService

        client = _make_client(db, "C208")
        client.email = "client@test.com"
        record = _make_client_record(db, client.id)
        db.flush()
        svc = NotificationSendService(db)
        monkeypatch.setattr(svc.email, "send", lambda *args, **kwargs: (True, None))

        svc.send_client_reminder(client.id, "hello")
        created = svc.notification_repo.list_by_client_record(record.id)[0]
        assert created.client_record_id == record.id

    def test_fallback_when_no_client_record(self, db, monkeypatch):
        from app.notification.services.notification_send_service import NotificationSendService

        client = _make_client(db, "C209")
        client.email = "client2@test.com"
        db.flush()
        svc = NotificationSendService(db)
        monkeypatch.setattr(svc.email, "send", lambda *args, **kwargs: (True, None))

        svc.send_client_reminder(client.id, "hello")
        created = svc.notification_repo.list_by_client(client.id)[0]
        assert created.client_record_id is None


class TestO4Correspondence:
    def test_repo_list_by_client_record(self, db):
        from app.correspondence.models.correspondence import Correspondence, CorrespondenceType
        from app.correspondence.repositories.correspondence_repository import CorrespondenceRepository

        client = _make_client(db, "C210")
        record = _make_client_record(db, client.id)
        user = _make_user(db)
        db.add(Correspondence(
            client_id=client.id,
            client_record_id=record.id,
            correspondence_type=CorrespondenceType.EMAIL,
            subject="subject",
            occurred_at=datetime.utcnow(),
            created_by=user.id,
        ))
        db.flush()

        items, total = CorrespondenceRepository(db).list_by_client_record_paginated(record.id, page=1, page_size=20)
        assert total == 1
        assert items[0].client_record_id == record.id

    def test_service_resolves_client_record_id_from_client_id(self, db):
        from app.correspondence.services.correspondence_service import CorrespondenceService
        from app.correspondence.models.correspondence import CorrespondenceType

        client = _make_client(db, "C211")
        record = _make_client_record(db, client.id)
        user = _make_user(db)
        entry = CorrespondenceService(db).add_entry(
            client_id=client.id,
            correspondence_type=CorrespondenceType.EMAIL,
            subject="hello",
            occurred_at=datetime.utcnow(),
            created_by=user.id,
        )
        assert entry.client_record_id == record.id

    def test_fallback_when_no_client_record(self, db):
        from app.correspondence.services.correspondence_service import CorrespondenceService
        from app.correspondence.models.correspondence import CorrespondenceType

        client = _make_client(db, "C212")
        user = _make_user(db)
        entry = CorrespondenceService(db).add_entry(
            client_id=client.id,
            correspondence_type=CorrespondenceType.EMAIL,
            subject="hello",
            occurred_at=datetime.utcnow(),
            created_by=user.id,
        )
        assert entry.client_record_id is None


class TestO5SignatureRequest:
    def test_repo_list_by_client_record(self, db):
        from app.signature_requests.models.signature_request import (
            SignatureRequest, SignatureRequestStatus, SignatureRequestType,
        )
        from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository

        client = _make_client(db, "C213")
        record = _make_client_record(db, client.id)
        user = _make_user(db)
        db.add(SignatureRequest(
            client_id=client.id,
            client_record_id=record.id,
            created_by=user.id,
            request_type=SignatureRequestType.CUSTOM,
            title="Sign",
            signer_name="Signer",
            status=SignatureRequestStatus.DRAFT,
        ))
        db.flush()

        items = SignatureRequestRepository(db).list_by_client_record(record.id)
        assert len(items) == 1
        assert items[0].client_record_id == record.id

    def test_service_resolves_client_record_id_from_client_id(self, db):
        from app.signature_requests.services.signature_request_service import SignatureRequestService

        client = _make_client(db, "C214")
        record = _make_client_record(db, client.id)
        user = _make_user(db)
        req = SignatureRequestService(db).create_request(
            client_id=client.id,
            created_by=user.id,
            created_by_name=user.full_name,
            request_type="custom",
            title="Sign",
            signer_name="Signer",
        )
        assert req.client_record_id == record.id

    def test_fallback_when_no_client_record(self, db):
        from app.signature_requests.services.signature_request_service import SignatureRequestService

        client = _make_client(db, "C215")
        user = _make_user(db)
        req = SignatureRequestService(db).create_request(
            client_id=client.id,
            created_by=user.id,
            created_by_name=user.full_name,
            request_type="custom",
            title="Sign",
            signer_name="Signer",
        )
        assert req.client_record_id is None


class TestO6AuthorityContact:
    def test_repo_list_by_client_record(self, db):
        from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
        from app.authority_contact.repositories.authority_contact_repository import AuthorityContactRepository

        client = _make_client(db, "C216")
        record = _make_client_record(db, client.id)
        db.add(AuthorityContact(
            client_id=client.id,
            client_record_id=record.id,
            contact_type=ContactType.OTHER,
            name="Officer",
        ))
        db.flush()

        items = AuthorityContactRepository(db).list_by_client_record(record.id)
        assert len(items) == 1
        assert items[0].client_record_id == record.id

    def test_service_resolves_client_record_id_from_client_id(self, db):
        from app.authority_contact.services.authority_contact_service import AuthorityContactService

        client = _make_client(db, "C217")
        record = _make_client_record(db, client.id)
        contact = AuthorityContactService(db).add_contact(
            client_id=client.id,
            contact_type="other",
            name="Officer",
        )
        assert contact.client_record_id == record.id

    def test_fallback_when_no_client_record(self, db):
        from app.authority_contact.services.authority_contact_service import AuthorityContactService

        client = _make_client(db, "C218")
        contact = AuthorityContactService(db).add_contact(
            client_id=client.id,
            contact_type="other",
            name="Officer",
        )
        assert contact.client_record_id is None


class TestO7BinderHandover:
    def test_repo_list_by_client_record(self, db):
        from app.binders.models.binder_handover import BinderHandover
        from app.binders.repositories.binder_handover_repository import BinderHandoverRepository

        client = _make_client(db, "C219")
        record = _make_client_record(db, client.id)
        user = _make_user(db)
        db.add(BinderHandover(
            client_id=client.id,
            client_record_id=record.id,
            received_by_name="Receiver",
            handed_over_at=date.today(),
            until_period_year=2024,
            until_period_month=6,
            created_by=user.id,
        ))
        db.flush()

        items = BinderHandoverRepository(db).list_by_client_record(record.id)
        assert len(items) == 1
        assert items[0].client_record_id == record.id

    def test_service_resolves_client_record_id_from_client_id(self, db):
        from app.binders.models.binder import Binder, BinderStatus
        from app.binders.services.binder_handover_service import BinderHandoverService

        client = _make_client(db, "C220")
        record = _make_client_record(db, client.id)
        user = _make_user(db)
        db.add(Binder(
            client_id=client.id,
            client_record_id=record.id,
            binder_number="20/1",
            status=BinderStatus.READY_FOR_PICKUP,
            created_by=user.id,
        ))
        db.flush()

        handover = BinderHandoverService(db).create_handover(
            client_id=client.id,
            binder_ids=[1],
            received_by_name="Receiver",
            handed_over_at=date.today(),
            until_period_year=2024,
            until_period_month=6,
            actor_id=user.id,
        )
        assert handover.client_record_id == record.id

    def test_fallback_when_no_client_record(self, db):
        from app.binders.models.binder import Binder, BinderStatus
        from app.binders.services.binder_handover_service import BinderHandoverService

        client = _make_client(db, "C221")
        user = _make_user(db)
        db.add(Binder(
            client_id=client.id,
            binder_number="21/1",
            status=BinderStatus.READY_FOR_PICKUP,
            created_by=user.id,
        ))
        db.flush()

        handover = BinderHandoverService(db).create_handover(
            client_id=client.id,
            binder_ids=[1],
            received_by_name="Receiver",
            handed_over_at=date.today(),
            until_period_year=2024,
            until_period_month=6,
            actor_id=user.id,
        )
        assert handover.client_record_id is None
