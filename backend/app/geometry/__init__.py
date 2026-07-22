"""Geometry export layer.

Like the importers, this package is allowed to touch OpenCascade. It turns a
solid into a GLB whose scene nodes are named by face id, so the frontend can map
a ray hit straight back to a face and the analysis can highlight faces.
"""
