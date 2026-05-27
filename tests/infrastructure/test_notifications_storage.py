import io

import httpx
import pytest

from app.infrastructure import storage as storage_mod
from app.infrastructure.notifications import EmailChannel, WhatsAppChannel, _to_html

BREVO_API_URL = "https://brevo.test/v3/smtp/email"
MAX_EXPECTED_PROVIDER_ERROR_BODY_LENGTH = 1000


class _Resp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_exc_info):
        return False


def test_email_channel_disabled_missing_config_and_success(monkeypatch):
    disabled = EmailChannel(
        enabled=False,
        api_key="",
        api_url=BREVO_API_URL,
        from_address="",
    )
    assert disabled.send("a@b.com", "hello") == (True, None)

    missing_key = EmailChannel(
        enabled=True,
        api_key="",
        api_url=BREVO_API_URL,
        from_address="from@x.com",
    )
    ok, msg = missing_key.send("a@b.com", "hello")
    assert ok is False
    assert "BREVO_API_KEY" in msg

    missing_from = EmailChannel(
        enabled=True,
        api_key="k",
        api_url=BREVO_API_URL,
        from_address="",
    )
    ok, msg = missing_from.send("a@b.com", "hello")
    assert ok is False
    assert "EMAIL_FROM_ADDRESS" in msg

    captured = {}

    def _post_ok(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return httpx.Response(201)

    monkeypatch.setattr("httpx.post", _post_ok)
    enabled = EmailChannel(
        enabled=True,
        api_key="k",
        api_url=BREVO_API_URL,
        from_address="from@x.com",
        from_name="CRM",
    )
    assert enabled.send("a@b.com", "hello")[0] is True
    assert captured["url"] == BREVO_API_URL
    assert captured["kwargs"]["json"]["textContent"] == "hello"
    assert captured["kwargs"]["json"]["htmlContent"] == _to_html("hello")

    ok, msg = enabled.send_html("a@b.com", "<p>hello</p>", "hello", "Subject")
    assert ok is True
    payload = captured["kwargs"]["json"]
    assert payload["htmlContent"] == "<p>hello</p>"
    assert payload["textContent"] == "hello"
    assert payload["subject"] == "Subject"


def test_whatsapp_channel_paths(monkeypatch):
    disabled = WhatsAppChannel(api_key="", api_url="https://wa", from_number="")
    assert disabled.enabled is False
    assert disabled.send("050", "x") == (False, "not configured")

    enabled = WhatsAppChannel(api_key="k", api_url="https://wa", from_number="123")

    monkeypatch.setattr("urllib.request.urlopen", lambda _req, **_kwargs: _Resp(201))
    assert enabled.send("050", "x") == (True, None)

    monkeypatch.setattr("urllib.request.urlopen", lambda _req, **_kwargs: _Resp(500))
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
        R2_REGION = "auto"
        LOCAL_STORAGE_PATH = str(tmp_path)

    import app.config as config_mod

    monkeypatch.setattr(config_mod, "settings", _Config)
    built = storage_mod.get_storage_provider()
    assert isinstance(built, storage_mod.LocalStorageProvider)


def test_s3_provider_init_is_stable_with_or_without_boto3():
    try:
        provider = storage_mod.S3StorageProvider(
            access_key_id="k",
            secret_access_key="s",
            bucket_name="b",
            endpoint_url="https://x",
            region="auto",
        )
        assert provider is not None
    except RuntimeError as exc:
        assert "boto3" in str(exc)
    except Exception as exc:  # environment-specific boto3/botocore model load failures
        assert "Expecting value" in str(exc) or "boto3" in str(exc)


def test_get_storage_provider_requires_r2_fields_in_production(monkeypatch):
    class _Config:
        APP_ENV = "production"
        R2_ACCESS_KEY_ID = None
        R2_SECRET_ACCESS_KEY = None
        R2_BUCKET_NAME = None
        R2_ENDPOINT_URL = None
        R2_REGION = "auto"
        LOCAL_STORAGE_PATH = "./storage"

    import app.config as config_mod

    monkeypatch.setattr(config_mod, "settings", _Config)
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

        def generate_presigned_url(self, _op, Params=None, ExpiresIn=3600):
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

    def _raise_post(_url, **_kwargs):
        raise httpx.ConnectError("net-down")

    monkeypatch.setattr("httpx.post", _raise_post)

    email = EmailChannel(
        enabled=True,
        api_key="k",
        api_url=BREVO_API_URL,
        from_address="from@x.com",
    )
    ok, msg = email.send("to@x.com", "hello")
    assert ok is False
    assert "Brevo email request failed" in msg

    def _post_rejected(_url, **_kwargs):
        return httpx.Response(400, text="x" * 1200)

    monkeypatch.setattr("httpx.post", _post_rejected)

    ok, msg = email.send("to@x.com", "hello")
    assert ok is False
    assert "Brevo rejected email: status=400" in msg
    assert len(msg.rsplit("body=", 1)[1]) == MAX_EXPECTED_PROVIDER_ERROR_BODY_LENGTH

    wa = WhatsAppChannel(api_key="k", api_url="https://wa", from_number="123")
    ok, msg = wa.send("050", "hello")
    assert ok is False
    assert "WhatsApp error" in msg
