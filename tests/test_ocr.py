"""Tests for the Gas & Water Meter OCR module."""

from __future__ import annotations

import tempfile
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from custom_components.gas_water_meter.http import _ext_from_content_type
from custom_components.gas_water_meter.ocr import (
    OcrResult,
    extract_exif_datetime,
    extract_meter_number,
    extract_meter_reading,
    preprocess_image,
)
from PIL import Image


class TestExtractMeterReading:
    """Tests for meter reading extraction from OCR text."""

    def test_simple_decimal(self) -> None:
        """Test extraction of simple decimal number."""
        assert extract_meter_reading("1234.567") == 1234.567

    def test_comma_decimal(self) -> None:
        """Test extraction with comma as decimal separator."""
        assert extract_meter_reading("1234,567") == 1234.567

    def test_integer_reading(self) -> None:
        """Test extraction of integer reading (4+ digits)."""
        assert extract_meter_reading("12345") == 12345.0

    def test_reading_with_spaces(self) -> None:
        """Test extraction of reading with spaces between digits."""
        assert extract_meter_reading("1 234.567") == 1234.567

    def test_reading_in_context(self) -> None:
        """Test extraction of reading from text with context."""
        text = "Meter reading: 1234.567 m3"
        result = extract_meter_reading(text)
        assert result is not None
        assert abs(result - 1234.567) < 0.001

    def test_multiple_numbers_picks_longest(self) -> None:
        """Test that the longest number is selected (most likely meter reading)."""
        text = "Type: gas\n12345.678\nDate 2026"
        result = extract_meter_reading(text)
        assert result is not None
        assert abs(result - 12345.678) < 0.001

    def test_no_numbers(self) -> None:
        """Test extraction from text without numbers."""
        assert extract_meter_reading("no numbers here") is None

    def test_empty_string(self) -> None:
        """Test extraction from empty string."""
        assert extract_meter_reading("") is None

    def test_short_numbers_ignored(self) -> None:
        """Test that short numbers (< 4 digits) without decimal are ignored."""
        # Only integers with 4+ digits or decimal numbers are matched
        assert extract_meter_reading("42") is None

    def test_reading_with_noise(self) -> None:
        """Test extraction from noisy OCR text."""
        text = "|||  1234.567  |||"
        result = extract_meter_reading(text)
        assert result is not None
        assert abs(result - 1234.567) < 0.001


class TestExtractMeterNumber:
    """Tests for meter number extraction from OCR text."""

    def test_nr_label(self) -> None:
        """Test extraction with 'Nr' label."""
        assert extract_meter_number("Nr: ABC-12345") == "ABC-12345"

    def test_nummer_label(self) -> None:
        """Test extraction with 'Nummer' label."""
        assert extract_meter_number("Nummer: 12345-678") == "12345-678"

    def test_zaehler_label(self) -> None:
        """Test extraction with 'Zähler' label."""
        assert extract_meter_number("Zähler: GAS-99887") == "GAS-99887"

    def test_zaehlernr_label(self) -> None:
        """Test extraction with 'Zählernr' label."""
        assert extract_meter_number("Zählernr 12345ABC") == "12345ABC"

    def test_meter_label(self) -> None:
        """Test extraction with 'Meter' label."""
        assert extract_meter_number("Meter: WAT-12345") == "WAT-12345"

    def test_serial_label(self) -> None:
        """Test extraction with 'Serial' label."""
        assert extract_meter_number("Serial: SN123456") == "SN123456"

    def test_no_label(self) -> None:
        """Test extraction when no label is present."""
        assert extract_meter_number("just some random text 12345") is None

    def test_empty_string(self) -> None:
        """Test extraction from empty string."""
        assert extract_meter_number("") is None

    def test_case_insensitive(self) -> None:
        """Test that label matching is case-insensitive."""
        assert extract_meter_number("NR: ABC-12345") == "ABC-12345"
        assert extract_meter_number("nr: ABC-12345") == "ABC-12345"

    def test_with_colon_or_dot(self) -> None:
        """Test labels with different separators."""
        assert extract_meter_number("Nr. ABC-12345") == "ABC-12345"
        assert extract_meter_number("Nr; ABC-12345") == "ABC-12345"


