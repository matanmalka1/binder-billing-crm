from app.users.models.user import UserRole
from app.users.repositories.user_repository import UserRepository


def test_get_by_email_and_update_last_login(test_db):
    repo = UserRepository(test_db)
    created = repo.create(
        full_name="Repo User",
        email="repo.user@example.com",
        password_hash="hashed",
        role=UserRole.ADVISOR,
    )

    fetched = repo.get_by_email("repo.user@example.com")
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.last_login_at is None

    repo.update_last_login(created.id)
    refreshed = repo.get_by_id(created.id)
    assert refreshed.last_login_at is not None


def test_token_version_mutation_methods(test_db):
    repo = UserRepository(test_db)
    user = repo.create(
        full_name="Token User",
        email="token.user@example.com",
        password_hash="original-hash",
        role=UserRole.SECRETARY,
    )

    bumped = repo.bump_token_version(user.id)
    assert bumped.token_version == 1
    assert bumped.is_active is True

    deactivated = repo.deactivate_and_bump_token(user.id)
    assert deactivated.is_active is False
    assert deactivated.token_version == 2

    reset = repo.set_password_and_bump_token(user.id, "new-hash")
    assert reset.password_hash == "new-hash"
    assert reset.token_version == 3

    assert repo.bump_token_version(999999) is None
    assert repo.deactivate_and_bump_token(999999) is None
    assert repo.set_password_and_bump_token(999999, "x") is None


def test_list_by_ids_handles_empty_and_existing_ids(test_db):
    repo = UserRepository(test_db)
    first = repo.create(
        full_name="List User One",
        email="list.one@example.com",
        password_hash="hashed",
        role=UserRole.ADVISOR,
    )
    second = repo.create(
        full_name="List User Two",
        email="list.two@example.com",
        password_hash="hashed",
        role=UserRole.SECRETARY,
    )

    assert repo.list_by_ids([]) == []
    fetched = repo.list_by_ids([first.id, second.id])
    assert {item.id for item in fetched} == {first.id, second.id}
