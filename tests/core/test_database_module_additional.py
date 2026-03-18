import importlib

import pytest

import app.config as config_mod
import app.database as database_mod


def test_get_db_closes_session_on_generator_close(monkeypatch):
    class _DB:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    db = _DB()
    monkeypatch.setattr(database_mod, "SessionLocal", lambda: db)

    dep = database_mod.get_db()
    yielded = next(dep)
    assert yielded is db
    assert db.closed is False

    dep.close()
    assert db.closed is True


def test_database_module_rejects_sqlite_in_production(monkeypatch):
    class _Cfg:
        APP_ENV = "production"
        DATABASE_URL = "sqlite:///should_fail.db"

    original = config_mod.config
    monkeypatch.setattr(config_mod, "config", _Cfg)
    try:
        with pytest.raises(RuntimeError):
            importlib.reload(database_mod)
    finally:
        config_mod.config = original
        importlib.reload(database_mod)
