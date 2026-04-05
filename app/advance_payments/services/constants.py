"""Advance payment domain constants."""

from decimal import Decimal

# Israeli VAT rate (מע"מ). Update this when the rate changes.
# History: 17% until 2015-10-01, 18% from 2025-01-01.
VAT_RATE: Decimal = Decimal("0.18")
