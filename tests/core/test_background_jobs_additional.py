import asyncio
from types import SimpleNamespace

import pytest

from app.core import background_jobs


class _StopLoop(Exception):
    pass


class _FakeDB:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeRepo:
    def __init__(self, db):
        self.db = db


class _FakeReminderService:
    def __init__(self, db):
        self.db = db
        self.sent = []

    def get_pending_reminders(self):
        return ([SimpleNamespace(id=1, reminder_type="custom")], 1, [])

    def mark_sent(self, reminder_id):
        self.sent.append(reminder_id)


def test_run_startup_expiry_uses_repo_and_closes_db(monkeypatch):
    db = _FakeDB()
    monkeypatch.setattr(background_jobs, "SessionLocal", lambda: db)
    monkeypatch.setattr(background_jobs, "SignatureRequestRepository", _FakeRepo)
    monkeypatch.setattr(background_jobs, "expire_overdue_requests", lambda repo: 2)

    background_jobs.run_startup_expiry()

    assert db.closed is True


def test_daily_expiry_job_runs_one_iteration_and_handles_errors(monkeypatch):
    db = _FakeDB()
    sleep_calls = {"n": 0}

    async def _fake_sleep(_):
        sleep_calls["n"] += 1
        if sleep_calls["n"] > 1:
            raise _StopLoop()

    monkeypatch.setattr(background_jobs, "SessionLocal", lambda: db)
    monkeypatch.setattr(background_jobs, "SignatureRequestRepository", _FakeRepo)
    monkeypatch.setattr(background_jobs, "expire_overdue_requests", lambda repo: 0)
    monkeypatch.setattr(background_jobs.asyncio, "sleep", _fake_sleep)

    with pytest.raises(_StopLoop):
        asyncio.run(background_jobs.daily_expiry_job())

    assert db.closed is True


def test_daily_reminder_job_runs_one_iteration(monkeypatch):
    db = _FakeDB()
    fake_service = _FakeReminderService(db)
    sleep_calls = {"n": 0}

    async def _fake_sleep(_):
        sleep_calls["n"] += 1
        if sleep_calls["n"] > 1:
            raise _StopLoop()

    monkeypatch.setattr(background_jobs, "SessionLocal", lambda: db)
    monkeypatch.setattr(background_jobs, "ReminderService", lambda _db: fake_service)
    monkeypatch.setattr(background_jobs.asyncio, "sleep", _fake_sleep)

    with pytest.raises(_StopLoop):
        asyncio.run(background_jobs.daily_reminder_job())

    assert fake_service.sent == [1]
    assert db.closed is True
