import os
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import event
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
from app.businesses.models.business import Business, BusinessStatus


@event.listens_for(Client, "after_insert")
def _create_default_business_for_client(mapper, connection, target):
    """Keep legacy tests working: every seeded client gets a matching business."""
    # Avoid forcing id=client.id, which can collide with already-created businesses
    # in suites that manually seed business rows between client inserts.
    connection.execute(
        Business.__table__.insert().values(
            client_id=target.id,
            business_name=target.full_name,
            status=BusinessStatus.ACTIVE,
            opened_at=date.today(),
        )
    )



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
    db = TestSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


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
    test_db.commit()
    test_db.refresh(client)
    return client
