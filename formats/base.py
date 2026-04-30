"""Exporter protocol — every format module must expose a function matching
this signature (or be callable via the factory below).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.models import FileRef


@runtime_checkable
class SyncExporter(Protocol):
    """Synchronous exporter interface."""
    def __call__(self, content: object, filename: str | None) -> FileRef: ...


@runtime_checkable
class AsyncExporter(Protocol):
    """Asynchronous exporter interface (for PDF, images)."""
    async def __call__(self, content: object, filename: str | None) -> FileRef: ...
