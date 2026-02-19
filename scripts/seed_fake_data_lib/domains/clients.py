from __future__ import annotations

from datetime import date, timedelta
from random import Random

from app.clients.models.client import Client, ClientStatus, ClientType

from ..constants import COMPANY_WORDS
from ..random_utils import full_name


def create_clients(db, rng: Random, cfg) -> list[Client]:
    clients: list[Client] = []
    for i in range(cfg.clients):
        open_days_ago = rng.randint(20, 1100)
        opened_at = date.today() - timedelta(days=open_days_ago)
        status = rng.choices(
            [ClientStatus.ACTIVE, ClientStatus.FROZEN, ClientStatus.CLOSED],
            weights=[80, 12, 8],
            k=1,
        )[0]
        closed_at = None
        if status == ClientStatus.CLOSED:
            closed_at = opened_at + timedelta(days=rng.randint(30, 800))
            if closed_at > date.today():
                closed_at = date.today() - timedelta(days=rng.randint(1, 15))

        client_type = rng.choice(list(ClientType))
        if client_type == ClientType.COMPANY:
            full_name_value = f"{rng.choice(COMPANY_WORDS)} {rng.choice(COMPANY_WORDS)} Ltd"
        else:
            full_name_value = full_name(rng)

        client = Client(
            full_name=full_name_value,
            id_number=f"{rng.randint(100000000, 999999999)}",
            client_type=client_type,
            status=status,
            primary_binder_number=f"PB-{50000 + i}",
            phone=f"05{rng.randint(10000000, 99999999)}",
            email=f"client{i + 1}@example.com",
            notes=rng.choice(["", "VIP", "Prefers WhatsApp", "Monthly follow-up"]),
            opened_at=opened_at,
            closed_at=closed_at,
        )
        db.add(client)
        clients.append(client)
    db.flush()
    return clients
