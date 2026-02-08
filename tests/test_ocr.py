"""Tests for the Gas & Water Meter OCR module."""

from __future__ import annotations

from custom_components.gas_water_meter.ocr import (
    extract_meter_number,
    extract_meter_reading,
)


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
        text = "Nr 42\n12345.678\nDate 2026"
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
