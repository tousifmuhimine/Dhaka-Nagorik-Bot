"""Helpers for storing and retrieving generated complaint documents."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.core.files.base import ContentFile

from complaints.storage_backends import build_document_storage, legacy_local_document_path


class DocumentStorageService:
    """Unified access to generated complaint documents across storage backends."""

    def __init__(self):
        self.storage = build_document_storage()

    def save_bytes(self, name: str, content: bytes) -> str:
        """Persist a generated document and return its stored key."""
        return self.storage.save(name, ContentFile(content))

    def read_bytes(self, name: str) -> bytes:
        """Read stored document bytes from Supabase or the legacy local path."""
        legacy_path = legacy_local_document_path(name)
        if legacy_path and legacy_path.exists():
            return legacy_path.read_bytes()

        with self.storage.open(name, "rb") as handle:
            return handle.read()

    def open_legacy_or_storage(self, name: str):
        """Open a generated document from storage or a legacy absolute path."""
        legacy_path = legacy_local_document_path(name)
        if legacy_path and legacy_path.exists():
            return legacy_path.open("rb")
        return self.storage.open(name, "rb")

    def exists(self, name: str) -> bool:
        """Return whether the named document exists."""
        legacy_path = legacy_local_document_path(name)
        if legacy_path and legacy_path.exists():
            return True
        return self.storage.exists(name)

    def filename(self, name: str) -> str:
        """Return the download filename for a stored document key/path."""
        return Path(name).name

    def guess_mime_type(self, name: str) -> str:
        """Infer a MIME type from the stored file name."""
        return mimetypes.guess_type(name)[0] or "application/octet-stream"
