import io
import pdfplumber
from core.extractors.base import BaseExtractor
from core.models import ExtractedDocument
from core.gemini_client import describe_image
from utils.text_utils import normalize


class PDFExtractor(BaseExtractor):
    def supports(self, mime, ext):
        return ext == ".pdf"

    def extract(self, data, filename):
        sections, raw_parts = [], []

        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    txt = page.extract_text() or ""
                    if txt.strip():
                        sections.append({"type": "text", "page": i, "content": normalize(txt)})
                        raw_parts.append(txt)
                    for t_idx, table in enumerate(page.extract_tables() or [], start=1):
                        if table and any(any(c for c in row) for row in table):
                            md = self._table_to_md(table)
                            sections.append({"type": "table", "page": i, "table_index": t_idx, "rows": table})
                            raw_parts.append(md)
        except Exception as e:
            sections.append({"type": "error", "content": str(e)})

        text_chars = sum(len(s.get("content", "")) for s in sections if s["type"] == "text")
        if text_chars < 40:
            sections.append({"type": "note", "content": "Low text yield — applying vision OCR"})
            raw_parts.append(self._vision_ocr(data))

        raw_text = normalize("\n\n".join(raw_parts))
        pages = sum(1 for s in sections if s.get("page"))
        return ExtractedDocument(
            filename=filename, mime="application/pdf",
            sections=sections, raw_text=raw_text,
            meta={"pages": pages, "chars": len(raw_text)},
        )

    @staticmethod
    def _table_to_md(rows):
        rows = [[("" if c is None else str(c)) for c in r] for r in rows]
        if not rows: return ""
        header = "| " + " | ".join(rows[0]) + " |"
        sep = "| " + " | ".join(["---"] * len(rows[0])) + " |"
        body = ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return "\n".join([header, sep, *body])

    @staticmethod
    def _vision_ocr(data, max_pages=5):
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(io.BytesIO(data))
            out = []
            for i in range(min(len(pdf), max_pages)):
                pil = pdf[i].render(scale=2.0).to_pil()
                buf = io.BytesIO(); pil.save(buf, format="PNG")
                text = describe_image(
                    buf.getvalue(), "image/png",
                    "Transcribe ALL text, tables and notes from this site report page. "
                    "Preserve structure. Do not summarize.",
                )
                out.append(f"[page {i+1}]\n{text}")
            return "\n\n".join(out)
        except Exception as e:
            return f"[vision OCR failed: {e}]"
