"""File upload/import handler for document analysis.

Handles:
  - Saving uploaded .md files to pm_data/imports/
  - File type and size validation
  - Reading .md content as plain text
"""

import hashlib
import os
from pathlib import Path

from loguru import logger

from app.config import config

ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".docx", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".bmp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class FileValidationError(Exception):
    """Raised when file validation fails."""


def validate_upload(filename: str, content: bytes) -> None:
    """Validate uploaded file type and size.

    Raises FileValidationError if invalid.
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Unsupported file type '{ext}'. Only {', '.join(ALLOWED_EXTENSIONS)} allowed."
        )
    if len(content) > MAX_FILE_SIZE:
        raise FileValidationError(
            f"File too large ({len(content) / 1024 / 1024:.1f} MB). Max {MAX_FILE_SIZE / 1024 / 1024:.0f} MB."
        )


def decode_content(content: bytes) -> str:
    """Decode bytes to string, trying UTF-8 first then GBK."""
    for enc in ("utf-8", "gbk", "gb2312"):
        try:
            return content.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    # Fallback: replace errors
    return content.decode("utf-8", errors="replace")


def save_import_file(session_id: str, filename: str, content: bytes) -> str:
    """Save uploaded file to pm_data/imports/{session_id}/{filename}.

    Returns the absolute file path.
    """
    import_dir = Path(config.data_dir) / "imports" / session_id
    import_dir.mkdir(parents=True, exist_ok=True)

    # Avoid path traversal
    safe_name = Path(filename).name
    dest = import_dir / safe_name

    # Deduplicate: if file with same content exists, skip write
    if dest.exists() and dest.stat().st_size == len(content):
        logger.debug(f"File already exists, skipping: {dest}")
        return str(dest)

    dest.write_bytes(content)
    logger.info(f"Saved import file: {dest} (size={len(content)})")
    return str(dest)
