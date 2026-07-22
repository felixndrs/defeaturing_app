"""Filesystem layout for uploads and generated artifacts.

Every path in the application is derived here. Moving to object storage later
means reimplementing this module, not hunting for hardcoded paths.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO

from ..config import get_settings


def _ensure(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_dir(project_id: str) -> Path:
    return _ensure(get_settings().upload_dir / project_id)


def artifact_dir(run_id: str) -> Path:
    return _ensure(get_settings().artifact_dir / run_id)


def save_upload(project_id: str, filename: str, stream: BinaryIO) -> Path:
    """Store an uploaded file, keeping only its basename."""
    safe_name = Path(filename).name
    target = project_dir(project_id) / safe_name
    with target.open("wb") as fh:
        shutil.copyfileobj(stream, fh)
    return target


def geometry_path(model_id: str) -> Path:
    return _ensure(get_settings().artifact_dir / "geometry") / f"{model_id}.glb"


def screenshot_path(run_id: str, feature_id: str, view: str) -> Path:
    return _ensure(artifact_dir(run_id) / "screenshots") / f"{feature_id}_{view}.png"


def report_path(run_id: str) -> Path:
    return artifact_dir(run_id) / "report.pdf"


def bundle_path(run_id: str) -> Path:
    return artifact_dir(run_id) / "review_bundle.zip"
