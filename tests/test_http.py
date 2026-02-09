"""Tests for the Gas & Water Meter HTTP upload API."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.gas_water_meter.const import DOMAIN
from custom_components.gas_water_meter.http import (
    UPLOAD_MAX_SIZE,
    ImageUploadView,
    _ext_from_content_type,
    _json_error,
    _json_response,
    _safe_remove,
)
from homeassistant.core import HomeAssistant

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockMultipartPart:
    """Simulate a single part in a multipart upload."""

    def __init__(self, name: str, data: bytes, content_type: str = "") -> None:
        self.name = name
        self._data = data
        self.headers = {"Content-Type": content_type} if content_type else {}

    async def read(self, decode: bool = True) -> bytes:
        return self._data

    async def text(self) -> str:
        return self._data.decode()


class MockMultipartReader:
    """Simulate an aiohttp multipart reader."""

    def __init__(self, parts: list[MockMultipartPart]) -> None:
        self._parts = list(parts)
        self._index = 0

    async def next(self) -> MockMultipartPart | None:
        if self._index >= len(self._parts):
            return None
        part = self._parts[self._index]
        self._index += 1
        return part


def _make_request(parts: list[MockMultipartPart] | None = None) -> MagicMock:
    """Create a mock aiohttp request with multipart reader."""
    request = MagicMock()
    if parts is not None:
        reader = MockMultipartReader(parts)
        request.multipart = AsyncMock(return_value=reader)
    else:
        request.multipart = AsyncMock(side_effect=Exception("Not multipart"))
    return request


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestJsonHelpers:
    """Tests for JSON response helpers."""

    def test_json_response_returns_200(self) -> None:
        resp = _json_response({"ok": True})
        assert resp.status == 200
        body = json.loads(resp.text)
        assert body["ok"] is True

    def test_json_response_custom_status(self) -> None:
        resp = _json_response({"created": True}, status=201)
        assert resp.status == 201

    def test_json_error_returns_error_message(self) -> None:
        resp = _json_error("Something failed", 400)
        assert resp.status == 400
        body = json.loads(resp.text)
        assert body["error"] == "Something failed"

    def test_json_error_413(self) -> None:
        resp = _json_error("Too large", 413)
        assert resp.status == 413


class TestExtFromContentType:
    """Tests for content type to extension mapping."""

    def test_jpeg(self) -> None:
        assert _ext_from_content_type("image/jpeg") == ".jpg"

    def test_png(self) -> None:
        assert _ext_from_content_type("image/png") == ".png"

    def test_heic(self) -> None:
        assert _ext_from_content_type("image/heic") == ".heic"

    def test_heif(self) -> None:
        assert _ext_from_content_type("image/heif") == ".heif"

    def test_with_charset(self) -> None:
        assert _ext_from_content_type("image/jpeg; charset=utf-8") == ".jpg"

    def test_unknown_type(self) -> None:
        assert _ext_from_content_type("application/pdf") is None

    def test_case_insensitive(self) -> None:
        assert _ext_from_content_type("Image/JPEG") == ".jpg"


class TestSafeRemove:
    """Tests for _safe_remove."""

    def test_removes_existing_file(self) -> None:
        fd, path = tempfile.mkstemp()
        os.close(fd)
        assert os.path.exists(path)
        _safe_remove(path)
        assert not os.path.exists(path)

    def test_ignores_nonexistent_file(self) -> None:
        _safe_remove("/nonexistent/file/that/does/not/exist.tmp")


# ---------------------------------------------------------------------------
# Tests for _read_upload
# ---------------------------------------------------------------------------


class TestReadUpload:
    """Tests for ImageUploadView._read_upload."""

    async def test_successful_upload(self, hass: HomeAssistant) -> None:
        view = ImageUploadView(hass)
        parts = [
            MockMultipartPart("file", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg"),
            MockMultipartPart("entry_id", b"test_entry_1"),
        ]
        request = _make_request(parts)
        content, entry_id, ext = await view._read_upload(request)
        assert isinstance(content, bytes)
        assert len(content) == 104
        assert entry_id == "test_entry_1"
        assert ext == ".jpg"

    async def test_missing_file_field(self, hass: HomeAssistant) -> None:
        view = ImageUploadView(hass)
        parts = [MockMultipartPart("entry_id", b"test_entry_1")]
        request = _make_request(parts)
        result, _, _ = await view._read_upload(request)
        # Should return an error response
        assert hasattr(result, "status")
        assert result.status == 400
        assert "No 'file' field" in result.text

    async def test_empty_file(self, hass: HomeAssistant) -> None:
        view = ImageUploadView(hass)
        parts = [
            MockMultipartPart("file", b"", "image/jpeg"),
            MockMultipartPart("entry_id", b"test_entry_1"),
        ]
        request = _make_request(parts)
        result, _, _ = await view._read_upload(request)
        assert result.status == 400
        assert "Empty file" in result.text

    async def test_file_too_large(self, hass: HomeAssistant) -> None:
        view = ImageUploadView(hass)
        large_content = b"\x00" * (UPLOAD_MAX_SIZE + 1)
        parts = [
            MockMultipartPart("file", large_content, "image/jpeg"),
            MockMultipartPart("entry_id", b"test_entry_1"),
        ]
        request = _make_request(parts)
        result, _, _ = await view._read_upload(request)
        assert result.status == 413
        assert "too large" in result.text

    async def test_invalid_multipart(self, hass: HomeAssistant) -> None:
        view = ImageUploadView(hass)
        request = _make_request(None)  # raises Exception on multipart()
        result, _, _ = await view._read_upload(request)
        assert result.status == 400
        assert "Invalid multipart" in result.text

    async def test_upload_without_entry_id(self, hass: HomeAssistant) -> None:
        view = ImageUploadView(hass)
        parts = [MockMultipartPart("file", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/png")]
        request = _make_request(parts)
        content, entry_id, ext = await view._read_upload(request)
        assert isinstance(content, bytes)
        assert entry_id is None
        assert ext == ".png"


# ---------------------------------------------------------------------------
# Tests for _save_to_temp
# ---------------------------------------------------------------------------


class TestSaveToTemp:
    """Tests for ImageUploadView._save_to_temp."""

    def test_creates_temp_file(self) -> None:
        content = b"\xff\xd8\xff\xe0test image data"
        path = ImageUploadView._save_to_temp(content, ".jpg")
        try:
            assert os.path.exists(path)
            assert path.endswith(".jpg")
            with open(path, "rb") as f:
                assert f.read() == content
        finally:
            os.unlink(path)

    def test_preserves_extension(self) -> None:
        path = ImageUploadView._save_to_temp(b"data", ".heic")
        try:
            assert path.endswith(".heic")
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Tests for _run_ocr
# ---------------------------------------------------------------------------


class TestRunOcr:
    """Tests for ImageUploadView._run_ocr."""

    async def test_returns_none_when_tesseract_unavailable(
        self, hass: HomeAssistant, mock_tesseract_unavailable
    ) -> None:
        view = ImageUploadView(hass)
        reading, meter_nr, conf = await view._run_ocr("/some/path.jpg")
        assert reading is None
        assert meter_nr is None
        assert conf == 0.0

    async def test_returns_ocr_result(self, hass: HomeAssistant, mock_tesseract_available) -> None:
        view = ImageUploadView(hass)
        mock_result = MagicMock()
        mock_result.meter_reading = 12345.678
        mock_result.meter_number = "GAS-001"
        mock_result.confidence = 0.9512

        with patch(
            "custom_components.gas_water_meter.http.read_meter_image",
            return_value=mock_result,
        ):
            reading, meter_nr, conf = await view._run_ocr("/some/path.jpg")

        assert reading == 12345.678
        assert meter_nr == "GAS-001"
        assert conf == 0.951

    async def test_handles_ocr_exception(self, hass: HomeAssistant, mock_tesseract_available) -> None:
        view = ImageUploadView(hass)
        with patch(
            "custom_components.gas_water_meter.http.read_meter_image",
            side_effect=RuntimeError("OCR crashed"),
        ):
            reading, meter_nr, conf = await view._run_ocr("/some/path.jpg")

        assert reading is None
        assert meter_nr is None
        assert conf == 0.0


# ---------------------------------------------------------------------------
# Tests for _process_image
# ---------------------------------------------------------------------------


class TestProcessImage:
    """Tests for ImageUploadView._process_image."""

    async def test_without_entry_id_returns_tmp_path(self, hass: HomeAssistant, mock_tesseract_unavailable) -> None:
        view = ImageUploadView(hass)
        with patch(
            "custom_components.gas_water_meter.http.extract_exif_datetime",
            return_value=None,
        ):
            result = await view._process_image("/tmp/test.jpg", None)

        assert result["image_path"] == "/tmp/test.jpg"
        assert result["exif_datetime"] is None
        assert result["ocr_reading"] is None
        assert result["ocr_available"] is False

    async def test_with_entry_id_persists_image(self, hass: HomeAssistant, mock_tesseract_unavailable) -> None:
        view = ImageUploadView(hass)
        mock_db = AsyncMock()
        mock_db.async_save_image = AsyncMock(return_value="/media/gas_water_meter/saved.jpg")
        hass.data[DOMAIN] = {"db": mock_db}

        with (
            patch(
                "custom_components.gas_water_meter.http.extract_exif_datetime",
                return_value="2026-01-15T10:00:00",
            ),
            patch("custom_components.gas_water_meter.http._safe_remove"),
        ):
            result = await view._process_image("/tmp/test.jpg", "entry_1")

        assert result["image_path"] == "/media/gas_water_meter/saved.jpg"
        assert result["exif_datetime"] == "2026-01-15T10:00:00"
        mock_db.async_save_image.assert_awaited_once()

    async def test_exif_datetime_extracted(self, hass: HomeAssistant, mock_tesseract_unavailable) -> None:
        view = ImageUploadView(hass)
        with patch(
            "custom_components.gas_water_meter.http.extract_exif_datetime",
            return_value="2026-03-01T14:30:00",
        ):
            result = await view._process_image("/tmp/test.jpg", None)

        assert result["exif_datetime"] == "2026-03-01T14:30:00"

    async def test_ocr_available_true_when_tesseract_installed(
        self, hass: HomeAssistant, mock_tesseract_available
    ) -> None:
        view = ImageUploadView(hass)
        mock_result = MagicMock()
        mock_result.meter_reading = 42.0
        mock_result.meter_number = "W-001"
        mock_result.confidence = 0.85

        with (
            patch(
                "custom_components.gas_water_meter.http.extract_exif_datetime",
                return_value=None,
            ),
            patch(
                "custom_components.gas_water_meter.http.read_meter_image",
                return_value=mock_result,
            ),
        ):
            result = await view._process_image("/tmp/test.jpg", None)

        assert result["ocr_available"] is True
        assert result["ocr_reading"] == 42.0

    async def test_ocr_available_false_when_tesseract_missing(
        self, hass: HomeAssistant, mock_tesseract_unavailable
    ) -> None:
        view = ImageUploadView(hass)
        with patch(
            "custom_components.gas_water_meter.http.extract_exif_datetime",
            return_value=None,
        ):
            result = await view._process_image("/tmp/test.jpg", None)

        assert result["ocr_available"] is False
        assert result["ocr_reading"] is None


# ---------------------------------------------------------------------------
# Tests for full post flow
# ---------------------------------------------------------------------------


class TestPostEndpoint:
    """Tests for ImageUploadView.post end-to-end."""

    async def test_successful_post(self, hass: HomeAssistant, mock_tesseract_unavailable) -> None:
        view = ImageUploadView(hass)
        parts = [
            MockMultipartPart("file", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg"),
        ]
        request = _make_request(parts)

        with patch(
            "custom_components.gas_water_meter.http.extract_exif_datetime",
            return_value=None,
        ):
            response = await view.post(request)

        assert response.status == 200
        body = json.loads(response.text)
        assert "image_path" in body
        # Clean up temp file
        _safe_remove(body["image_path"])

    async def test_post_with_processing_error(self, hass: HomeAssistant) -> None:
        view = ImageUploadView(hass)
        parts = [
            MockMultipartPart("file", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg"),
            MockMultipartPart("entry_id", b"test_entry_1"),
        ]
        request = _make_request(parts)

        with patch.object(view, "_process_image", side_effect=Exception("Boom")):
            response = await view.post(request)

        assert response.status == 500
        body = json.loads(response.text)
        assert "Internal error" in body["error"]

    async def test_post_invalid_request(self, hass: HomeAssistant) -> None:
        view = ImageUploadView(hass)
        request = _make_request(None)
        response = await view.post(request)
        assert response.status == 400
