"""Tests for the Gas & Water Meter OCR module."""

from __future__ import annotations

import tempfile
from io import BytesIO
from unittest.mock import patch

from custom_components.gas_water_meter.ocr import (
    extract_exif_datetime,
    extract_meter_number,
    extract_meter_reading,
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
        path = self._create_jpeg_with_exif(36867, "2026:02:08 14:30:00")
        result = extract_exif_datetime(path)
        assert result == "2026-02-08T14:30:00"

    def test_datetime_digitized(self) -> None:
        """Test extraction of DateTimeDigitized EXIF tag."""
        path = self._create_jpeg_with_exif(36868, "2026:01:15 09:45:00")
        result = extract_exif_datetime(path)
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
        img = Image.new("RGB", (100, 100), color="white")
        exif = img.getexif()
        ifd = exif.get_ifd(0x8769)
        ifd[36867] = "2026:02:08 10:00:00"  # DateTimeOriginal
        ifd[36868] = "2026:02:08 11:00:00"  # DateTimeDigitized

        buf = BytesIO()
        img.save(buf, format="JPEG", exif=exif.tobytes())
        buf.seek(0)

        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)  # noqa: SIM115
        tmp.write(buf.read())
        tmp.close()

        result = extract_exif_datetime(tmp.name)
        assert result == "2026-02-08T10:00:00"
