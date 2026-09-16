from abc import ABC, abstractmethod
from core.models import ExtractedDocument


class BaseExtractor(ABC):
    @abstractmethod
    def supports(self, mime: str, ext: str) -> bool: ...

    @abstractmethod
    def extract(self, data: bytes, filename: str) -> ExtractedDocument: ...
