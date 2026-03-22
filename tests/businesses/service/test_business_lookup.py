from app.businesses.services.business_lookup import get_business_or_raise
from app.core.exceptions import NotFoundError


class _Repo:
    def __init__(self, result):
        self._result = result

    def get_by_id(self, _business_id):
        return self._result


def test_get_business_or_raise_returns_business(monkeypatch):
    business = object()

    monkeypatch.setattr(
        "app.businesses.services.business_lookup.BusinessRepository",
        lambda _db: _Repo(business),
    )

    assert get_business_or_raise(db=object(), business_id=10) is business


def test_get_business_or_raise_raises_not_found(monkeypatch):
    monkeypatch.setattr(
        "app.businesses.services.business_lookup.BusinessRepository",
        lambda _db: _Repo(None),
    )

    try:
        get_business_or_raise(db=object(), business_id=404)
        raise AssertionError("Expected NotFoundError")
    except NotFoundError as exc:
        assert exc.code == "BUSINESS.NOT_FOUND"
