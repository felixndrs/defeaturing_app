from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from OCP.Interface import Interface_Static
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.TopoDS import TopoDS_Shape


@pytest.fixture(scope="session", autouse=True)
def tmp_data_dir(tmp_path_factory) -> Path:
    """Point the app at a throwaway data directory for the whole test session.

    Without this, tests would write into the developer's real data/ directory.
    """
    import os

    from app.config import get_settings

    data = tmp_path_factory.mktemp("data")
    os.environ["DATA_DIR"] = str(data)
    os.environ["DATABASE_URL"] = f"sqlite:///{(data / 'test.db').as_posix()}"
    get_settings.cache_clear()
    return data


@pytest.fixture
def write_step(tmp_path):
    """Write an OCC shape to a STEP file, so importers are tested via real files."""

    def _write(shape: TopoDS_Shape, name: str) -> Path:
        writer = STEPControl_Writer()
        Interface_Static.SetCVal_s("write.step.schema", "AP214")
        writer.Transfer(shape, STEPControl_AsIs)
        path = tmp_path / name
        writer.Write(str(path))
        return path

    return _write
