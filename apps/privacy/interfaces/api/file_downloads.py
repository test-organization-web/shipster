import os
import tempfile

from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from apps.privacy.application.create_data_export import DirectDataExportResult
from apps.privacy.application.download_data_export import DownloadableExport


def build_direct_export_response(result: DirectDataExportResult) -> FileResponse:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    try:
        handle.write(result.payload)
        handle.flush()
        temp_path = handle.name
    finally:
        handle.close()

    return FileResponse(
        path=temp_path,
        filename=result.filename,
        media_type=result.media_type,
        background=BackgroundTask(os.unlink, temp_path),
        headers={"X-Privacy-Export-Request-Id": str(result.request_id)},
    )


def build_download_response(downloadable: DownloadableExport) -> FileResponse:
    return FileResponse(
        path=downloadable.locator,
        filename=downloadable.filename,
        media_type=downloadable.media_type,
    )
