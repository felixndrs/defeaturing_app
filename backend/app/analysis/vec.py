"""Small vector helpers on plain 3-tuples.

Kept dependency-free and local so the geometric reasoning in pairing and the
detectors reads directly, without pulling numpy semantics into the domain.
"""

from __future__ import annotations

import math

Vec3 = tuple[float, float, float]


def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def scale(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a: Vec3) -> float:
    return math.sqrt(dot(a, a))


def dist(a: Vec3, b: Vec3) -> float:
    return norm(sub(a, b))


def normalize(a: Vec3) -> Vec3:
    n = norm(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-12 else (0.0, 0.0, 0.0)


def canonical_dir(a: Vec3) -> Vec3:
    """Direction with a sign convention, so an axis and its reverse compare equal.

    A cylinder's axis has no intrinsic orientation; without this two faces on the
    same surface could fail to match just because OCC reported opposite normals.
    """
    v = normalize(a)
    for c in v:
        if abs(c) > 1e-9:
            if c < 0:
                return (-v[0], -v[1], -v[2])
            return v
    return v


def point_line_foot(point: Vec3, line_point: Vec3, direction: Vec3) -> Vec3:
    """Foot of the perpendicular from `point` onto the line."""
    d = normalize(direction)
    t = dot(sub(point, line_point), d)
    return add(line_point, scale(d, t))


def radial_dir(point: Vec3, axis_point: Vec3, axis_dir: Vec3) -> Vec3:
    """Unit vector from the axis to `point`, perpendicular to the axis."""
    foot = point_line_foot(point, axis_point, axis_dir)
    return normalize(sub(point, foot))
