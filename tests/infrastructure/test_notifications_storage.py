import io

import pytest

from app.infrastructure.notifications import EmailChannel, WhatsAppChannel
from app.infrastructure.notifications import _to_html
from app.infrastructure import storage as storage_mod


class _Resp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_email_channel_disabled_missing_config_and_success(monkeypatch):
    disabled = EmailChannel(enabled=False, api_key="", from_address="")
    assert disabled.send("a@b.com", "hello") == (True, None)

    missing_key = EmailChannel(enabled=True, api_key="", from_address="from@x.com")
    ok, msg = missing_key.send("a@b.com", "hello")
    assert ok is False
    assert "SENDGRID_API_KEY" in msg

    missing_from = EmailChannel(enabled=True, api_key="k", from_address="")
    ok, msg = missing_from.send("a@b.com", "hello")
    assert ok is False
    assert "EMAIL_FROM_ADDRESS" in msg

    def _urlopen_ok(req, timeout=10):
        return _Resp(202)

    monkeypatch.setattr("urllib.request.urlopen", _urlopen_ok)
    enabled = EmailChannel(enabled=True, api_key="k", from_address="from@x.com", from_name="CRM")
    assert enabled.send("a@b.com", "hello")[0] is True


def test_whatsapp_channel_paths(monkeypatch):
    disabled = WhatsAppChannel(api_key="", api_url="https://wa", from_number="")
    assert disabled.enabled is False
    assert disabled.send("050", "x") == (False, "not configured")

    enabled = WhatsAppChannel(api_key="k", api_url="https://wa", from_number="123")

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=10: _Resp(201))
    assert enabled.send("050", "x") == (True, None)

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=10: _Resp(500))
    ok, msg = enabled.send("050", "x")
    assert ok is False
    assert "Unexpected WhatsApp status" in msg


def test_local_storage_and_provider_factory(monkeypatch, tmp_path):
    provider = storage_mod.LocalStorageProvider(base_path=str(tmp_path))
    key = provider.upload("a/b.txt", io.BytesIO(b"data"), "text/plain")
    assert key == "a/b.txt"
    assert provider.get_presigned_url(key).endswith(key)
    provider.delete(key)
    provider.delete("missing.txt")

    class _Config:
        APP_ENV = "development"
        R2_ACCESS_KEY_ID = None
        R2_SECRET_ACCESS_KEY = None
        R2_BUCKET_NAME = None
        R2_ENDPOINT_URL = None

    import app.config as config_mod

    monkeypatch.setattr(config_mod, "config", _Config)
    built = storage_mod.get_storage_provider()
    assert isinstance(built, storage_mod.LocalStorageProvider)


def test_s3_provider_init_is_stable_with_or_without_boto3():
    try:
        provider = storage_mod.S3StorageProvider(
            access_key_id="k",
            secret_access_key="s",
            bucket_name="b",
            endpoint_url="https://x",
        )
        assert provider is not None
    except RuntimeError as exc:
        assert "boto3" in str(exc)


def test_get_storage_provider_requires_r2_fields_in_production(monkeypatch):
    class _Config:
        APP_ENV = "production"
        R2_ACCESS_KEY_ID = None
        R2_SECRET_ACCESS_KEY = None
        R2_BUCKET_NAME = None
        R2_ENDPOINT_URL = None

    import app.config as config_mod

    monkeypatch.setattr(config_mod, "config", _Config)
    with pytest.raises(RuntimeError):
        storage_mod.get_storage_provider()


def test_s3_provider_upload_delete_and_presigned(monkeypatch):
    class _FakeClient:
        def __init__(self):
            self.uploaded = None
            self.deleted = None

        def upload_fileobj(self, fileobj, bucket, key, ExtraArgs=None):
            self.uploaded = (bucket, key, fileobj.read(), ExtraArgs)

        def delete_object(self, Bucket, Key):
            self.deleted = (Bucket, Key)

        def generate_presigned_url(self, op, Params=None, ExpiresIn=3600):
            return f"https://example/{Params['Bucket']}/{Params['Key']}?exp={ExpiresIn}"

    class _Provider(storage_mod.S3StorageProvider):
        def __init__(self):
            self._bucket = "bucket"
            self._endpoint_url = "https://x"
            self._client = _FakeClient()

    provider = _Provider()
    key = provider.upload("a/b.txt", io.BytesIO(b"abc"), "text/plain")
    provider.delete("a/b.txt")
    url = provider.get_presigned_url("a/b.txt", expires_in=120)

    assert key == "a/b.txt"
    assert provider._client.uploaded[0:2] == ("bucket", "a/b.txt")
    assert provider._client.deleted == ("bucket", "a/b.txt")
    assert "exp=120" in url


def test_notification_helpers_html_and_channel_exceptions(monkeypatch):
    html = _to_html("line1\n\nline2")
    assert "<p>line1</p>" in html
    assert "<br>" in html

    def _raise_urlopen(req, timeout=10):
        raise RuntimeError("net-down")

    monkeypatch.setattr("urllib.request.urlopen", _raise_urlopen)

    email = EmailChannel(enabled=True, api_key="k", from_address="from@x.com")
    ok, msg = email.send("to@x.com", "hello")
    assert ok is False
    assert "SendGrid error" in msg

    wa = WhatsAppChannel(api_key="k", api_url="https://wa", from_number="123")
    ok, msg = wa.send("050", "hello")
    assert ok is False
    assert "WhatsApp error" in msg
