"""
File upload validation and sanitization utilities.
Ensures magic byte verification, size limits, and path traversal protection.
"""

import os
import re
from backend.app.observability.errors import ErrorCategory, FactLensAPIException

PDF_MAGIC_BYTES = b"%PDF-"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize an uploaded file name to eliminate path traversal, directory separators,
    and dangerous control characters.
    """
    if not filename:
        return "document.pdf"

    # Strip directory components (e.g. ../../etc/passwd -> passwd)
    basename = os.path.basename(filename.replace("\\", "/"))

    # Remove null bytes, control characters, and non-printable characters
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", basename)

    # Strip dangerous shell characters
    cleaned = re.sub(r"[^\w\.\-\_]", "_", cleaned)

    # Prevent hidden files or relative dots
    cleaned = cleaned.lstrip(".")

    if not cleaned or not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned or 'document'}.pdf"

    return cleaned


def validate_pdf_file(
    filename: str,
    file_bytes: bytes,
    max_file_size_mb: int = 50,
) -> str:
    """
    Validate an uploaded file:
    1. Check file size is non-empty and does not exceed max_file_size_mb.
    2. Check PDF magic bytes (%PDF-).
    3. Sanitize filename.

    :return: Sanitized filename
    :raises FactLensAPIException: If validation fails
    """
    if not file_bytes or len(file_bytes) == 0:
        raise FactLensAPIException(
            message="Uploaded file is empty (0 bytes).",
            category=ErrorCategory.EMPTY_DOCUMENT,
            status_code=400,
        )

    max_bytes = max_file_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        file_size_mb = len(file_bytes) / (1024 * 1024)
        raise FactLensAPIException(
            message=(
                f"File size ({file_size_mb:.1f} MB) exceeds maximum allowed size "
                f"of {max_file_size_mb} MB."
            ),
            category=ErrorCategory.INVALID_FILE,
            status_code=413,
            context={"file_size_bytes": len(file_bytes), "max_allowed_mb": max_file_size_mb},
        )

    if not file_bytes.startswith(PDF_MAGIC_BYTES):
        raise FactLensAPIException(
            message=(
                "Invalid PDF file header. The uploaded file does not start with valid "
                "PDF magic bytes ('%PDF-')."
            ),
            category=ErrorCategory.INVALID_FILE,
            status_code=400,
            context={"magic_bytes_preview": str(file_bytes[:16])},
        )

    return sanitize_filename(filename)
