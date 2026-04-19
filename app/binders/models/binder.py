from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Date, DateTime, ForeignKey,
    Index, Integer, String, Text,
    column, and_,
)
from sqlalchemy.orm import relationship
from app.utils.enum_utils import pg_enum
from app.database import Base
from app.utils.time_utils import utcnow


class BinderStatus(str, PyEnum):
    IN_OFFICE = "in_office"
    CLOSED_IN_OFFICE = "closed_in_office"   # full, no more intake, still physically present
    READY_FOR_PICKUP = "ready_for_pickup"
    RETURNED = "returned"


RETURNED_STATUS_VALUE = BinderStatus.RETURNED.value


class Binder(Base):
    """
    Physical binder belonging to a client.

    A binder is identified by a globally unique number (binder_number)
    assigned to the client and kept constant throughout the binder's lifecycle.
    When a binder is full, a new binder is opened with the same number
    and a new period.

    All materials from all of the client's businesses are stored in the same binder.
    The material type is defined at the BinderIntakeMaterial level, not at binder level.
    """
    __tablename__ = "binders"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # The binder belongs to the client, not to a specific business.
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    client_record_id = Column(Integer, ForeignKey("client_records.id"), nullable=True, index=True)

    # Globally unique number (the label number on the physical binder).
    binder_number = Column(String, nullable=False)

    # Binder period: when it starts and when it ends.
    # period_start is derived from the reporting period of the first material inserted.
    # NULL for newly opened binders that have not yet received any material.
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)  # null = active/open binder

    # Binder status.
    status = Column(
        pg_enum(BinderStatus),
        default=BinderStatus.IN_OFFICE,
        nullable=False,
    )

    # When the client actually picked up the binder.
    returned_at = Column(Date, nullable=True)

    # Who picked up the binder (client / courier / employee / family member).
    pickup_person_name = Column(String, nullable=True)

    # Physical logistics info: shelf location, binder color, material condition.
    notes = Column(Text, nullable=True)

    # Metadata.
    created_at = Column(DateTime, default=utcnow, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    intakes = relationship("BinderIntake", back_populates="binder", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_binder_client", "client_id"),
        Index("idx_binder_status", "status"),
        Index("idx_binder_period_start", "period_start"),
        # Unique binder_number among open (IN_OFFICE) non-deleted binders only.
        # CLOSED_IN_OFFICE and RETURNED binders may share a number with a newer IN_OFFICE binder.
        Index(
            "idx_active_binder_unique",
            "binder_number",
            unique=True,
            postgresql_where=and_(
                column("status") == BinderStatus.IN_OFFICE.value,
                column("deleted_at").is_(None),
            ),
            sqlite_where=and_(
                column("status") == BinderStatus.IN_OFFICE.value,
                column("deleted_at").is_(None),
            ),
        ),
    )
    def __repr__(self):
        return (
            f"<Binder(id={self.id}, number='{self.binder_number}', "
            f"client_id={self.client_id}, status='{self.status}')>"
        )
