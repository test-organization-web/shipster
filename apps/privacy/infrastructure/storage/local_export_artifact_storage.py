from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from apps.privacy.domain.entities import PrivacyDownloadableArtifact, PrivacyExportArtifact
from apps.privacy.domain.ports.export_artifact_storage import ExportArtifactStorage

_LOG = logging.getLogger(__name__)


class LocalExportArtifactStorage(ExportArtifactStorage):
    """Store durable privacy export artifacts on local disk."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir.resolve()

    def _path_for_key(self, key: str) -> Path:
        return self._base_dir / f"{key}.json"

    async def write_json_bytes(self, *, key: str, payload: bytes) -> PrivacyExportArtifact:
        path = self._path_for_key(key)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, payload)
        _LOG.debug(
            "privacy export storage: wrote artifact",
            extra={"artifact_key": key, "size_bytes": len(payload)},
        )
        return PrivacyExportArtifact(
            key=key,
            filename=f"{key}.json",
            media_type="application/json",
            size_bytes=len(payload),
        )

    async def open_for_download(self, key: str) -> PrivacyDownloadableArtifact:
        path = self._path_for_key(key)
        try:
            stat_result = await asyncio.to_thread(path.stat)
        except FileNotFoundError as exc:
            raise FileNotFoundError(str(path)) from exc
        if not path.is_file() or stat_result.st_size <= 0:
            raise FileNotFoundError(str(path))
        return PrivacyDownloadableArtifact(
            locator=str(path),
            media_type="application/json",
        )

    async def delete(self, key: str) -> None:
        path = self._path_for_key(key)
        try:
            await asyncio.to_thread(path.unlink)
            _LOG.debug("privacy export storage: deleted artifact", extra={"artifact_key": key})
        except FileNotFoundError:
            _LOG.debug(
                "privacy export storage: delete skipped (already absent)",
                extra={"artifact_key": key},
            )
