"""
LiRA Backend — Storage Abstraction
Local filesystem and S3-compatible (R2) storage backends.
"""

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from app.core.config import get_settings


class StorageBackend(ABC):
    """Abstract storage interface for artifact files."""

    @abstractmethod
    def save(self, run_id: str, filename: str, content: bytes) -> str:
        """Save file and return storage path."""
        ...

    @abstractmethod
    def save_from_path(self, run_id: str, filename: str, source_path: str) -> str:
        """Copy file from source path to storage and return storage path."""
        ...

    @abstractmethod
    def load(self, storage_path: str) -> bytes:
        """Load file content from storage path."""
        ...

    @abstractmethod
    def exists(self, storage_path: str) -> bool:
        """Check if file exists at storage path."""
        ...

    @abstractmethod
    def list_files(self, run_id: str) -> List[str]:
        """List all files for a run."""
        ...

    @abstractmethod
    def get_url(self, storage_path: str) -> str:
        """Get a URL (or local path) to access the file."""
        ...

    @abstractmethod
    def delete(self, storage_path: str) -> None:
        """Delete a file from storage."""
        ...


class LocalStorage(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, root_dir: Optional[str] = None):
        settings = get_settings()
        self.root = Path(root_dir or settings.STORAGE_LOCAL_ROOT).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id: str) -> Path:
        d = self.root / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save(self, run_id: str, filename: str, content: bytes) -> str:
        path = self._run_dir(run_id) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)

    def save_from_path(self, run_id: str, filename: str, source_path: str) -> str:
        dest = self._run_dir(run_id) / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest)
        return str(dest)

    def load(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()

    def exists(self, storage_path: str) -> bool:
        return Path(storage_path).exists()

    def list_files(self, run_id: str) -> List[str]:
        run_dir = self._run_dir(run_id)
        return [str(f) for f in run_dir.rglob("*") if f.is_file()]

    def get_url(self, storage_path: str) -> str:
        return storage_path  # Local path for dev

    def delete(self, storage_path: str) -> None:
        p = Path(storage_path)
        if p.exists():
            p.unlink()


class S3Storage(StorageBackend):
    """S3-compatible storage backend (AWS S3 / Cloudflare R2)."""

    def __init__(self):
        import boto3
        settings = get_settings()
        self.bucket_name = settings.S3_BUCKET_NAME

        session_kwargs = {}
        client_kwargs = {}

        if settings.S3_ENDPOINT_URL:
            client_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL

        if settings.S3_ACCESS_KEY_ID:
            session_kwargs["aws_access_key_id"] = settings.S3_ACCESS_KEY_ID
            session_kwargs["aws_secret_access_key"] = settings.S3_SECRET_ACCESS_KEY

        if settings.S3_REGION:
            session_kwargs["region_name"] = settings.S3_REGION

        session = boto3.Session(**session_kwargs)
        self.s3 = session.client("s3", **client_kwargs)

    def _key(self, run_id: str, filename: str) -> str:
        return f"runs/{run_id}/{filename}"

    def save(self, run_id: str, filename: str, content: bytes) -> str:
        key = self._key(run_id, filename)
        self.s3.put_object(Bucket=self.bucket_name, Key=key, Body=content)
        return key

    def save_from_path(self, run_id: str, filename: str, source_path: str) -> str:
        key = self._key(run_id, filename)
        self.s3.upload_file(source_path, self.bucket_name, key)
        return key

    def load(self, storage_path: str) -> bytes:
        response = self.s3.get_object(Bucket=self.bucket_name, Key=storage_path)
        return response["Body"].read()

    def exists(self, storage_path: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=storage_path)
            return True
        except Exception:
            return False

    def list_files(self, run_id: str) -> List[str]:
        prefix = f"runs/{run_id}/"
        response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
        return [obj["Key"] for obj in response.get("Contents", [])]

    def get_url(self, storage_path: str) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": storage_path},
            ExpiresIn=3600,
        )

    def delete(self, storage_path: str) -> None:
        self.s3.delete_object(Bucket=self.bucket_name, Key=storage_path)


def get_storage() -> StorageBackend:
    """Factory for the configured storage backend."""
    settings = get_settings()
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage()
    return LocalStorage()
