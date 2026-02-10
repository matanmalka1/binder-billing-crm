from sqlalchemy.orm import Session

from app.models import Binder


class TimelineRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_client_binders(self, client_id: int) -> list[Binder]:
        return self.db.query(Binder).filter(Binder.client_id == client_id).all()
