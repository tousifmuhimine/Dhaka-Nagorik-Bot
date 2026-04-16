"""Storage backends for Supabase-hosted media and generated documents."""

from __future__ import annotations

import mimetypes
import posixpath
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from typing import cast

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from supabase import create_client
from storage3.types import CreateOrUpdateBucketOptions, FileOptions


@deconstructible
class SupabaseStorage(Storage):
    """Django storage backend backed by a Supabase Storage bucket."""

    _bucket_cache: set[str] = set()

    def __init__(self, bucket_name: str, base_path: str = ""):
        self.bucket_name = bucket_name
        self.base_path = (base_path or "").strip().strip("/")

    def _client(self):
        return create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )

    def _bucket(self):
        self._ensure_bucket_exists()
        return self._client().storage.from_(self.bucket_name)

    def _ensure_bucket_exists(self):
        if self.bucket_name in self._bucket_cache:
            return

        storage_api = self._client().storage
        try:
            storage_api.get_bucket(self.bucket_name)
        except Exception:
            bucket_options: CreateOrUpdateBucketOptions = {"public": False}
            storage_api.create_bucket(
                self.bucket_name,
                options=bucket_options,
            )
        self._bucket_cache.add(self.bucket_name)

    def _normalize_name(self, name: str) -> str:
        clean_name = str(name or "").replace("\\", "/").lstrip("/")
        if self.base_path:
            return posixpath.join(self.base_path, clean_name)
        return clean_name

    def _strip_base_path(self, name: str) -> str:
        clean_name = str(name or "").replace("\\", "/").lstrip("/")
        if self.base_path and clean_name.startswith(f"{self.base_path}/"):
            return clean_name[len(self.base_path) + 1:]
        return clean_name

    def _save(self, name, content):
        logical_name = self.get_available_name(self._strip_base_path(name))
        object_name = self._normalize_name(logical_name)

        if hasattr(content, "seek"):
            content.seek(0)
        payload = content.read()
        if isinstance(payload, str):
            payload = payload.encode("utf-8")

        content_type = getattr(content, "content_type", None) or mimetypes.guess_type(logical_name)[0]
        resolved_content_type = (
            content_type
            if isinstance(content_type, str) and content_type
            else "application/octet-stream"
        )
        file_options: FileOptions = {"content-type": resolved_content_type}
        self._bucket().upload(object_name, payload, file_options=file_options)
        return logical_name

    def _open(self, name, mode="rb"):
        data = self._bucket().download(self._normalize_name(name))
        return File(BytesIO(data), name=self._strip_base_path(name))

    def delete(self, name):
        self._bucket().remove([self._normalize_name(name)])

    def exists(self, name):
        object_name = self._normalize_name(name)
        folder, filename = posixpath.split(object_name)
        try:
            entries: list[object] = list(self._bucket().list(folder or None))
        except Exception:
            return False

        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            item = cast(Mapping[str, object], entry)
            if item.get("name") == filename:
                return True
        return False

    def size(self, name):
        object_name = self._normalize_name(name)
        folder, filename = posixpath.split(object_name)
        try:
            entries: list[object] = list(self._bucket().list(folder or None))
        except Exception:
            return 0
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            item = cast(Mapping[str, object], entry)
            if item.get("name") == filename:
                metadata = item.get("metadata")
                if isinstance(metadata, Mapping):
                    size = metadata.get("size", 0)
                else:
                    size = 0
                return int(size or 0)
        return 0

    def url(self, name):
        signed = self._bucket().create_signed_url(
            self._normalize_name(name),
            expires_in=settings.SUPABASE_STORAGE_SIGNED_URL_TTL,
        )
        return signed["signedURL"]

    def path(self, name):
        raise NotImplementedError("Supabase-backed files do not have a local filesystem path.")


def build_document_storage():
    """Return the storage backend used for generated complaint documents."""
    if settings.USE_SUPABASE_STORAGE:
        return SupabaseStorage(
            bucket_name=settings.SUPABASE_DOCUMENT_BUCKET,
            base_path="",
        )

    from django.core.files.storage import FileSystemStorage

    return FileSystemStorage(location=str(settings.DOCUMENT_OUTPUT_DIR))


def legacy_local_document_path(name: str) -> Path | None:
    """Return a legacy absolute document path if one is stored in the database."""
    if not name:
        return None

    candidate = Path(name)
    if candidate.is_absolute():
        try:
            resolved = candidate.resolve()
            allowed_root = Path(settings.DOCUMENT_OUTPUT_DIR).resolve()
        except FileNotFoundError:
            return None

        if allowed_root in resolved.parents or resolved == allowed_root:
            return resolved
    return None
