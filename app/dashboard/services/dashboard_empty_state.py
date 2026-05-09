def build_attention_empty_checks(*, open_charges: int) -> list[dict[str, str]]:
    """Return attention-board empty-state checks based on real data.

    Only includes a check for a category that (a) has attention items and
    (b) is actually empty right now. Currently only open charges are
    surfaced as attention items, so only the charges check is emitted.
    """
    if open_charges == 0:
        return [{"key": "open_charges", "label": "אין חיובים פתוחים"}]
    return []
