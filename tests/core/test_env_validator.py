"""Tests for environment validation."""
import os
import sys
from io import StringIO
from unittest.mock import patch

import pytest

from app.core.env_validator import EnvValidator


def test_validation_passes_with_required_vars():
    """Test that validation passes when required vars are set."""
    with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}, clear=True):
        # Should not raise or exit
        EnvValidator.validate()


def test_validation_noops_when_no_extra_vars_defined():
    """Validator should not exit when REQUIRED_VARS is empty."""
    with patch.dict(os.environ, {}, clear=True):
        # Should not raise or exit even if JWT_SECRET missing
        EnvValidator.validate()


def test_validation_still_handles_future_required_vars():
    """If REQUIRED_VARS is populated, missing values should trigger exit."""
    with patch.object(EnvValidator, "REQUIRED_VARS", ["SOME_REQUIRED"]), patch.dict(
        os.environ, {}, clear=True
    ):
        with pytest.raises(SystemExit) as exc_info:
            EnvValidator.validate()
        assert exc_info.value.code == 1
