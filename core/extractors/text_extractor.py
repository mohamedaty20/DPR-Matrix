from core.extractors.base import BaseExtractor
from core.models import ExtractedDocument
from utils.text_utils import normalize


class TextExtractor(BaseExtractor):
    def supports(self, mime, ext):
        return ext == ".txt"

    def extract(self, data, filename):
        for enc in ("utf-8", "utf-16", "latin-1"):
            try:
                text = data.decode(enc); break
            except UnicodeDecodeError:
                continue
        else:
            text = data.decode("utf-8", errors="replace")
        text = normalize(text)
        return ExtractedDocument(
            filename=filename, mime="text/plain",
            sections=[{"type": "text", "content": text}],
            raw_text=text, meta={"chars": len(text)},
        )