class TestExtractExifDatetime:
    """Tests for EXIF datetime extraction from images."""

    def _create_jpeg_with_exif(self, exif_tag_id: int, value: str, *, use_ifd: bool = True) -> str:
        """Create a temporary JPEG file with a specific EXIF tag and return its path."""
        img = Image.new("RGB", (100, 100), color="white")
        exif = img.getexif()

        if use_ifd:
            # Set tag in the ExifIFD sub-directory (0x8769)
            ifd = exif.get_ifd(0x8769)
            ifd[exif_tag_id] = value
        else:
            # Set tag in root EXIF
            exif[exif_tag_id] = value

        buf = BytesIO()
        img.save(buf, format="JPEG", exif=exif.tobytes())
        buf.seek(0)

        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)  # noqa: SIM115
        tmp.write(buf.read())
        tmp.close()
        return tmp.name

    def test_datetime_original(self) -> None:
        """Test extraction of DateTimeOriginal EXIF tag."""
        mock_img = MagicMock()
        mock_exif = MagicMock()
        mock_exif.__bool__ = lambda _s: True
        mock_exif.get_ifd.return_value = {36867: "2026:02:08 14:30:00"}
        mock_exif.get.return_value = None
        mock_img.getexif.return_value = mock_exif

        with patch("custom_components.gas_water_meter.ocr.Image.open", return_value=mock_img):
            result = extract_exif_datetime("/fake/path.jpg")
        assert result == "2026-02-08T14:30:00"

    def test_datetime_digitized(self) -> None:
        """Test extraction of DateTimeDigitized EXIF tag."""
        mock_img = MagicMock()
        mock_exif = MagicMock()
        mock_exif.__bool__ = lambda _s: True
        mock_exif.get_ifd.return_value = {36868: "2026:01:15 09:45:00"}
        mock_exif.get.return_value = None
        mock_img.getexif.return_value = mock_exif

        with patch("custom_components.gas_water_meter.ocr.Image.open", return_value=mock_img):
            result = extract_exif_datetime("/fake/path.jpg")
        assert result == "2026-01-15T09:45:00"

    def test_datetime_root_tag(self) -> None:
        """Test extraction of root DateTime EXIF tag."""
        path = self._create_jpeg_with_exif(306, "2025:12:25 18:00:00", use_ifd=False)
        result = extract_exif_datetime(path)
        assert result == "2025-12-25T18:00:00"

    def test_no_exif_data(self) -> None:
        """Test that None is returned when no EXIF data exists."""
        img = Image.new("RGB", (100, 100), color="white")
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)  # noqa: SIM115
        img.save(tmp.name, format="PNG")
        tmp.close()

        result = extract_exif_datetime(tmp.name)
        assert result is None

    def test_corrupt_exif_returns_none(self) -> None:
        """Test that corrupt EXIF data returns None gracefully."""
        with patch("PIL.Image.open", side_effect=Exception("corrupt")):
            result = extract_exif_datetime("/fake/path.jpg")
            assert result is None

    def test_priority_original_over_digitized(self) -> None:
        """Test that DateTimeOriginal takes priority over DateTimeDigitized."""
        mock_img = MagicMock()
        mock_exif = MagicMock()
        mock_exif.__bool__ = lambda _s: True
        # Both tags present; DateTimeOriginal (36867) should take priority
        mock_exif.get_ifd.return_value = {
            36867: "2026:02:08 10:00:00",
            36868: "2026:02:08 11:00:00",
        }
        mock_exif.get.return_value = None
        mock_img.getexif.return_value = mock_exif

        with patch("custom_components.gas_water_meter.ocr.Image.open", return_value=mock_img):
            result = extract_exif_datetime("/fake/path.jpg")
        assert result == "2026-02-08T10:00:00"

    # ---- Timezone offset tests ----

    def test_offset_time_original_appended(self) -> None:
        """Test that OffsetTimeOriginal is appended to DateTimeOriginal."""
        mock_img = MagicMock()
        mock_exif = MagicMock()
        mock_exif.__bool__ = lambda _s: True
        mock_exif.get_ifd.return_value = {
            36867: "2026:02:08 15:30:00",  # DateTimeOriginal
            36881: "+01:00",  # OffsetTimeOriginal
        }
        mock_exif.get.return_value = None
        mock_img.getexif.return_value = mock_exif

        with patch("custom_components.gas_water_meter.ocr.Image.open", return_value=mock_img):
            result = extract_exif_datetime("/fake/path.jpg")
        assert result == "2026-02-08T15:30:00+01:00"

    def test_offset_time_digitized_appended(self) -> None:
        """Test that OffsetTimeDigitized is appended to DateTimeDigitized."""
        mock_img = MagicMock()
        mock_exif = MagicMock()
        mock_exif.__bool__ = lambda _s: True
        mock_exif.get_ifd.return_value = {
            36868: "2026:01:15 09:45:00",  # DateTimeDigitized
            36882: "-05:00",  # OffsetTimeDigitized
        }
        mock_exif.get.return_value = None
        mock_img.getexif.return_value = mock_exif

        with patch("custom_components.gas_water_meter.ocr.Image.open", return_value=mock_img):
            result = extract_exif_datetime("/fake/path.jpg")
        assert result == "2026-01-15T09:45:00-05:00"

    def test_offset_time_for_root_datetime(self) -> None:
        """Test that OffsetTime is appended to root DateTime tag."""
        mock_img = MagicMock()
        mock_exif = MagicMock()
        mock_exif.__bool__ = lambda _s: True
        # No DateTimeOriginal / DateTimeDigitized in IFD
        mock_exif.get_ifd.return_value = {
            36880: "+02:00",  # OffsetTime
        }
        mock_exif.get.return_value = "2026:06:15 12:00:00"  # Root DateTime (306)
        mock_img.getexif.return_value = mock_exif

        with patch("custom_components.gas_water_meter.ocr.Image.open", return_value=mock_img):
            result = extract_exif_datetime("/fake/path.jpg")
        assert result == "2026-06-15T12:00:00+02:00"

    def test_no_offset_returns_naive_datetime(self) -> None:
        """Test that missing offset tags produce a naive ISO string."""
        mock_img = MagicMock()
        mock_exif = MagicMock()
        mock_exif.__bool__ = lambda _s: True
        mock_exif.get_ifd.return_value = {
            36867: "2026:02:08 15:30:00",  # DateTimeOriginal only, no offset
        }
        mock_exif.get.return_value = None
        mock_img.getexif.return_value = mock_exif

        with patch("custom_components.gas_water_meter.ocr.Image.open", return_value=mock_img):
            result = extract_exif_datetime("/fake/path.jpg")
        assert result == "2026-02-08T15:30:00"
        assert "+" not in result
        assert "Z" not in result

    def test_utc_offset(self) -> None:
        """Test that UTC offset (+00:00) is handled."""
        mock_img = MagicMock()
        mock_exif = MagicMock()
        mock_exif.__bool__ = lambda _s: True
        mock_exif.get_ifd.return_value = {
            36867: "2026:02:08 14:30:00",
            36881: "+00:00",
        }
        mock_exif.get.return_value = None
        mock_img.getexif.return_value = mock_exif

        with patch("custom_components.gas_water_meter.ocr.Image.open", return_value=mock_img):
            result = extract_exif_datetime("/fake/path.jpg")
        assert result == "2026-02-08T14:30:00+00:00"

    def test_offset_with_whitespace_is_stripped(self) -> None:
        """Test that offset values with trailing whitespace are handled."""
        mock_img = MagicMock()
        mock_exif = MagicMock()
        mock_exif.__bool__ = lambda _s: True
        mock_exif.get_ifd.return_value = {
            36867: "2026:02:08 15:30:00",
            36881: "+01:00 ",  # Trailing whitespace
        }
        mock_exif.get.return_value = None
        mock_img.getexif.return_value = mock_exif

        with patch("custom_components.gas_water_meter.ocr.Image.open", return_value=mock_img):
            result = extract_exif_datetime("/fake/path.jpg")
        assert result == "2026-02-08T15:30:00+01:00"

    def test_offset_original_takes_priority_when_both_present(self) -> None:
        """Test that OffsetTimeOriginal is used with DateTimeOriginal even if OffsetTimeDigitized is also present."""
        mock_img = MagicMock()
        mock_exif = MagicMock()
        mock_exif.__bool__ = lambda _s: True
        mock_exif.get_ifd.return_value = {
            36867: "2026:02:08 15:30:00",  # DateTimeOriginal
            36868: "2026:02:08 15:30:00",  # DateTimeDigitized
            36881: "+01:00",  # OffsetTimeOriginal
            36882: "+02:00",  # OffsetTimeDigitized
        }
        mock_exif.get.return_value = None
        mock_img.getexif.return_value = mock_exif

        with patch("custom_components.gas_water_meter.ocr.Image.open", return_value=mock_img):
            result = extract_exif_datetime("/fake/path.jpg")
        # DateTimeOriginal matched, so OffsetTimeOriginal (+01:00) is used
        assert result == "2026-02-08T15:30:00+01:00"


class TestPreprocessImage:
    """Tests for the image preprocessing pipeline."""

    def test_preprocess_returns_image(self) -> None:
        """Test that preprocess_image returns a PIL Image."""
        # Create a simple test image
        img = Image.new("RGB", (200, 100), color="white")
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)  # noqa: SIM115
        img.save(tmp.name, format="JPEG")
        tmp.close()

        result = preprocess_image(tmp.name)
        assert isinstance(result, Image.Image)

    def test_preprocess_converts_to_binary(self) -> None:
        """Test that preprocessing produces a binary (1-bit) image."""
        img = Image.new("RGB", (200, 100), color="gray")
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)  # noqa: SIM115
        img.save(tmp.name, format="JPEG")
        tmp.close()

        result = preprocess_image(tmp.name)
        # The final step applies binary threshold with mode="1"
        assert result.mode == "1"

    def test_preprocess_handles_exif_orientation(self) -> None:
        """Test that preprocessing applies EXIF auto-orientation."""
        # Create image with EXIF orientation tag
        img = Image.new("RGB", (200, 100), color="white")
        exif = img.getexif()
        # Tag 274 = Orientation; value 6 = rotated 90 CW
        exif[274] = 6
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)  # noqa: SIM115
        img.save(tmp.name, format="JPEG", exif=exif.tobytes())
        tmp.close()

        result = preprocess_image(tmp.name)
        # After orientation correction, width/height should be swapped
        assert result.size == (100, 200)


class TestReadMeterImage:
    """Tests for the full OCR pipeline."""

    def test_read_meter_image_tesseract_unavailable(self) -> None:
        """Test that read_meter_image raises RuntimeError when Tesseract is unavailable."""
        from custom_components.gas_water_meter.ocr import read_meter_image  # noqa: PLC0415

        with (
            patch("custom_components.gas_water_meter.ocr._TESSERACT_AVAILABLE", False),
            pytest.raises(RuntimeError, match="Tesseract OCR is not available"),
        ):
            read_meter_image("/fake/path.jpg")

    def test_read_meter_image_full_flow(self) -> None:
        """Test complete OCR pipeline with mocked pytesseract."""
        import custom_components.gas_water_meter.ocr as ocr_mod  # noqa: PLC0415

        # Create a test image
        img = Image.new("RGB", (200, 100), color="white")
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)  # noqa: SIM115
        img.save(tmp.name, format="JPEG")
        tmp.close()

        mock_tess = MagicMock()
        mock_tess.image_to_string.side_effect = [
            "12345.678",  # digit OCR
            "Nr: GAS-99999\n12345.678 m3",  # full-text OCR
        ]
        mock_tess.image_to_data.return_value = {
            "conf": ["95", "90", "88", "-1", "92"],
        }
        mock_tess.Output.DICT = "dict"

        with (
            patch("custom_components.gas_water_meter.ocr._TESSERACT_AVAILABLE", True),
            patch.dict("sys.modules", {"pytesseract": mock_tess}),
        ):
            result = ocr_mod.read_meter_image(tmp.name)

        assert isinstance(result, OcrResult)
        assert result.meter_reading == 12345.678
        assert result.meter_number == "GAS-99999"
        assert result.confidence > 0

    def test_read_meter_image_confidence_error_fallback(self) -> None:
        """Test that confidence defaults to 0.0 when image_to_data fails."""
        import custom_components.gas_water_meter.ocr as ocr_mod  # noqa: PLC0415

        img = Image.new("RGB", (200, 100), color="white")
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)  # noqa: SIM115
        img.save(tmp.name, format="JPEG")
        tmp.close()

        mock_tess = MagicMock()
        mock_tess.image_to_string.side_effect = [
            "12345.678",  # digit OCR
            "some text",  # full-text OCR
        ]
        mock_tess.image_to_data.side_effect = Exception("data extraction failed")
        mock_tess.Output.DICT = "dict"

        with (
            patch("custom_components.gas_water_meter.ocr._TESSERACT_AVAILABLE", True),
            patch.dict("sys.modules", {"pytesseract": mock_tess}),
        ):
            result = ocr_mod.read_meter_image(tmp.name)

        assert result.confidence == 0.0


class TestExtFromContentType:
    """Tests for HTTP content-type to file extension mapping."""

    def test_jpeg(self) -> None:
        assert _ext_from_content_type("image/jpeg") == ".jpg"

    def test_png(self) -> None:
        assert _ext_from_content_type("image/png") == ".png"

    def test_gif(self) -> None:
        assert _ext_from_content_type("image/gif") == ".gif"

    def test_webp(self) -> None:
        assert _ext_from_content_type("image/webp") == ".webp"

    def test_tiff(self) -> None:
        assert _ext_from_content_type("image/tiff") == ".tiff"

    def test_heic(self) -> None:
        assert _ext_from_content_type("image/heic") == ".heic"

    def test_heif(self) -> None:
        assert _ext_from_content_type("image/heif") == ".heif"

    def test_heic_sequence(self) -> None:
        assert _ext_from_content_type("image/heic-sequence") == ".heic"

    def test_heif_sequence(self) -> None:
        assert _ext_from_content_type("image/heif-sequence") == ".heif"

    def test_content_type_with_charset(self) -> None:
        assert _ext_from_content_type("image/jpeg; charset=utf-8") == ".jpg"

    def test_case_insensitive(self) -> None:
        assert _ext_from_content_type("Image/HEIC") == ".heic"

    def test_unknown_type(self) -> None:
        assert _ext_from_content_type("application/octet-stream") is None


class TestHeifAvailability:
    """Tests for HEIF opener registration."""

    def test_is_heif_available_function_exists(self) -> None:
        """Test that the is_heif_available function is importable."""
        from custom_components.gas_water_meter.ocr import is_heif_available  # noqa: PLC0415

        # Should return a boolean regardless of whether pillow-heif is installed
        assert isinstance(is_heif_available(), bool)

    def test_heif_opener_registration_succeeds(self) -> None:
        """Test that register_heif_opener is called when pillow-heif is available."""
        mock_register = MagicMock()
        mock_module = MagicMock()
        mock_module.register_heif_opener = mock_register

        with patch.dict("sys.modules", {"pillow_heif": mock_module}):
            # Re-execute the registration logic
            from pillow_heif import register_heif_opener  # noqa: PLC0415

            register_heif_opener()
            mock_register.assert_called_once()

    def test_heif_opener_graceful_fallback(self) -> None:
        """Test that missing pillow-heif does not raise an error."""
        with patch.dict("sys.modules", {"pillow_heif": None}):
            try:
                from pillow_heif import register_heif_opener  # noqa: PLC0415

                register_heif_opener()
                available = True
            except (ImportError, TypeError):
                available = False

        assert not available
