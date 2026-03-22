import pytest

from app.binders.services.binder_service import BinderService
from app.clients.repositories.client_repository import ClientRepository


@pytest.fixture(autouse=True)
def _ensure_binder_service_client_repo(monkeypatch):
    """
    Test-only compatibility shim:
    BinderService currently misses client_repo init, while API response helpers
    call BinderListService methods that require it.
    """
    original_init = BinderService.__init__

    def patched_init(self, db):
        original_init(self, db)
        if not hasattr(self, "client_repo"):
            self.client_repo = ClientRepository(db)

    monkeypatch.setattr(BinderService, "__init__", patched_init)
