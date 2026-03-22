from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder_intake_material import BinderIntakeMaterial, MaterialType


class BinderIntakeMaterialRepository:
    """Data access layer for BinderIntakeMaterial entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        intake_id: int,
        material_type: MaterialType,
        business_id: Optional[int] = None,
        annual_report_id: Optional[int] = None,
        description: Optional[str] = None,
    ) -> BinderIntakeMaterial:
        material = BinderIntakeMaterial(
            intake_id=intake_id,
            material_type=material_type,
            business_id=business_id,
            annual_report_id=annual_report_id,
            description=description,
        )
        self.db.add(material)
        self.db.commit()
        self.db.refresh(material)
        return material

    def list_by_intake(self, intake_id: int) -> list[BinderIntakeMaterial]:
        return (
            self.db.query(BinderIntakeMaterial)
            .filter(BinderIntakeMaterial.intake_id == intake_id)
            .order_by(BinderIntakeMaterial.id.asc())
            .all()
        )

    def list_by_binder(self, binder_id: int) -> list[BinderIntakeMaterial]:
        """Return all materials across all intakes for a binder (via join)."""
        from app.binders.models.binder_intake import BinderIntake
        return (
            self.db.query(BinderIntakeMaterial)
            .join(BinderIntake, BinderIntake.id == BinderIntakeMaterial.intake_id)
            .filter(BinderIntake.binder_id == binder_id)
            .order_by(BinderIntakeMaterial.id.asc())
            .all()
        )
