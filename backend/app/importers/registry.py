from __future__ import annotations

from pathlib import Path

from ..domain.enums import ModelRole
from ..domain.models import GeometryModel
from .base import Importer

_IMPORTERS: list[Importer] = []


def register_importer(cls: type[Importer]) -> type[Importer]:
    """Class decorator that adds an importer to the registry."""
    _IMPORTERS.append(cls())
    return cls


def available_importers() -> list[Importer]:
    return list(_IMPORTERS)


def supported_extensions() -> list[str]:
    return sorted({ext for imp in _IMPORTERS for ext in imp.extensions})


class UnsupportedFormatError(Exception):
    pass


def find_importer(path: Path) -> Importer:
    for importer in _IMPORTERS:
        if importer.can_handle(path):
            return importer
    raise UnsupportedFormatError(
        f"No importer for {path.name!r}. Supported: {', '.join(supported_extensions())}"
    )


def load_model(path: Path, role: ModelRole, model_id: str) -> GeometryModel:
    """Auto-detect the format of `path` and import it."""
    return find_importer(path).load(path, role, model_id)
