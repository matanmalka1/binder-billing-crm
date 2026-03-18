import builtins
import importlib

import pytest

import app.config as config_mod
from app.core.exceptions import AppError


def _restore_config_module(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    importlib.reload(config_mod)


def test_config_raises_when_jwt_secret_missing(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("ENV_FILE", raising=False)

    original_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name == "dotenv":
            raise ImportError("dotenv missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)

    with pytest.raises(AppError) as exc_info:
        importlib.reload(config_mod)

    assert exc_info.value.code == "CONFIG.JWT_SECRET_MISSING"
    _restore_config_module(monkeypatch)


def test_config_import_handles_missing_dotenv_dependency(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    original_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name == "dotenv":
            raise ImportError("dotenv missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)
    importlib.reload(config_mod)

    assert config_mod.load_dotenv is None

    _restore_config_module(monkeypatch)


def test_load_env_files_uses_env_file_when_provided(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("ENV_FILE", "/tmp/custom.env")

    captured = {}

    def _fake_load_dotenv(*, dotenv_path, override):
        captured["dotenv_path"] = str(dotenv_path)
        captured["override"] = override

    monkeypatch.setattr(config_mod, "load_dotenv", _fake_load_dotenv)
    config_mod._load_env_files()

    assert captured["dotenv_path"] == "/tmp/custom.env"
    assert captured["override"] is False
