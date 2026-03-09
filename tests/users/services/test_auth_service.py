import pytest

from app.users.services.auth_service import AuthService


def test_verify_password_accepts_correct_secret():
    password = "Sup3r$ecret!"
    password_hash = AuthService.hash_password(password)

    assert AuthService.verify_password(password, password_hash) is True


def test_verify_password_rejects_wrong_secret():
    password_hash = AuthService.hash_password("correct-horse")

    assert AuthService.verify_password("battery-staple", password_hash) is False
