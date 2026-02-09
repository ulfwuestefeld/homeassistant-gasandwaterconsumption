"""REST API for photo upload in Gas & Water Meter integration."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .db import MeterDatabase
from .ocr import extract_exif_datetime, is_tesseract_available, read_meter_image

_LOGGER = logging.getLogger(__name__)

UPLOAD_MAX_SIZE = 20 * 1024 * 1024  # 20 MB


class ImageUploadView(HomeAssistantView):
    """Handle image uploads for meter reading OCR."""

    url = f"/api/{DOMAIN}/upload_image"
    name = f"api:{DOMAIN}:upload_image"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self._hass = hass

    async def post(self, request: web.Request) -> web.Response:
        """Handle POST with multipart image upload."""
        content, entry_id, ext = await self._read_upload(request)
        if isinstance(content, web.Response):
            return content  # Error response

        tmp_path = self._save_to_temp(content, ext)
        try:
            result = await self._process_image(tmp_path, entry_id)
            return _json_response(result)
        except Exception:
            _LOGGER.exception("Error processing uploaded image")
            return _json_error("Internal error processing image", 500)
        finally:
            # Clean temp file only if it still exists and was already persisted
            if entry_id:
                _safe_remove(tmp_path)

    async def _read_upload(
        self, request: web.Request
    ) -> tuple[bytes, str | None, str] | tuple[web.Response, None, str]:
        """Parse multipart upload and return (content, entry_id, ext) or (error_response, None, '')."""
        try:
            reader = await request.multipart()
        except Exception:
            return _json_error("Invalid multipart request", 400), None, ""

        file_content: bytes | None = None
        entry_id: str | None = None
        ext = ".jpg"

        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == "file":
                file_content = await part.read(decode=False)
                ct = part.headers.get("Content-Type", "")
                ext = _ext_from_content_type(ct) or ".jpg"
            elif part.name == "entry_id":
                entry_id = (await part.text()).strip()

        if file_content is None:
            return _json_error("No 'file' field in upload", 400), None, ""
        if len(file_content) > UPLOAD_MAX_SIZE:
            return _json_error("File too large (max 20 MB)", 413), None, ""
        if not file_content:
            return _json_error("Empty file", 400), None, ""

        return file_content, entry_id, ext

    @staticmethod
    def _save_to_temp(content: bytes, ext: str) -> str:
        """Write content to a temp file and return the path."""
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext)
        os.write(tmp_fd, content)
        os.close(tmp_fd)
        return tmp_path

    async def _process_image(self, tmp_path: str, entry_id: str | None) -> dict[str, Any]:
        """Extract EXIF/OCR data and optionally persist the image."""
        hass = self._hass

        exif_dt = await hass.async_add_executor_job(extract_exif_datetime, tmp_path)

        ocr_reading, ocr_meter_number, ocr_confidence = await self._run_ocr(tmp_path)

        image_path = tmp_path
        if entry_id:
            image_path = await self._persist_image(tmp_path, entry_id, exif_dt)

        return {
            "image_path": image_path,
            "exif_datetime": exif_dt,
            "ocr_available": is_tesseract_available(),
            "ocr_reading": ocr_reading,
            "ocr_meter_number": ocr_meter_number,
            "ocr_confidence": ocr_confidence,
        }

    async def _run_ocr(self, image_path: str) -> tuple[float | None, str | None, float]:
        """Run OCR on the image. Returns (reading, meter_number, confidence)."""
        if not is_tesseract_available():
            return None, None, 0.0
        try:
            ocr_result = await self._hass.async_add_executor_job(read_meter_image, image_path)
            return (
                ocr_result.meter_reading,
                ocr_result.meter_number,
                round(ocr_result.confidence, 3),
            )
        except Exception:
            _LOGGER.warning("OCR failed for uploaded image", exc_info=True)
            return None, None, 0.0

    async def _persist_image(self, tmp_path: str, entry_id: str, exif_dt: str | None) -> str:
        """Move uploaded image to persistent storage."""
        from datetime import UTC, datetime  # noqa: PLC0415

        db: MeterDatabase = self._hass.data[DOMAIN]["db"]
        ts = exif_dt or datetime.now(tz=UTC).isoformat()
        saved_path = await db.async_save_image(tmp_path, entry_id, ts)
        _safe_remove(tmp_path)
        return saved_path


def _json_response(data: dict[str, Any], status: int = 200) -> web.Response:
    """Return a JSON response."""
    return web.Response(
        text=json.dumps(data),
        content_type="application/json",
        status=status,
    )


def _json_error(message: str, status: int) -> web.Response:
    """Return a JSON error response."""
    return web.Response(
        text=json.dumps({"error": message}),
        content_type="application/json",
        status=status,
    )


def _ext_from_content_type(ct: str) -> str | None:
    """Map content type to file extension."""
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/tiff": ".tiff",
        "image/heic": ".heic",
        "image/heif": ".heif",
        "image/heif-sequence": ".heif",
        "image/heic-sequence": ".heic",
    }
    return mapping.get(ct.split(";", maxsplit=1)[0].strip().lower())


def _safe_remove(path: str) -> None:
    """Remove a file, ignoring errors."""
    with contextlib.suppress(OSError):
        os.unlink(path)
