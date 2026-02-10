"""Tesseract OCR module for meter reading extraction."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom tessdata directory shipped with the integration
# ---------------------------------------------------------------------------

_TESSDATA_DIR = Path(__file__).parent / "tessdata"


def _get_tessdata_config() -> str:
    """Return a ``--tessdata-dir`` CLI fragment if custom tessdata files exist.

    Tesseract expects the directory to contain at least one ``.traineddata``
    file.  When the bundled ``tessdata/`` directory has no such files the
    system-installed training data is used as a fallback (empty string
    returned).
    """
    if _TESSDATA_DIR.is_dir() and any(_TESSDATA_DIR.glob("*.traineddata")):
        _LOGGER.debug("Using custom tessdata directory: %s", _TESSDATA_DIR)
        return f"--tessdata-dir {_TESSDATA_DIR}"
    return ""

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


# ---------------------------------------------------------------------------
# Tesseract binary auto-installation & availability check
# ---------------------------------------------------------------------------

_TESSERACT_AVAILABLE = False


def _check_tesseract() -> bool:
    """Return True if the tesseract binary and pytesseract wrapper are usable."""
    try:
        import pytesseract  # noqa: PLC0415

        pytesseract.get_tesseract_version()
    except (OSError, ImportError):
        return False
    else:
        return True


def _install_tesseract() -> bool:
    """Try to install the tesseract-ocr system package.

    Supports Alpine Linux (HAOS / Docker) and Debian/Ubuntu.
    Returns True if installation succeeded.
    """
    # Already installed?
    if shutil.which("tesseract"):
        return True

    # --- Alpine Linux (apk) - typical for Home Assistant OS ---
    if shutil.which("apk"):
        try:
            _LOGGER.info("Installing tesseract-ocr via apk (Alpine)")
            subprocess.run(
                [  # noqa: S607
                    "apk",
                    "add",
                    "--no-cache",
                    "tesseract-ocr",
                    "tesseract-ocr-data-eng",
                    "tesseract-ocr-data-deu",
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            _LOGGER.warning("apk install of tesseract-ocr failed: %s", exc)
        else:
            _LOGGER.info("tesseract-ocr installed successfully via apk")
            return True

    # --- Debian / Ubuntu (apt-get) ---
    if shutil.which("apt-get"):
        try:
            _LOGGER.info("Installing tesseract-ocr via apt-get (Debian)")
            subprocess.run(
                ["apt-get", "update", "-qq"],  # noqa: S607
                check=True,
                capture_output=True,
                timeout=60,
            )
            subprocess.run(
                [  # noqa: S607
                    "apt-get",
                    "install",
                    "-y",
                    "-qq",
                    "tesseract-ocr",
                    "tesseract-ocr-eng",
                    "tesseract-ocr-deu",
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            _LOGGER.warning("apt-get install of tesseract-ocr failed: %s", exc)
        else:
            _LOGGER.info("tesseract-ocr installed successfully via apt-get")
            return True

    _LOGGER.warning(
        "Could not auto-install tesseract-ocr. "
        "Please install it manually (e.g. 'apk add tesseract-ocr' or "
        "'apt-get install tesseract-ocr')."
    )
    return False


def ensure_tesseract() -> bool:
    """Ensure the Tesseract binary is installed and update availability flag.

    This is safe to call multiple times; it short-circuits if Tesseract is
    already available. It is meant to be called from an executor (blocking I/O).
    """
    global _TESSERACT_AVAILABLE  # noqa: PLW0603

    if _check_tesseract():
        _TESSERACT_AVAILABLE = True
        return True

    # Try automatic installation
    _install_tesseract()

    # Re-check after installation attempt
    _TESSERACT_AVAILABLE = _check_tesseract()
    if _TESSERACT_AVAILABLE:
        _LOGGER.info("Tesseract OCR is now available")
    else:
        _LOGGER.warning("Tesseract OCR is not available. OCR-based meter reading detection will be disabled.")
    return _TESSERACT_AVAILABLE


# Initial check at import time (best-effort, no install)
_TESSERACT_AVAILABLE = _check_tesseract()
if not _TESSERACT_AVAILABLE:
    _LOGGER.debug("Tesseract OCR not found at import time - will attempt auto-install during setup.")


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

    If a corresponding timezone offset tag is present (OffsetTimeOriginal,
    OffsetTimeDigitized, or OffsetTime), it is appended so the returned
    ISO 8601 string is timezone-aware (e.g. "2026-02-08T15:30:00+01:00").

    Returns an ISO 8601 formatted datetime string, or None if no EXIF date is found.
    """
    # EXIF datetime tag IDs
    tag_dt_original = 36867
    tag_dt_digitized = 36868
    tag_dt_root = 306

    # Corresponding timezone offset tag IDs (stored in ExifIFD)
    tag_off_original = 36881  # OffsetTimeOriginal
    tag_off_digitized = 36882  # OffsetTimeDigitized
    tag_off_root = 36880  # OffsetTime (for root DateTime)

    # Map each datetime tag to its matching offset tag
    offset_for_tag = {
        tag_dt_original: tag_off_original,
        tag_dt_digitized: tag_off_digitized,
        tag_dt_root: tag_off_root,
    }

    try:
        img = Image.open(image_path)
        exif_data = img.getexif()

        if not exif_data:
            return None

        # Check IFD EXIF sub-directory for DateTimeOriginal and DateTimeDigitized
        exif_ifd = exif_data.get_ifd(0x8769)  # ExifIFD

        exif_datetime_str = None
        matched_tag: int | None = None

        for tag_id in [tag_dt_original, tag_dt_digitized]:
            value = exif_ifd.get(tag_id)
            if value:
                exif_datetime_str = value
                matched_tag = tag_id
                break

        # Fallback to root DateTime tag
        if exif_datetime_str is None:
            exif_datetime_str = exif_data.get(tag_dt_root)
            if exif_datetime_str is not None:
                matched_tag = tag_dt_root

        if exif_datetime_str is None:
            return None

        # EXIF datetime format is "YYYY:MM:DD HH:MM:SS"
        # Convert to ISO 8601 format
        parsed = datetime.strptime(exif_datetime_str, "%Y:%m:%d %H:%M:%S")
        iso_str = parsed.isoformat()

        # Look up the timezone offset tag corresponding to the matched datetime tag
        offset_tag = offset_for_tag.get(matched_tag)
        if offset_tag is not None:
            # Offset tags live in the ExifIFD sub-directory
            offset_value = exif_ifd.get(offset_tag)
            if offset_value and isinstance(offset_value, str):
                # Value is like "+01:00" or "-05:00"
                iso_str += offset_value.strip()

    except Exception:
        _LOGGER.debug("Could not extract EXIF datetime from %s", image_path, exc_info=True)
        return None
    else:
        return iso_str


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

    # Build tessdata-dir fragment (empty string when no custom data present)
    td = _get_tessdata_config()

    # Run OCR optimized for digits (meter reading)
    digit_config = rf"--psm 6 -c tessedit_char_whitelist=0123456789.,- {td}".rstrip()
    digit_text = tess.image_to_string(processed, config=digit_config).strip()

    # Run OCR with full character set (for meter number / labels)
    full_text = tess.image_to_string(
        Image.open(image_path),
        config=td,
    ).strip()

    # Get confidence data
    try:
        data = tess.image_to_data(
            processed,
            output_type=tess.Output.DICT,
            config=td,
        )
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
