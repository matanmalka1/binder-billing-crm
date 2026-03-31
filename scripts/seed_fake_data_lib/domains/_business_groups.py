from __future__ import annotations

from random import Random


def group_businesses_by_client(businesses) -> dict[int, list]:
    grouped: dict[int, list] = {}
    for business in businesses:
        grouped.setdefault(int(business.client_id), []).append(business)
    return grouped


def pick_businesses_for_client(rng: Random, client_businesses: list, count: int) -> list:
    if count <= 0 or not client_businesses:
        return []
    return [rng.choice(client_businesses) for _ in range(count)]
