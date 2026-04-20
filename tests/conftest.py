import os
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.main as main_module
import app.core.background_jobs as background_jobs_module

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-secret")

from app.database import Base, get_db
import app.notes.models.entity_note  # noqa: F401
from app.signature_requests.models.signature_request import SignatureAuditEvent, SignatureRequest
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.clients.models.client import Client
from app.clients.models.legal_entity import LegalEntity  # noqa: F401
from app.clients.models.client_record import ClientRecord  # noqa: F401
from app.clients.models.person import Person  # noqa: F401
from app.clients.models.person_legal_entity_link import PersonLegalEntityLink  # noqa: F401
from app.businesses.models.business import Business, BusinessStatus


def _ensure_client_identity_graph(session, client: Client) -> None:
    if any(isinstance(obj, ClientRecord) and obj.id == client.id for obj in session.new):
        return

    legal_entity = (
        session.query(LegalEntity)
        .filter(
            LegalEntity.id_number == client.id_number,
            LegalEntity.id_number_type == client.id_number_type,
        )
        .first()
    )
    if not legal_entity:
        pending_legal_entities = [
            obj for obj in session.new
            if isinstance(obj, LegalEntity)
            and obj.id_number == client.id_number
            and obj.id_number_type == client.id_number_type
        ]
        if pending_legal_entities:
            legal_entity = pending_legal_entities[0]
        else:
            legal_entity = LegalEntity(
                id_number=client.id_number,
                id_number_type=client.id_number_type,
                entity_type=client.entity_type,
                vat_reporting_frequency=client.vat_reporting_frequency,
                vat_exempt_ceiling=client.vat_exempt_ceiling,
                advance_rate=client.advance_rate,
                advance_rate_updated_at=client.advance_rate_updated_at,
            )
            session.add(legal_entity)
            session.flush()

    if legal_entity.id is None:
        session.flush()

    record = (
        session.query(ClientRecord)
        .filter(ClientRecord.id == client.id, ClientRecord.deleted_at.is_(None))
        .first()
    )
    if record:
        return

    session.add(
        ClientRecord(
            id=client.id,
            legal_entity_id=legal_entity.id,
            office_client_number=client.office_client_number,
            accountant_name=client.accountant_name,
            status=client.status,
            created_by=client.created_by,
        )
    )
    session.flush()


@pytest.fixture(scope="function")
def test_db():
    """Create test database with proper SQLite threading config."""
    # Use StaticPool and check_same_thread=False for SQLite in tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    @event.listens_for(TestSessionLocal.class_, "before_commit")
    def _autocreate_client_identity_graph(session):
        if session.info.get("_auto_client_graph_running"):
            return
        session.info["_auto_client_graph_running"] = True
        try:
            clients = list(session.query(Client).filter(Client.deleted_at.is_(None)).all())
            for client in clients:
                _ensure_client_identity_graph(session, client)
        finally:
            session.info.pop("_auto_client_graph_running", None)

    db = TestSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def create_client_with_business(test_db):
    """Create a test client with an explicit default business."""
    def _create(
        *,
        full_name: str = "Seeded Test Client",
        id_number: str = "SEEDED-001",
        business_name: str | None = None,
        opened_at: date | None = None,
        **client_fields,
    ):
        client = Client(
            full_name=full_name,
            id_number=id_number,
            **client_fields,
        )
        test_db.add(client)
        test_db.flush()
        _ensure_client_identity_graph(test_db, client)
        business = Business(
            client_id=client.id,
            business_name=business_name or full_name,
            status=BusinessStatus.ACTIVE,
            opened_at=opened_at or date.today(),
        )
        test_db.add(business)
        test_db.commit()
        test_db.refresh(client)
        test_db.refresh(business)
        return client, business

    return _create


@pytest.fixture(scope="function")
def client(test_db):
    """FastAPI test client with test database."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    main_module.app.dependency_overrides[get_db] = override_get_db
    original_expire = background_jobs_module.expire_overdue_requests
    background_jobs_module.expire_overdue_requests = lambda repo: 0

    with TestClient(main_module.app) as test_client:
        yield test_client

    main_module.app.dependency_overrides.clear()
    background_jobs_module.expire_overdue_requests = original_expire


@pytest.fixture(scope="function")
def test_user(test_db):
    """Create test user."""
    user = User(
        full_name="Test User",
        email="test@example.com",
        password_hash=AuthService.hash_password("password123"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_token(test_user):
    """Generate auth token for test user."""
    return AuthService.generate_token(test_user)


@pytest.fixture(scope="function")
def secretary_user(test_db):
    """Create secretary user."""
    user = User(
        full_name="Test Secretary",
        email="secretary@example.com",
        password_hash=AuthService.hash_password("password123"),
        role=UserRole.SECRETARY,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def secretary_token(secretary_user):
    """Generate auth token for secretary user."""
    return AuthService.generate_token(secretary_user)


@pytest.fixture(scope="function")
def advisor_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="function")
def secretary_headers(secretary_token):
    return {"Authorization": f"Bearer {secretary_token}"}


@pytest.fixture(scope="function")
def vat_client(test_db):
    """A client fixture for VAT work item tests."""
    client = Client(
        full_name="VAT Test Client",
        id_number="123456789",
    )
    test_db.add(client)
    test_db.flush()
    _ensure_client_identity_graph(test_db, client)
    test_db.add(
        Business(
            client_id=client.id,
            business_name=client.full_name,
            status=BusinessStatus.ACTIVE,
            opened_at=date.today(),
        )
    )
    test_db.commit()
    test_db.refresh(client)
    return client
