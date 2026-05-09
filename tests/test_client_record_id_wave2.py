from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import (
    PersonLegalEntityLink,
    PersonLegalEntityRole,
)
from app.common.enums import IdNumberType, VatType
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
    client = LegalEntity(
        official_name="Wave 2 Client",
        id_number=id_number,
        id_number_type=IdNumberType.INDIVIDUAL,
        vat_reporting_frequency=VatType.MONTHLY,
    )
    db.add(client)
    db.flush()
    return client


def _make_client_record(db, legal_entity_id: int):
    record = ClientRecord(legal_entity_id=legal_entity_id)
    db.add(record)
    db.flush()
    return record


def _attach_owner_person(db, legal_entity_id: int, *, email: str | None = None):
    person = Person(
        full_name="Wave 2 Owner",
        id_number=f"P-{legal_entity_id}",
        id_number_type=IdNumberType.OTHER,
        email=email,
    )
    db.add(person)
    db.flush()
    db.add(
        PersonLegalEntityLink(
            person_id=person.id,
            legal_entity_id=legal_entity_id,
            role=PersonLegalEntityRole.OWNER,
        )
    )
    db.flush()
    return person


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

    record = db.get(ClientRecord, client_id)

    business = Business(
        legal_entity_id=record.legal_entity_id if record else None,
        business_name=f"Biz-{client_id}",
        status=BusinessStatus.ACTIVE,
        opened_at=date.today(),
    )
    db.add(business)
    db.flush()
    business.client_id = client_id
    return business


class TestO2Charge:
    def test_repo_list_by_client_record(self, db):
        from app.charge.models.charge import Charge, ChargeStatus
        from app.charge.repositories.charge_repository import ChargeRepository

        client = _make_client(db, "C204")
        record = _make_client_record(db, client.id)
        db.add(
            Charge(
                client_record_id=record.id,
                charge_type="other",
                status=ChargeStatus.DRAFT,
                amount=100,
            )
        )
        db.flush()

        items = ChargeRepository(db).list_charges_by_client_record(record.id)
        assert len(items) == 1
        assert items[0].client_record_id == record.id


class TestO3Notification:
    def test_repo_list_by_client_record(self, db):
        from app.notification.models.notification import (
            Notification,
            NotificationChannel,
            NotificationSeverity,
            NotificationStatus,
            NotificationTrigger,
        )
        from app.notification.repositories.notification_repository import (
            NotificationRepository,
        )

        client = _make_client(db, "C207")
        record = _make_client_record(db, client.id)
        db.add(
            Notification(
                client_record_id=record.id,
                trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
                channel=NotificationChannel.EMAIL,
                severity=NotificationSeverity.INFO,
                recipient="x@test.com",
                content_snapshot="body",
                status=NotificationStatus.PENDING,
            )
        )
        db.flush()

        items = NotificationRepository(db).list_by_client_record(record.id)
        assert len(items) == 1
        assert items[0].client_record_id == record.id

    def test_service_resolves_client_record_id_from_client_id(self, db, monkeypatch):
        from app.notification.services.notification_send_service import (
            NotificationSendService,
        )

        client = _make_client(db, "C208")
        record = _make_client_record(db, client.id)
        _attach_owner_person(db, client.id, email="client@test.com")
        db.flush()
        svc = NotificationSendService(db)
        monkeypatch.setattr(svc.email, "send", lambda *args, **kwargs: (True, None))

        svc.send_client_reminder(client.id, "hello")
        created = svc.notification_repo.list_by_client_record(record.id)[0]
        assert created.client_record_id == record.id


class TestO4Correspondence:
    def test_repo_list_by_client_record(self, db):
        from app.correspondence.models.correspondence import (
            Correspondence,
            CorrespondenceType,
        )
        from app.correspondence.repositories.correspondence_repository import (
            CorrespondenceRepository,
        )

        client = _make_client(db, "C210")
        record = _make_client_record(db, client.id)
        user = _make_user(db)
        db.add(
            Correspondence(
                client_record_id=record.id,
                correspondence_type=CorrespondenceType.EMAIL,
                subject="subject",
                occurred_at=datetime.utcnow(),
                created_by=user.id,
            )
        )
        db.flush()

        items, total = CorrespondenceRepository(db).list_by_client_record_paginated(
            record.id, page=1, page_size=20
        )
        assert total == 1
        assert items[0].client_record_id == record.id


class TestO5SignatureRequest:
    def test_repo_list_by_client_record(self, db):
        from app.signature_requests.models.signature_request import (
            SignatureRequest,
            SignatureRequestStatus,
            SignatureRequestType,
        )
        from app.signature_requests.repositories.signature_request_repository import (
            SignatureRequestRepository,
        )

        client = _make_client(db, "C213")
        record = _make_client_record(db, client.id)
        user = _make_user(db)
        db.add(
            SignatureRequest(
                client_record_id=record.id,
                created_by=user.id,
                request_type=SignatureRequestType.CUSTOM,
                title="Sign",
                signer_name="Signer",
                status=SignatureRequestStatus.DRAFT,
            )
        )
        db.flush()

        items = SignatureRequestRepository(db).list_by_client_record(record.id)
        assert len(items) == 1
        assert items[0].client_record_id == record.id


class TestO6AuthorityContact:
    def test_repo_list_by_client_record(self, db):
        from app.authority_contact.models.authority_contact import (
            AuthorityContact,
            ContactType,
        )
        from app.authority_contact.repositories.authority_contact_repository import (
            AuthorityContactRepository,
        )

        client = _make_client(db, "C216")
        record = _make_client_record(db, client.id)
        db.add(
            AuthorityContact(
                client_record_id=record.id,
                contact_type=ContactType.OTHER,
                name="Officer",
            )
        )
        db.flush()

        items = AuthorityContactRepository(db).list_by_client_record(record.id)
        assert len(items) == 1
        assert items[0].client_record_id == record.id


class TestO7BinderHandover:
    def test_repo_list_by_client_record(self, db):
        from app.binders.models.binder_handover import BinderHandover
        from app.binders.repositories.binder_handover_repository import (
            BinderHandoverRepository,
        )

        client = _make_client(db, "C219")
        record = _make_client_record(db, client.id)
        user = _make_user(db)
        db.add(
            BinderHandover(
                client_record_id=record.id,
                received_by_name="Receiver",
                handed_over_at=date.today(),
                until_period_year=2024,
                until_period_month=6,
                created_by=user.id,
            )
        )
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
        db.add(
            Binder(
                client_record_id=record.id,
                binder_number="20/1",
                status=BinderStatus.READY_FOR_PICKUP,
                created_by=user.id,
            )
        )
        db.flush()

        handover = BinderHandoverService(db).create_handover(
            client_record_id=record.id,
            binder_ids=[1],
            received_by_name="Receiver",
            handed_over_at=date.today(),
            until_period_year=2024,
            until_period_month=6,
            actor_id=user.id,
        )
        assert handover.client_record_id == record.id
