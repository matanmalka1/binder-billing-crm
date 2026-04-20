from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord


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


def _make_client(db, id_number="C301"):
    from app.common.enums import VatType

    client = Client(full_name="Doc Client", id_number=id_number, vat_reporting_frequency=VatType.MONTHLY)
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


class TestPermanentDocumentClientRecord:
    def test_scope_client_visible_via_client_record(self, db):
        from app.permanent_documents.models.permanent_document import DocumentScope, DocumentStatus
        from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository

        client = _make_client(db)
        record = _make_client_record(db, client.id)
        repo = PermanentDocumentRepository(db)
        repo.create(
            client_record_id=record.id,
            business_id=None,
            scope=DocumentScope.CLIENT,
            document_type="id_copy",
            storage_key="a",
            uploaded_by=1,
            status=DocumentStatus.APPROVED,
        )
        docs = repo.list_by_client_record(record.id, scope=DocumentScope.CLIENT)
        assert len(docs) == 1
        assert docs[0].client_record_id == record.id

    def test_scope_business_visible_via_client_record(self, db):
        from app.permanent_documents.models.permanent_document import DocumentScope, DocumentStatus
        from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository
        from app.businesses.models.business import Business, BusinessStatus

        client = _make_client(db, "C302")
        record = _make_client_record(db, client.id)
        business = Business(client_id=client.id, business_name="Biz", status=BusinessStatus.ACTIVE, opened_at=date.today())
        db.add(business)
        db.flush()
        repo = PermanentDocumentRepository(db)
        repo.create(
            client_record_id=record.id,
            business_id=business.id,
            scope=DocumentScope.BUSINESS,
            document_type="tax_form",
            storage_key="b",
            uploaded_by=1,
            status=DocumentStatus.APPROVED,
        )
        docs = repo.list_by_client_record(record.id, scope=DocumentScope.BUSINESS)
        assert len(docs) == 1
        assert docs[0].business_id == business.id

