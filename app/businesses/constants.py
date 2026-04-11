from app.businesses.models.business import BusinessType

_SOLE_TRADER_TYPES: frozenset[BusinessType] = frozenset({
    BusinessType.OSEK_PATUR,
    BusinessType.OSEK_MURSHE,
})
