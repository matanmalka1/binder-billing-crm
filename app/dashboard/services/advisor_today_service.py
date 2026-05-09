from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session


class AdvisorTodayService:
    def __init__(self, db: Session):
        self.db = db

    def build(self, reference_date: date) -> dict:
        return {"deadline_items": []}
