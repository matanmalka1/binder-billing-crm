from app.users.models.user import User, UserRole


def test_user_repr_includes_key_fields():
    user = User(
        id=7,
        full_name="Repr User",
        email="repr.user@example.com",
        password_hash="hash",
        role=UserRole.ADVISOR,
    )
    text = repr(user)
    assert "id=7" in text
    assert "repr.user@example.com" in text
    assert "UserRole.ADVISOR" in text
