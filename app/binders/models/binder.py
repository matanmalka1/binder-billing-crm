from __future__ import annotations

from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.enum_utils import pg_enum
from app.utils.time_utils import utcnow


class BinderStatus(str, PyEnum):
    IN_OFFICE = "in_office"
    CLOSED_IN_OFFICE = "closed_in_office"  # full, no more intake, still physically present
    READY_FOR_PICKUP = "ready_for_pickup"
    RETURNED = "returned"


RETURNED_STATUS_VALUE = BinderStatus.RETURNED.value


class Binder(Base):
    """
    Physical binder belonging to a client.

    A binder is identified by a number (binder_number) that is unique per
    client_record_id while the binder is not soft-deleted.

    All materials from all of the client's businesses are stored in the same binder.
    The material type is defined at the BinderIntakeMaterial level, not at binder level.
    """

    __tablename__ = "binders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    client_record_id: Mapped[int] = mapped_column(
        ForeignKey("client_records.id"), nullable=False, index=True
    )

    # Label number on the physical binder, unique per active client record.
    binder_number: Mapped[str] = mapped_column(String, nullable=False)

    # Binder period: when it starts and when it ends.
    # period_start is derived from the reporting period of the first material inserted.
    # NULL for newly opened binders that have not yet received any material.
    period_start: Mapped[date | None] = mapped_column(nullable=True)
    period_end: Mapped[date | None] = mapped_column(nullable=True)  # null = active/open binder

    # Binder status.
    status: Mapped[BinderStatus] = mapped_column(
        pg_enum(BinderStatus),
        default=BinderStatus.IN_OFFICE,
        nullable=False,
    )

    # When the binder was marked ready for pickup (used for overdue pickup detection).
    ready_for_pickup_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # When the client actually picked up the binder.
    returned_at: Mapped[date | None] = mapped_column(nullable=True)

    # Who picked up the binder (client / courier / employee / family member).
    pickup_person_name: Mapped[str | None] = mapped_column(String, nullable=True)

    # Physical logistics info: shelf location, binder color, material condition.
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata.
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    intakes: Mapped[list["BinderIntake"]] = relationship(
        "BinderIntake", back_populates="binder", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_binder_status", "status"),
        Index("idx_binder_period_start", "period_start"),
        Index(
            "uq_binder_number_per_client",
            "client_record_id",
            "binder_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self):
        return (
            f"<Binder(id={self.id}, number='{self.binder_number}', "
            f"client_record_id={self.client_record_id}, status='{self.status}')>"
        )
