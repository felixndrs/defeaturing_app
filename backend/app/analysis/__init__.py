"""Analysis layer.

Allowed to touch OpenCascade (via the shape cache) for the few checks that need
the live solid, e.g. classifying a region as material added vs removed. The
comparison itself runs on the format-independent domain model, so a future mesh
importer feeds the same pipeline.
"""
