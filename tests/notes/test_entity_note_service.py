from app.notes.services.entity_note_service import EntityNoteService


def test_list_notes_includes_creator_name(test_db, test_user):
    service = EntityNoteService(test_db)
    created = service.add_note(
        entity_type="client",
        entity_id=123,
        note="בדיקה",
        created_by=test_user.id,
    )
    test_db.commit()

    items, total = service.list_notes(entity_type="client", entity_id=123)

    assert total == 1
    assert items[0].id == created.id
    assert items[0].created_by == test_user.id
    assert items[0].created_by_name == test_user.full_name


def test_update_note_keeps_creator_name(test_db, test_user):
    service = EntityNoteService(test_db)
    created = service.add_note(
        entity_type="client",
        entity_id=123,
        note="לפני",
        created_by=test_user.id,
    )
    test_db.commit()

    updated = service.update_note(
        note_id=created.id,
        entity_type="client",
        entity_id=123,
        note="אחרי",
        actor_id=test_user.id,
    )

    assert updated.note == "אחרי"
    assert updated.created_by_name == test_user.full_name


def test_missing_creator_does_not_fallback_to_another_user(test_db, test_user):
    service = EntityNoteService(test_db)
    service.add_note(
        entity_type="client",
        entity_id=123,
        note="יוצר חסר",
        created_by=test_user.id + 999,
    )
    test_db.commit()

    items, total = service.list_notes(entity_type="client", entity_id=123)

    assert total == 1
    assert items[0].created_by_name is None
