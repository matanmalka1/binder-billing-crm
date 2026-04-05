import os
from abc import ABC, abstractmethod
from typing import BinaryIO

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class StorageProvider(ABC):
    """Abstract storage provider for S3/GCS compatible storage."""

    @abstractmethod
    def upload(self, key: str, file_data: BinaryIO, content_type: str) -> str:
        """
        Upload file to storage.

        Args:
            key: Storage key/path
            file_data: File binary data
            content_type: MIME type

        Returns:
            Storage key for retrieval
        """

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete file from storage.

        Args:
            key: Storage key/path
        """

    @abstractmethod
    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generate a presigned URL for downloading a file.

        Args:
            key: Storage key/path
            expires_in: URL expiry in seconds (default: 1 hour)

        Returns:
            Presigned URL string
        """


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider for development/testing."""

    def __init__(self, base_path: str = "./storage"):
        self.base_path = os.path.realpath(base_path)
        os.makedirs(self.base_path, exist_ok=True)

    def _safe_path(self, key: str) -> str:
        """
        Resolve the absolute path for a storage key and verify it stays
        within base_path (guards against path-traversal attacks).
        """
        resolved = os.path.realpath(os.path.join(self.base_path, key))
        if not resolved.startswith(self.base_path + os.sep) and resolved != self.base_path:
            raise ValueError(f"Invalid storage key — path escapes base directory: {key!r}")
        return resolved

    def upload(self, key: str, file_data: BinaryIO, content_type: str) -> str:
        """Upload file to local storage."""
        file_path = self._safe_path(key)
        parent = os.path.dirname(file_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(file_data.read())

        logger.info("[LocalStorage] Uploaded: %s", key)
        return key

    def delete(self, key: str) -> None:
        """Delete file from local storage."""
        file_path = self._safe_path(key)
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info("[LocalStorage] Deleted: %s", key)
        else:
            logger.warning("[LocalStorage] Delete — file not found: %s", key)

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Return local file path as URL (dev only)."""
        return f"/local-storage/{key}"


class S3StorageProvider(StorageProvider):
    """
    S3-compatible storage provider.

    Works with AWS S3 and Cloudflare R2 (R2 is fully S3-compatible).

    Required config:
        access_key_id      — AWS_ACCESS_KEY_ID / R2 Access Key ID
        secret_access_key  — AWS_SECRET_ACCESS_KEY / R2 Secret Access Key
        bucket_name        — S3_BUCKET_NAME / R2 bucket name
        endpoint_url       — For R2: https://<account-id>.r2.cloudflarestorage.com
                             For AWS S3: leave as None
        region             — AWS region (default: auto, R2 ignores this)
    """

    def __init__(
        self,
        *,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        endpoint_url: str | None = None,
        region: str = "auto",
    ) -> None:
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise RuntimeError(
                "הספרייה boto3 נדרשת עבור S3StorageProvider. "
                "יש להתקין באמצעות: pip install boto3"
            )

        self._bucket = bucket_name
        self._endpoint_url = endpoint_url

        self._client = boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            endpoint_url=endpoint_url,
            region_name=region,
            config=Config(
                signature_version="s3v4",
                connect_timeout=5,
                read_timeout=30,
            ),
        )

        logger.info(
            "S3StorageProvider initialized | bucket=%s endpoint=%s",
            bucket_name,
            endpoint_url or "AWS default",
        )

    def upload(self, key: str, file_data: BinaryIO, content_type: str) -> str:
        """Upload file to S3/R2."""
        self._client.upload_fileobj(
            file_data,
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        logger.info("[S3Storage] Uploaded: %s → bucket=%s", key, self._bucket)
        return key

    def delete(self, key: str) -> None:
        """Delete file from S3/R2."""
        self._client.delete_object(Bucket=self._bucket, Key=key)
        logger.info("[S3Storage] Deleted: %s", key)

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generate a presigned URL for secure file download.

        Args:
            key: Storage key/path
            expires_in: Expiry in seconds (default: 1 hour)

        Returns:
            Presigned URL valid for `expires_in` seconds
        """
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        logger.info("[S3Storage] Presigned URL generated for: %s (expires_in=%ds)", key, expires_in)
        return url


def get_storage_provider() -> StorageProvider:
    """
    Factory — returns the correct StorageProvider based on config.

    - development / test → LocalStorageProvider
    - staging / production → S3StorageProvider (Cloudflare R2 or AWS S3)
    """
    from app.config import config

    if config.APP_ENV in ("development", "test"):
        logger.info("Storage: using LocalStorageProvider (env=%s)", config.APP_ENV)
        return LocalStorageProvider()

    # Validate required config for cloud storage
    missing = [
        var for var, val in {
            "R2_ACCESS_KEY_ID": config.R2_ACCESS_KEY_ID,
            "R2_SECRET_ACCESS_KEY": config.R2_SECRET_ACCESS_KEY,
            "R2_BUCKET_NAME": config.R2_BUCKET_NAME,
            "R2_ENDPOINT_URL": config.R2_ENDPOINT_URL,
        }.items()
        if not val
    ]
    if missing:
        raise RuntimeError(
            f"S3StorageProvider דורש שמשתני הסביבה הבאים יהיו מוגדרים: {', '.join(missing)}"
        )

    logger.info("Storage: using S3StorageProvider (env=%s)", config.APP_ENV)
    return S3StorageProvider(
        access_key_id=config.R2_ACCESS_KEY_ID,
        secret_access_key=config.R2_SECRET_ACCESS_KEY,
        bucket_name=config.R2_BUCKET_NAME,
        endpoint_url=config.R2_ENDPOINT_URL,
        region="auto",
    )
