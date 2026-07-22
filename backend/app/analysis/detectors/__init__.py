"""Detector package.

Importing it registers every built-in detector. A new feature type is a new
module here plus the @register_detector decorator.
"""

from . import boss, chamfer, fillet, hole, pocket, rib, slot  # noqa: F401  (register)
from .base import FeatureCluster, available_detectors, register_detector  # noqa: F401
from .unknown import build_unknown  # noqa: F401
