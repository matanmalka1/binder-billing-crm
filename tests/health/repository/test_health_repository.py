import pytest

from app.health.repositories.health_repository import HealthRepository


def test_can_connect_returns_true_with_working_session(test_db):
    repo = HealthRepository(test_db)

    assert repo.can_connect() is True


def test_can_connect_returns_false_on_query_error():
    class BrokenSession:
        def query(self, *_args, **_kwargs):
            raise RuntimeError("db down")

    repo = HealthRepository(BrokenSession())

    assert repo.can_connect() is False
