class DPRMatrixError(Exception): pass
class ExtractionError(DPRMatrixError): pass
class UnsupportedFormatError(ExtractionError): pass
class GeminiError(DPRMatrixError): pass
class ExportError(DPRMatrixError): pass
