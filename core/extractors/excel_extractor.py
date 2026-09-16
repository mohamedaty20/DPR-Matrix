import io
import pandas as pd
from core.extractors.base import BaseExtractor
from core.models import ExtractedDocument
from utils.text_utils import normalize


def _df_to_md(df):
    cols = [str(c) for c in df.columns]
    rows = [["" if v is None else str(v) for v in r] for r in df.values.tolist()]
    if not cols: return ""
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join([header, sep, *body])


class ExcelExtractor(BaseExtractor):
    def supports(self, mime, ext):
        return ext in {".xlsx", ".xls"}

    def extract(self, data, filename):
        engine = "openpyxl" if filename.lower().endswith(".xlsx") else "xlrd"
        sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, engine=engine)

        sections, raw_parts = [], []
        for sheet_name, df in sheets.items():
            if df.empty: continue
            df = df.fillna("")
            md = _df_to_md(df)
            sections.append({
                "type": "table", "sheet": sheet_name,
                "columns": [str(c) for c in df.columns],
                "rows": df.values.tolist(),
            })
            raw_parts.append(f"### Sheet: {sheet_name}\n{md}")

        raw_text = normalize("\n\n".join(raw_parts))
        return ExtractedDocument(
            filename=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            sections=sections, raw_text=raw_text,
            meta={"sheets": list(sheets.keys()), "chars": len(raw_text)},
        )
