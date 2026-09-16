"""Text normalization and chunking."""
from __future__ import annotations
import re

_WS_RE = re.compile(r"[ \t]+")
_NEWLINES_RE = re.compile(r"\n{3,}")


def normalize(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WS_RE.sub(" ", text)
    text = _NEWLINES_RE.sub("\n\n", text)
    return text.strip()


def chunk(text: str, max_chars: int = 12000) -> list[str]:
    """Split text into chunks of ~max_chars, respecting paragraph breaks."""
    if len(text) <= max_chars:
        return [text]
    chunks, current = [], []
    size = 0
    for para in text.split("\n\n"):
        if size + len(para) > max_chars and current:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        current.append(para)
        size += len(para) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks
