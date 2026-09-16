from core.errors import UnsupportedFormatError
from core.models import ExtractedDocument
from utils.files import validate_upload
from core.extractors.text_extractor import TextExtractor
from core.extractors.pdf_extractor import PDFExtractor
from core.extractors.excel_extractor import ExcelExtractor
from core.extractors.image_extractor import ImageExtractor

_EXTRACTORS = [PDFExtractor(), ExcelExtractor(), ImageExtractor(), TextExtractor()]


def route(data: bytes, filename: str, mime: str = "") -> ExtractedDocument:
    ext = validate_upload(filename, data)
    for ex in _EXTRACTORS:
        if ex.supports(mime, ext):
            return ex.extract(data, filename)
    raise UnsupportedFormatError(f"No extractor for '{filename}' ({ext})")
