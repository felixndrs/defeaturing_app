"""Importer contract.

Adding support for a new file format means adding one module in this package
that subclasses Importer and decorates itself with @register_importer. Nothing
else in the application needs to change.
"""

from __future__ import annotations

import abc
from pathlib import Path

from ..domain.enums import ModelRole, SourceFormat
from ..domain.models import GeometryModel


class ImportError_(Exception):
    """Raised when a file matches an importer but cannot be read."""


class Importer(abc.ABC):
    #: Human readable name, used in logs and reports.
    name: str
    #: Format this importer produces in GeometryModel.source_format.
    source_format: SourceFormat
    #: Lowercase file extensions this importer claims, including the dot.
    extensions: tuple[str, ...] = ()

    def can_handle(self, path: Path) -> bool:
        """Whether this importer should be used for `path`.

        The default is extension based. Importers for formats that share an
        extension (.dat is used by several solvers) should override this and
        sniff the file content instead.
        """
        return path.suffix.lower() in self.extensions

    @abc.abstractmethod
    def load(self, path: Path, role: ModelRole, model_id: str) -> GeometryModel:
        """Read `path` into the internal data model."""
