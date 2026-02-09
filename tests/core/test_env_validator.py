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


def test_validation_fails_on_missing_required_var():
    """Test that validation fails when required var is missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            EnvValidator.validate()
        
        assert exc_info.value.code == 1


def test_validation_fails_on_empty_required_var():
    """Test that validation fails when required var is empty."""
    with patch.dict(os.environ, {"JWT_SECRET": "  "}, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            EnvValidator.validate()
        
        assert exc_info.value.code == 1


def test_validation_prints_error_message():
    """Test that validation prints helpful error message."""
    with patch.dict(os.environ, {}, clear=True):
        stderr_capture = StringIO()
        
        with patch("sys.stderr", stderr_capture):
            with pytest.raises(SystemExit):
                EnvValidator.validate()
        
        error_output = stderr_capture.getvalue()
        assert "ENVIRONMENT VALIDATION FAILED" in error_output
        assert "JWT_SECRET" in error_output