"""Write the fixture pairs to STEP files.

    python -m app.testing.generate_testdata [output_dir]

Default output_dir is ../testdata relative to the repo. Each fixture yields
<name>_original.step and <name>_defeatured.step, plus a manifest.json listing
the expected features so a reviewer knows the ground truth.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from .fixtures import FIXTURES
from .step_io import write_step

DEFAULT_DIR = Path(__file__).resolve().parents[3] / "testdata"


def generate(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for fx in FIXTURES:
        t0 = time.perf_counter()
        orig = output_dir / f"{fx.name}_original.step"
        deft = output_dir / f"{fx.name}_defeatured.step"
        write_step(fx.original(), orig)
        write_step(fx.defeatured(), deft)
        dt = time.perf_counter() - t0
        manifest.append(
            {
                "name": fx.name,
                "description": fx.description,
                "original": orig.name,
                "defeatured": deft.name,
                "expected_features": [f.value for f in fx.expected_features],
                "expected_params": {k.value: v for k, v in fx.expected_params.items()},
            }
        )
        print(f"  {fx.name:20s} {dt*1000:6.0f} ms  {fx.description}")

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path


def main() -> None:
    output_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_DIR
    print(f"Generating {len(FIXTURES)} fixture pairs into {output_dir}")
    t0 = time.perf_counter()
    manifest = generate(output_dir)
    print(f"Done in {time.perf_counter()-t0:.2f}s. Manifest: {manifest}")


if __name__ == "__main__":
    main()
