import app.main as main_module


def test_root_and_info_handlers_return_expected_payload(monkeypatch):
    monkeypatch.setattr(main_module.settings, "APP_ENV", "test")

    assert main_module.root() == {"service": "binder-billing-crm", "status": "running"}
    assert main_module.info() == {"app": "Binder Billing CRM", "env": "test"}
