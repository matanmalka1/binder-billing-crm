from app.clients.repositories.client_repository import ClientRepository
from app.clients.models.client import Client


def get_client_or_raise(client_repo: ClientRepository, client_id: int) -> Client:
    """Fetch a client or raise a ValueError if missing."""
    client = client_repo.get_by_id(client_id)
    if not client:
        raise ValueError(f"Client {client_id} not found")
    return client
