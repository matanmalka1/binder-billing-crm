from app.health.services.health_service import HealthService


def test_health_service_check_handles_repo_exception(monkeypatch, test_db):
    service = HealthService(test_db)

    class _BrokenRepo:
        def can_connect(self):
            raise RuntimeError("boom")

    service.health_repo = _BrokenRepo()
    result = service.check()
    assert result == {"status": "unhealthy", "database": "disconnected"}

