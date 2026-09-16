from core.extractors.base import BaseExtractor
from core.models import ExtractedDocument
from core.gemini_client import describe_image
from utils.text_utils import normalize

PROMPT = (
    "You are transcribing a construction Daily Progress Report (DPR) image. "
    "Extract ALL visible text, handwriting, tables, checkboxes, and numerical data. "
    "Preserve table structure using markdown. Do not summarize — transcribe verbatim."
)


class ImageExtractor(BaseExtractor):
    def supports(self, mime, ext):
        return ext in {".png", ".jpg", ".jpeg"}

    def extract(self, data, filename):
        mime = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
        try:
            text = normalize(describe_image(data, mime, PROMPT))
        except Exception as e:
            text = f"[vision OCR failed: {e}]"
        return ExtractedDocument(
            filename=filename, mime=mime,
            sections=[{"type": "ocr", "content": text}],
            raw_text=text, meta={"chars": len(text)},
        )
