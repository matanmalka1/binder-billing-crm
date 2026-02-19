from __future__ import annotations

from random import Random

from .constants import FIRST_NAMES, LAST_NAMES


def full_name(rng: Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
