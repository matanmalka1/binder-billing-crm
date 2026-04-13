from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import Binder
from app.binders.models.binder_status_log import BinderStatusLog
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository
from app.binders.repositories.binder_intake_repository import BinderIntakeRepository
from app.binders.repositories.binder_intake_material_repository import BinderIntakeMaterialRepository
from app.binders.schemas.binder import BinderHistoryEntry, BinderIntakeMaterialResponse, BinderIntakeResponse
from app.core.exceptions import NotFoundError
from app.binders.services.messages import BINDER_NOT_FOUND
from app.users.repositories.user_repository import UserRepository


class BinderHistoryService:
    """Binder audit history read service."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.log_repo = BinderStatusLogRepository(db)
        self.intake_repo = BinderIntakeRepository(db)
        self.material_repo = BinderIntakeMaterialRepository(db)
        self.user_repo = UserRepository(db)

    def build_history_entries(self, logs: list[BinderStatusLog]) -> list[BinderHistoryEntry]:
        """Enrich status log records with changed_by user names."""
        user_ids = {log.changed_by for log in logs}
        users = [self.user_repo.get_by_id(uid) for uid in user_ids]
        name_map = {u.id: u.full_name for u in users if u}
        return [
            BinderHistoryEntry(
                old_status=log.old_status,
                new_status=log.new_status,
                changed_by=log.changed_by,
                changed_by_name=name_map.get(log.changed_by),
                changed_at=log.changed_at,
                notes=log.notes,
            )
            for log in logs
        ]

    def get_binder_history(
        self, binder_id: int
    ) -> Optional[tuple[Binder, list[BinderStatusLog]]]:
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            return None
        logs = self.log_repo.list_by_binder(binder_id)
        return binder, logs

    def get_binder_intakes(self, binder_id: int) -> list[BinderIntakeResponse]:
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            raise NotFoundError(
                BINDER_NOT_FOUND.format(binder_id=binder_id),
                "BINDER.NOT_FOUND",
            )

        intakes = self.intake_repo.list_by_binder(binder_id)

        # Batch-fetch user names to avoid N+1 queries.
        user_ids = {i.received_by for i in intakes}
        users = [self.user_repo.get_by_id(uid) for uid in user_ids]
        name_map = {u.id: u.full_name for u in users if u}

        result: list[BinderIntakeResponse] = []
        for intake in intakes:
            # Populate the materials list for each intake.
            raw_materials = self.material_repo.list_by_intake(intake.id)
            material_responses = [
                BinderIntakeMaterialResponse.model_validate(m) for m in raw_materials
            ]
            result.append(
                BinderIntakeResponse(
                    id=intake.id,
                    binder_id=intake.binder_id,
                    received_at=intake.received_at,
                    received_by=intake.received_by,
                    received_by_name=name_map.get(intake.received_by),
                    notes=intake.notes,
                    created_at=intake.created_at,
                    materials=material_responses,
                )
            )
        return result
