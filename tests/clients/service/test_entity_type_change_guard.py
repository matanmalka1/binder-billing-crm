"""Step 3 tests: entity_type change guard in ClientService.update_client.

- SECRETARY cannot change entity_type → ForbiddenError
- ADVISOR can change entity_type → open deadlines canceled, audit logged
"""

from datetime import date
from itertools import count

import pytest

from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.services.client_service import ClientService
from app.common.enums import EntityType, IdNumberType, VatType
from app.core.exceptions import ForbiddenError
from app.tax_deadline.models.tax_deadline import TaxDeadline, DeadlineType, TaxDeadlineStatus
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.businesses.models.business import Business
from app.audit.models.entity_audit_log import EntityAuditLog

_seq = count(1)


def _make_user(db, role=UserRole.ADVISOR) -> User:
    u = User(
        full_name=f"User {next(_seq)}",
        email=f"u{next(_seq)}@test.com",
        password_hash=AuthService.hash_password("x"),
        role=role,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _setup(db) -> tuple:
    """Returns (client, client_record, advisor_user, secretary_user)."""
    idx = next(_seq)
    le = LegalEntity(
        id_number=f"ET{idx:06d}",
        id_number_type=IdNumberType.CORPORATION,
        entity_type=EntityType.OSEK_MURSHE,
        vat_reporting_frequency=VatType.MONTHLY,
    )
    db.add(le)
    db.flush()

    client = Client(
        full_name=f"EntityType Guard {idx}",
        id_number=f"ET{idx:06d}",
        entity_type=EntityType.OSEK_MURSHE,
        vat_reporting_frequency=VatType.MONTHLY,
    )
    db.add(client)
    db.flush()

    cr = ClientRecord(id=client.id, legal_entity_id=le.id)
    db.add(cr)

    biz = Business(client_id=client.id, business_name=client.full_name, opened_at=date(2026, 1, 1))
    db.add(biz)
    db.commit()
    db.refresh(client)
    db.refresh(cr)

    advisor = _make_user(db, UserRole.ADVISOR)
    secretary = _make_user(db, UserRole.SECRETARY)
    db.commit()
    return client, cr, advisor, secretary


def _add_pending_deadline(db, client, cr) -> TaxDeadline:
    dl = TaxDeadline(
        client_record_id=cr.id,
        deadline_type=DeadlineType.VAT,
        period="2026-05",
        due_date=date(2026, 6, 15),
        status=TaxDeadlineStatus.PENDING,
    )
    db.add(dl)
    db.commit()
    return dl


def test_secretary_cannot_change_entity_type(test_db):
    client, cr, advisor, secretary = _setup(test_db)
    service = ClientService(test_db)

    with pytest.raises(ForbiddenError):
        service.update_client(
            client.id,
            actor_id=secretary.id,
            actor_role=UserRole.SECRETARY,
            entity_type=EntityType.COMPANY_LTD,
        )


def test_advisor_can_change_entity_type_and_cancels_deadlines(test_db):
    client, cr, advisor, secretary = _setup(test_db)
    dl = _add_pending_deadline(test_db, client, cr)

    service = ClientService(test_db)
    service.update_client(
        client.id,
        actor_id=advisor.id,
        actor_role=UserRole.ADVISOR,
        entity_type=EntityType.COMPANY_LTD,
    )

    test_db.refresh(dl)
    assert dl.status == TaxDeadlineStatus.CANCELED


def test_entity_type_change_logs_audit_entry(test_db):
    client, cr, advisor, secretary = _setup(test_db)

    service = ClientService(test_db)
    service.update_client(
        client.id,
        actor_id=advisor.id,
        actor_role=UserRole.ADVISOR,
        entity_type=EntityType.COMPANY_LTD,
    )

    audit_entries = (
        test_db.query(EntityAuditLog)
        .filter(
            EntityAuditLog.entity_id == client.id,
            EntityAuditLog.action == "entity_type_changed",
        )
        .all()
    )
    assert len(audit_entries) == 1
    entry = audit_entries[0]
    assert entry.old_value is not None
    assert entry.new_value is not None
    assert entry.old_value != entry.new_value


def test_non_entity_type_update_does_not_cancel_deadlines(test_db):
    client, cr, advisor, secretary = _setup(test_db)
    dl = _add_pending_deadline(test_db, client, cr)

    service = ClientService(test_db)
    service.update_client(
        client.id,
        actor_id=advisor.id,
        actor_role=UserRole.ADVISOR,
        full_name="New Name",
    )

    test_db.refresh(dl)
    assert dl.status == TaxDeadlineStatus.PENDING
