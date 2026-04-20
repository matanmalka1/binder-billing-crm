from sqlalchemy.orm import Session

from app.binders.repositories.binder_repository import BinderRepository


class BinderRepositoryExtensions(BinderRepository):
    """Compatibility shim for callers/tests that still import the legacy name."""

    def __init__(self, db: Session):
        super().__init__(db)

    def list_by_client(
        self,
        client_record_id: int,
        page: int = 1,
        page_size: int = 20,
    ):
        return self.list_by_client_paginated(
            client_record_id=client_record_id,
            page=page,
            page_size=page_size,
        )
