from sqlalchemy import CheckConstraint, Column, DateTime, Index, Integer, String
from app.database import Base
from app.utils.time_utils import utcnow
from app.common.enums import IdNumberType
from app.utils.enum_utils import pg_enum


class Person(Base):
    """Physical individual who may own or be linked to one or more legal entities."""

    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, autoincrement=True)

    full_name = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    # Person-valid types only — CORPORATION is rejected by the check constraint below.
    id_number = Column(String, nullable=False)
    id_number_type = Column(pg_enum(IdNumberType), nullable=False)

    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)

    address_street = Column(String, nullable=True)
    address_building_number = Column(String, nullable=True)
    address_apartment = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_zip_code = Column(String, nullable=True)

    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint(
            "id_number_type IN ('individual', 'passport', 'other')",
            name="ck_persons_id_number_type_not_corporation",
        ),
        Index("ix_persons_full_name", "full_name"),
        Index("ix_persons_id_number", "id_number"),
    )

    def __repr__(self) -> str:
        return f"<Person(id={self.id}, full_name='{self.full_name}')>"
