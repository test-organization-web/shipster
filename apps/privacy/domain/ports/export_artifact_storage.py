from typing import Protocol

from apps.privacy.domain.entities import PrivacyDownloadableArtifact, PrivacyExportArtifact


class ExportArtifactStorage(Protocol):
    async def write_json_bytes(self, *, key: str, payload: bytes) -> PrivacyExportArtifact:
        """Store a JSON artifact and return its metadata."""

    async def open_for_download(self, key: str) -> PrivacyDownloadableArtifact:
        """Resolve a stored artifact for download (locator is adapter-defined)."""

    async def delete(self, key: str) -> None:
        """Delete an existing artifact if it still exists."""
