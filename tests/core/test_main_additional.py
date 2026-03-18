import runpy
import sys
import types

import app.main as main_module


def test_root_and_info_handlers_return_expected_payload(monkeypatch):
    monkeypatch.setattr(main_module.config, "APP_ENV", "test")

    assert main_module.root() == {"service": "binder-billing-crm", "status": "running"}
    assert main_module.info() == {"app": "Binder Billing CRM", "env": "test"}


def test_main_module_invokes_uvicorn_run_in_dunder_main(monkeypatch):
    calls = {}

    def _run(app_path, host, port, reload):
        calls["app_path"] = app_path
        calls["host"] = host
        calls["port"] = port
        calls["reload"] = reload

    fake_uvicorn = types.SimpleNamespace(run=_run)
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    runpy.run_module("app.main", run_name="__main__")

    assert calls == {
        "app_path": "app.main:app",
        "host": "0.0.0.0",
        "port": main_module.config.PORT,
        "reload": True,
    }
