"""Upload validation helpers. No disk I/O — everything stays in memory."""
from __future__ import annotations
from config import settings
from core.errors import UnsupportedFormatError

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".txt"}

MAGIC_BYTES = {
    b"%PDF": ".pdf",
    b"PK\x03\x04": ".xlsx",          # xlsx (zip)
    b"\xd0\xcf\x11\xe0": ".xls",     # legacy xls (OLE)
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
}


def _ext(filename: str) -> str:
    return ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""


def validate_upload(filename: str, data: bytes) -> str:
    """Return normalized extension or raise UnsupportedFormatError."""
    ext = _ext(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"'{filename}' has unsupported extension '{ext}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    size_mb = len(data) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_MB:
        raise UnsupportedFormatError(
            f"'{filename}' is {size_mb:.1f} MB — exceeds "
            f"{settings.MAX_UPLOAD_MB} MB limit."
        )

    # Magic-byte check for binary formats (skip .txt which has no signature)
    if ext != ".txt":
        for sig, expected_ext in MAGIC_BYTES.items():
            if data.startswith(sig):
                # xlsx vs xls — both are zip/OLE; fine either way
                return ext
        # No magic match — reject only if user claims a binary format
        raise UnsupportedFormatError(
            f"'{filename}' content does not match its extension '{ext}'."
        )
    return ext
