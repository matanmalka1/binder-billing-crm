from abc import ABC, abstractmethod
from typing import BinaryIO


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
        pass


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider for development/testing."""

    def __init__(self, base_path: str = "./storage"):
        self.base_path = base_path
        import os
        os.makedirs(base_path, exist_ok=True)

    def upload(self, key: str, file_data: BinaryIO, content_type: str) -> str:
        """Upload file to local storage."""
        import os

        file_path = os.path.join(self.base_path, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(file_data.read())

        return key