import pytest

from app.actions import obligation_orchestrator as orchestrator
from app.common.enums import EntityType


def test_derive_client_type_raises_for_missing_or_unknown_entity_type():
    with pytest.raises(ValueError, match="סוג ישות לא נתמך ליצירת דוח שנתי"):
        orchestrator._derive_client_type(None)

    with pytest.raises(ValueError, match="סוג ישות לא נתמך ליצירת דוח שנתי"):
        orchestrator._derive_client_type("unknown")  # type: ignore[arg-type]


def test_generate_client_obligations_fails_before_writes_for_unknown_entity_type(monkeypatch):
    class Repo:
        def __init__(self, db):
            self.db = db

        def get_by_id(self, client_record_id):
            return object()

    class DeadlineGenerator:
        def __init__(self, db):
            raise AssertionError("Deadline generation should not start")

    class ReportService:
        def __init__(self, db):
            raise AssertionError("Report creation should not start")

    monkeypatch.setattr(orchestrator, "ClientRecordRepository", Repo)
    monkeypatch.setattr(orchestrator, "DeadlineGeneratorService", DeadlineGenerator)
    monkeypatch.setattr(orchestrator, "AnnualReportService", ReportService)

    with pytest.raises(ValueError, match="סוג ישות לא נתמך ליצירת דוח שנתי"):
        orchestrator.generate_client_obligations(
            db=object(),
            client_record_id=1,
            entity_type="unknown",  # type: ignore[arg-type]
        )


def test_derive_client_type_maps_supported_entity_type():
    client_type = orchestrator._derive_client_type(EntityType.OSEK_MURSHE)

    assert client_type.value == "self_employed"


def test_generate_client_obligations_result_collects_partial_failures(monkeypatch):
    class Savepoint:
        def commit(self):
            return None

        def rollback(self):
            return None

    class Db:
        def begin_nested(self):
            return Savepoint()

    class Repo:
        def __init__(self, db):
            self.db = db

        def get_by_id(self, client_record_id):
            return object()

    class DeadlineGenerator:
        def __init__(self, db):
            self.db = db

        def generate_all(self, client_record_id, year):
            if year == 2027:
                raise RuntimeError("deadline failed")
            return 2

    class ReportService:
        def __init__(self, db):
            self.db = db

        def create_report(self, **kwargs):
            if kwargs["tax_year"] == 2026:
                raise RuntimeError("report failed")

    monkeypatch.setattr(orchestrator, "ClientRecordRepository", Repo)
    monkeypatch.setattr(orchestrator, "DeadlineGeneratorService", DeadlineGenerator)
    monkeypatch.setattr(orchestrator, "AnnualReportService", ReportService)

    result = orchestrator.generate_client_obligations_result(
        db=Db(),
        client_record_id=1,
        entity_type=EntityType.OSEK_MURSHE,
        reference_date=orchestrator.date(2026, 10, 1),
        best_effort=True,
    )

    assert result.deadlines_created == 2
    assert result.reports_created == 1
    assert result.total_created == 3
    assert result.errors == [
        "deadline_generation_failed:2027",
        "annual_report_creation_failed:2026",
    ]


def test_generate_client_obligations_keeps_int_api(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "generate_client_obligations_result",
        lambda **kwargs: orchestrator.ObligationResult(
            deadlines_created=2,
            reports_created=1,
        ),
    )

    total = orchestrator.generate_client_obligations(
        db=object(),
        client_record_id=1,
        entity_type=EntityType.OSEK_MURSHE,
    )

    assert total == 3
