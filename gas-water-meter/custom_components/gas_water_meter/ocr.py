"""Tesseract OCR module for meter reading extraction."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

if TYPE_CHECKING:
    from pathlib import Path

_LOGGER = logging.getLogger(__name__)

# Register HEIC/HEIF support if pillow-heif is installed
_HEIF_AVAILABLE = False
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    _HEIF_AVAILABLE = True
except ImportError:
    _LOGGER.debug("pillow-heif is not installed - HEIC/HEIF photo support unavailable")


def is_heif_available() -> bool:
    """Return whether HEIC/HEIF image support is available."""
    return _HEIF_AVAILABLE

# Check if pytesseract is available
_TESSERACT_AVAILABLE = False
try:
    import pytesseract

    # Verify the binary is accessible
    pytesseract.get_tesseract_version()
    _TESSERACT_AVAILABLE = True
except (OSError, ImportError):
    _LOGGER.warning("Tesseract OCR is not available. Install pytesseract and the tesseract-ocr binary for OCR support.")


def is_tesseract_available() -> bool:
    """Return whether Tesseract OCR is available."""
    return _TESSERACT_AVAILABLE


@dataclass
class OcrResult:
    """Result of an OCR meter reading extraction."""

    meter_reading: float | None
    meter_number: str | None
    confidence: float
    raw_text: str
    exif_datetime: str | None


def extract_exif_datetime(image_path: str | Path) -> str | None:
    """Extract the photo capture date/time from EXIF data.

    Checks the following EXIF tags in order of preference:
    1. DateTimeOriginal (tag 36867) -- when the photo was originally taken
    2. DateTimeDigitized (tag 36868) -- when the image was digitized
    3. DateTime (tag 306) -- last modification time

    Returns an ISO 8601 formatted datetime string, or None if no EXIF date is found.
    """
    # EXIF tag IDs
    tag_datetime_original = 36867
    tag_datetime_digitized = 36868
    tag_datetime = 306

    try:
        img = Image.open(image_path)
        exif_data = img.getexif()

        if not exif_data:
            return None

        # Check IFD EXIF sub-directory for DateTimeOriginal and DateTimeDigitized
        exif_ifd = exif_data.get_ifd(0x8769)  # ExifIFD

        exif_datetime_str = None
        for tag_id in [tag_datetime_original, tag_datetime_digitized]:
            value = exif_ifd.get(tag_id)
            if value:
                exif_datetime_str = value
                break

        # Fallback to root DateTime tag
        if exif_datetime_str is None:
            exif_datetime_str = exif_data.get(tag_datetime)

        if exif_datetime_str is None:
            return None

        # EXIF datetime format is "YYYY:MM:DD HH:MM:SS"
        # Convert to ISO 8601 format
        parsed = datetime.strptime(exif_datetime_str, "%Y:%m:%d %H:%M:%S")
        return parsed.isoformat()

    except Exception:
        _LOGGER.debug("Could not extract EXIF datetime from %s", image_path, exc_info=True)
        return None


def preprocess_image(image_path: str | Path) -> Image.Image:
    """Preprocess a meter image for better OCR results.

    Pipeline:
    1. Load and convert to grayscale
    2. Auto-orient based on EXIF
    3. Enhance contrast
    4. Apply sharpening
    5. Apply threshold for better digit recognition
    """
    img = Image.open(image_path)

    # Auto-orient based on EXIF data
    img = ImageOps.exif_transpose(img)

    # Convert to grayscale
    img = img.convert("L")

    # Enhance contrast
    img = ImageOps.autocontrast(img, cutoff=2)

    # Sharpen for better digit edges
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.0)

    # Apply a slight blur to reduce noise, then sharpen
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # Apply binary threshold for clean digit recognition
    threshold = 128
    img = img.point(lambda x: 255 if x > threshold else 0, mode="1")

    return img


def extract_meter_reading(raw_text: str) -> float | None:
    """Extract a numeric meter reading from OCR text.

    Looks for patterns like:
    - 1234.567
    - 1234,567
    - 12345
    - 1 234.567 (with spaces)
    """
    # Remove spaces within numbers
    cleaned = re.sub(r"(\d)\s+(\d)", r"\1\2", raw_text)

    # Find all numeric patterns (with optional decimal part)
    patterns = re.findall(r"\d+[.,]\d+|\d{4,}", cleaned)

    if not patterns:
        return None

    # Take the longest match (most likely to be the meter reading)
    best = max(patterns, key=len)

    # Normalize decimal separator
    best = best.replace(",", ".")

    try:
        return float(best)
    except ValueError:
        return None


def extract_meter_number(raw_text: str) -> str | None:
    """Extract a meter number from OCR text.

    Looks for alphanumeric patterns near common labels.
    """
    # Look for patterns near meter number labels
    label_patterns = [
        r"(?:Nr|No|Nummer|Number|Z[äa]hler(?:nr)?)[.:;]?\s*([A-Za-z0-9\-/]{4,20})",
        r"(?:Meter|Serial)[.:;]?\s*([A-Za-z0-9\-/]{4,20})",
    ]

    for pattern in label_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def read_meter_image(image_path: str | Path) -> OcrResult:
    """Read a meter image and extract the reading and meter number.

    This is a blocking function -- must be called via async_add_executor_job.

    Raises RuntimeError if Tesseract is not available.
    """
    if not _TESSERACT_AVAILABLE:
        msg = "Tesseract OCR is not available. Please install the tesseract-ocr binary on your system."
        raise RuntimeError(msg)

    import pytesseract as tess  # noqa: PLC0415

    # Extract EXIF datetime before preprocessing (which strips EXIF)
    exif_dt = extract_exif_datetime(image_path)

    # Preprocess the image
    processed = preprocess_image(image_path)

    # Run OCR optimized for digits (meter reading)
    digit_config = r"--psm 6 -c tessedit_char_whitelist=0123456789.,-"
    digit_text = tess.image_to_string(processed, config=digit_config).strip()

    # Run OCR with full character set (for meter number / labels)
    full_text = tess.image_to_string(Image.open(image_path)).strip()

    # Get confidence data
    try:
        data = tess.image_to_data(processed, output_type=tess.Output.DICT)
        confidences = [int(c) for c in data["conf"] if int(c) > 0]
        avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
    except Exception:
        avg_confidence = 0.0

    # Extract values
    meter_reading = extract_meter_reading(digit_text)
    meter_number = extract_meter_number(full_text)

    # Combine raw text for debugging
    raw_text = f"DIGITS: {digit_text}\n---\nFULL: {full_text}"

    _LOGGER.debug(
        "OCR result: reading=%s, number=%s, confidence=%.2f, raw=%s",
        meter_reading,
        meter_number,
        avg_confidence,
        raw_text,
    )

    return OcrResult(
        meter_reading=meter_reading,
        meter_number=meter_number,
        confidence=avg_confidence,
        raw_text=raw_text,
        exif_datetime=exif_dt,
    )
