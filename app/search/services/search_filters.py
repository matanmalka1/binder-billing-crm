def matches_signal_type(current_signals: list[str], signal_types: list[str]) -> bool:
    if not signal_types:
        return True
    return any(signal in current_signals for signal in signal_types)
