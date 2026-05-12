"""Shared update/delete logic for financial line repositories (income, expense)."""

from typing import TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class FinancialLineMixin:
    """Mixin for repositories whose entities are simple hard-deleted financial lines."""

    db: Session  # set by concrete repository __init__

    def _update_line(self, get_by_id, line_id: int, **fields):
        line = get_by_id(line_id)
        if not line:
            return None
        for k, v in fields.items():
            if hasattr(line, k):
                setattr(line, k, v)
        self.db.flush()
        return line

    def _delete_line(self, get_by_id, line_id: int) -> bool:
        line = get_by_id(line_id)
        if not line:
            return False
        self.db.delete(line)
        self.db.flush()
        return True
