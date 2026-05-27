from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.time_utils import utcnow


class BinderHandover(Base):
    """
    Grouped handover event: one or more binders physically returned to the client together.

    Records who received the binders on the client side, when, and up to which
    reporting-period cutoff the binders were returned.
    """

    __tablename__ = "binder_handovers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_record_id: Mapped[int] = mapped_column(
        ForeignKey("client_records.id"), nullable=False, index=True
    )

    # Name of the person who physically received the binders on the client side.
    received_by_name: Mapped[str] = mapped_column(String, nullable=False)

    # Date the handover physically took place.
    handed_over_at: Mapped[date] = mapped_column(nullable=False)

    # Reporting-period cutoff: all binders up to this period were returned.
    until_period_year: Mapped[int] = mapped_column(nullable=False)
    until_period_month: Mapped[int] = mapped_column(nullable=False)  # 1–12

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<BinderHandover(id={self.id}, client_record_id={self.client_record_id}, "
            f"handed_over_at='{self.handed_over_at}')>"
        )


class BinderHandoverBinder(Base):
    """Association between a handover event and the specific binders returned in it."""

    __tablename__ = "binder_handover_binders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    handover_id: Mapped[int] = mapped_column(
        ForeignKey("binder_handovers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    binder_id: Mapped[int] = mapped_column(
        ForeignKey("binders.id"),
        nullable=False,
        index=True,
    )

    __table_args__ = (Index("idx_handover_binder_unique", "handover_id", "binder_id", unique=True),)

    def __repr__(self):
        return f"<BinderHandoverBinder(handover_id={self.handover_id}, binder_id={self.binder_id})>"
