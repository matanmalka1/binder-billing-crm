from app.search.services.search_filters import matches_signal_type


def test_matches_signal_type_returns_true_when_no_filter():
    assert matches_signal_type(["late_submission"], []) is True


def test_matches_signal_type_returns_true_when_any_signal_matches():
    assert matches_signal_type(["missing_docs", "overdue"], ["overdue", "idle_binder"]) is True


def test_matches_signal_type_returns_false_when_no_signal_matches():
    assert matches_signal_type(["missing_docs"], ["overdue"]) is False


def test_matches_signal_type_handles_empty_current_signals():
    assert matches_signal_type([], ["overdue"]) is False
