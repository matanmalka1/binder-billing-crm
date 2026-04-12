from app.businesses.models.business import EntityType

_SOLE_TRADER_TYPES: frozenset[EntityType] = frozenset({
    EntityType.OSEK_PATUR,
    EntityType.OSEK_MURSHE,
})
