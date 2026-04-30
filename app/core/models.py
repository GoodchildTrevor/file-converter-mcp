"""Domain models — shared across all layers.

Rules:
- No I/O in this file.
- No imports from formats/, storage/, integrations/.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExportFormat(str, Enum):
    TXT   = "txt"
    MD    = "md"
    HTML  = "html"
    JSON  = "json"
    XML   = "xml"
    CSV   = "csv"
    DOCX  = "docx"
    PPTX  = "pptx"
    XLSX  = "xlsx"
    PDF   = "pdf"

    @classmethod
    def text_formats(cls) -> frozenset["ExportFormat"]:
        return frozenset({cls.TXT, cls.MD, cls.HTML, cls.JSON, cls.XML})

    @classmethod
    def table_formats(cls) -> frozenset["ExportFormat"]:
        return frozenset({cls.CSV, cls.XLSX})

    @classmethod
    def document_formats(cls) -> frozenset["ExportFormat"]:
        return frozenset({cls.DOCX, cls.PPTX, cls.PDF})


class ArchiveFormat(str, Enum):
    ZIP    = "zip"
    TAR    = "tar"
    TAR_GZ = "tar.gz"
    SEVEN_Z = "7z"


@dataclass
class FileRef:
    """Pointer to a generated file — always returned by exporters."""
    path: str
    name: str
    url: str | None = None
    media_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "name": self.name, "url": self.url}


@dataclass
class ExportResult:
    """Successful export outcome."""
    file: FileRef
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"url": self.file.url, "path": self.file.path, **self.metadata}


@dataclass
class ExportError(Exception):
    """Typed export failure — returned as {"error": {"message": ...}} by MCP tools."""
    message: str
    code: str = "EXPORT_ERROR"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message}}
