"""
קבועים סטטוטוריים — אינם תלויי שנת מס.
מקורות: פקודת מס הכנסה [נוסח חדש] + חוק מע"מ.
"""
from __future__ import annotations

# ── סעיף 46 לפקודת מס הכנסה — זיכוי בגין תרומות ─────────────────────────────
# שיעור זיכוי 35% על תרומות מעל לסף המינימום.
# מקור: פקודת מס הכנסה, סעיף 46; אומת מול כל זכות.
DONATION_CREDIT_RATE: float = 0.35
DONATION_MINIMUM_ILS: float = 190.0

__all__ = [
    "DONATION_CREDIT_RATE",
    "DONATION_MINIMUM_ILS",
]
