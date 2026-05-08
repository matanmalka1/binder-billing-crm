import json

from app.audit.constants import ACTION_STATUS_CHANGED, ACTION_UPDATED, ENTITY_CLIENT
from app.audit.models.entity_audit_log import EntityAuditLog
from app.audit.services.entity_audit_writer import EntityAuditWriter


def test_writer_serializes_dict_as_valid_json(test_db, test_user):
    EntityAuditWriter(test_db).record_update(
        ENTITY_CLIENT,
        10,
        test_user.id,
        old_value={"full_name": "ישן"},
        new_value={"full_name": "חדש"},
    )

    entry = test_db.query(EntityAuditLog).one()
    assert entry.action == ACTION_UPDATED
    assert json.loads(entry.old_value) == {"full_name": "ישן"}
    assert json.loads(entry.new_value) == {"full_name": "חדש"}


def test_writer_wraps_plain_string(test_db, test_user):
    EntityAuditWriter(test_db).record_update(
        ENTITY_CLIENT,
        10,
        test_user.id,
        old_value="old",
        new_value="new",
    )

    entry = test_db.query(EntityAuditLog).one()
    assert json.loads(entry.old_value) == {"value": "old"}
    assert json.loads(entry.new_value) == {"value": "new"}


def test_writer_skips_when_actor_is_none(test_db):
    result = EntityAuditWriter(test_db).record_create(ENTITY_CLIENT, 10, None, new_value={"x": 1})

    assert result is None
    assert test_db.query(EntityAuditLog).count() == 0


def test_record_status_change_stores_status_payload(test_db, test_user):
    EntityAuditWriter(test_db).record_status_change(
        ENTITY_CLIENT,
        10,
        test_user.id,
        "draft",
        "active",
    )

    entry = test_db.query(EntityAuditLog).one()
    assert entry.action == ACTION_STATUS_CHANGED
    assert json.loads(entry.old_value) == {"status": "draft"}
    assert json.loads(entry.new_value) == {"status": "active"}
