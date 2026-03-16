from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.clients.schemas.client import BulkClientFailedItem
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.clients.models.client import Client, ClientStatus
from app.users.models.user import UserRole
from app.clients.repositories.client_repository import ClientRepository
from app.binders.services.signals_service import SignalsService

# Hard limit for in-memory signal filtering.
# Exceeding this means the deployment has outgrown in-memory signal computation.
# Proper fix: persist signal state or use a materialized view (Sprint 10+).
_HAS_SIGNALS_FETCH_LIMIT = 1000


class ClientService:
    """Client management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRepository(db)
        self.signals_service = SignalsService(db)

    def create_client(
        self,
        full_name: str,
        id_number: str,
        client_type: str,
        opened_at: date,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        notes: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> Client:
        """Create new client. Raises ValueError if ID number exists."""
        existing = self.client_repo.get_by_id_number(id_number)
        if existing:
            raise ConflictError(f"לקוח עם מספר ת.ז. {id_number} כבר קיים", "CLIENT.CONFLICT")

        return self.client_repo.create(
            full_name=full_name,
            id_number=id_number,
            client_type=client_type,
            opened_at=opened_at,
            phone=phone,
            email=email,
            notes=notes,
            created_by=actor_id,
        )

    def get_client(self, client_id: int) -> Optional[Client]:
        """Get client by ID."""
        return self.client_repo.get_by_id(client_id)

    def _client_has_operational_signals(
        self,
        client_id: int,
        reference_date: Optional[date] = None,
    ) -> bool:
        signals = self.signals_service.compute_client_signals(
            client_id=client_id,
            reference_date=reference_date,
        )
        return bool(
            signals.get("missing_documents")
            or signals.get("unpaid_charges")
            or signals.get("binder_signals")
        )

    def list_clients(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        has_signals: Optional[bool] = None,
        search: Optional[str] = None,
        reference_date: Optional[date] = None,
    ) -> tuple[list[Client], int]:
        """List clients with pagination. Returns (items, total)."""
        if has_signals is None:
            items = self.client_repo.list(
                status=status, page=page, page_size=page_size, search=search
            )
            total = self.client_repo.count(status=status, search=search)
            return items, total

        total_count = self.client_repo.count(status=status, search=search)
        if total_count > _HAS_SIGNALS_FETCH_LIMIT:
            raise AppError(
                f"מספר הלקוחות ({total_count}) חורג מהמגבלה לסינון לפי איתותים ({_HAS_SIGNALS_FETCH_LIMIT}). "
                "יש להשתמש בפילטרים נוספים.",
                "CLIENT.INVALID_STATUS",
            )
        base_clients = self.client_repo.list(
            status=status, page=1, page_size=_HAS_SIGNALS_FETCH_LIMIT, search=search
        )
        filtered = [
            client
            for client in base_clients
            if self._client_has_operational_signals(client.id, reference_date)
            == has_signals
        ]

        total = len(filtered)
        offset = (page - 1) * page_size
        return filtered[offset : offset + page_size], total

    def list_all_clients(self, status: Optional[str] = None) -> list[Client]:
        """Return every client matching the optional status filter."""
        return self.client_repo.list_all(status=status)

    def delete_client(self, client_id: int, actor_id: int) -> bool:
        """Soft-delete a client. Returns False if not found."""
        client = self.client_repo.get_by_id(client_id)
        if not client:
            return False
        return self.client_repo.soft_delete(client_id, deleted_by=actor_id)

    def update_client(
        self,
        client_id: int,
        user_role: UserRole,
        **fields,
    ) -> Optional[Client]:
        client = self.client_repo.get_by_id(client_id)
        if not client:
            return None

        if "status" in fields and fields["status"] in ["frozen", "closed"]:
            if user_role != UserRole.ADVISOR:
                raise ForbiddenError("רק יועצים יכולים להקפיא או לסגור לקוחות", "CLIENT.FORBIDDEN")

        if "status" in fields and fields["status"] == ClientStatus.CLOSED:
            if "closed_at" not in fields:
                fields["closed_at"] = date.today()

        return self.client_repo.update(client_id, **fields)

    def bulk_update_status(
        self,
        client_ids: list[int],
        action: str,
        actor_id: int,
    ) -> tuple[list[int], list[BulkClientFailedItem]]:
        """Apply freeze/close/activate to multiple clients. Never raises on partial failure."""
        action_to_status = {"freeze": "frozen", "close": "closed", "activate": "active"}
        status = action_to_status[action]

        succeeded: list[int] = []
        failed: list[BulkClientFailedItem] = []

        for client_id in client_ids:
            try:
                result = self.update_client(
                    client_id=client_id,
                    user_role=UserRole.ADVISOR,
                    status=status,
                )
                if result is None:
                    raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
                succeeded.append(client_id)
            except Exception as exc:
                failed.append(BulkClientFailedItem(id=client_id, error=str(exc)))

        return succeeded, failed
