// Pure geometry helpers behind the 3D viewer's floor plane and footprint
// labels. They live outside Viewer.tsx so the arithmetic that decides where a
// label lands -- and how much depth precision the camera gets -- can be checked
// without a WebGL context.

/** Padding around a footprint, as a fraction of its larger side. */
const FOOTPRINT_PAD = 0.06;

export interface Extent {
  x: number;
  z: number;
}

export interface LabelPlacement {
  /** Rotation about Y, radians: 0 / 90° / 180° / 270°. */
  yaw: number;
  /** Outward normal of the chosen footprint edge, in the XZ plane. */
  dir: { x: number; z: number };
  /** Distance from the footprint centre to the label's baseline. */
  offset: number;
  fontSize: number;
  /** Padding used for the outline rectangle. */
  pad: number;
}

/**
 * Near/far planes around the current viewing distance.
 *
 * Depth-buffer precision follows far/near, not the absolute values: a ratio in
 * the tens of thousands (near 0.1 against a part 80 units across) is what makes
 * the grid and the part's bottom face flicker against each other at some
 * distances. A ratio of 500 spends the buffer where the geometry actually is.
 */
export function clipPlanes(distance: number): { near: number; far: number } {
  return { near: Math.max(distance / 50, 0.01), far: Math.max(distance, 0.01) * 10 };
}

/**
 * Height of the grid plane and of the floor labels riding just above it.
 *
 * `lowestY` is the lowest point of any model; passing null (nothing loaded yet)
 * falls back to the origin. Offsetting by a fraction of the scene size -- not
 * by a fixed hairline -- is what keeps the grid out of the part's bottom face:
 * STEP coordinates rarely put the part on y=0, and at part sizes of tens of
 * units a 0.01 gap is below what the depth buffer resolves.
 */
export function floorLevels(lowestY: number | null, sceneSize: number) {
  const floorY = (lowestY ?? 0) - sceneSize * 0.02;
  return { floorY, labelY: floorY + sceneSize * 0.005 };
}

/**
 * Which of the four footprint edges faces the camera, as a multiple of 90°.
 *
 * Snapping to four states is what makes the caption sit *on* an edge instead of
 * sliding along a circle around the part.
 */
export function quadrantOf(
  camera: { x: number; z: number },
  center: { x: number; z: number },
): number {
  const azimuth = Math.atan2(camera.x - center.x, camera.z - center.z);
  return ((Math.round(azimuth / (Math.PI / 2)) % 4) + 4) % 4;
}

/**
 * Where the caption for `quadrant` sits and how big it is.
 *
 * `yaw` and `dir` deliberately match: rotating the flat-laid text by `yaw`
 * turns its baseline across the viewing direction and points the glyph tops
 * away from the camera, so the label reads upright from that side.
 */
export function labelPlacement(
  quadrant: number,
  size: Extent,
  minFontSize: number,
): LabelPlacement {
  const yaw = (quadrant * Math.PI) / 2;
  const alongZ = quadrant % 2 === 0;
  const half = (alongZ ? size.z : size.x) / 2;
  const across = alongZ ? size.x : size.z;
  const pad = Math.max(size.x, size.z) * FOOTPRINT_PAD;
  const fontSize = Math.max(across * 0.11, minFontSize);
  return {
    yaw,
    // sin/cos of a right angle are 6e-17 rather than 0 in floating point;
    // rounding keeps the label exactly on its edge instead of a hair beside it.
    dir: { x: round(Math.sin(yaw)), z: round(Math.cos(yaw)) },
    offset: half + pad + fontSize * 0.9,
    fontSize,
    pad,
  };
}

/** Corner points (x/z) of the padded outline around a footprint. */
export function footprintCorners(
  min: Extent,
  max: Extent,
): Array<{ x: number; z: number }> {
  const pad = Math.max(max.x - min.x, max.z - min.z) * FOOTPRINT_PAD;
  const x0 = min.x - pad;
  const x1 = max.x + pad;
  const z0 = min.z - pad;
  const z1 = max.z + pad;
  return [
    { x: x0, z: z0 },
    { x: x1, z: z0 },
    { x: x1, z: z1 },
    { x: x0, z: z1 },
  ];
}

function round(value: number): number {
  return Math.abs(value) < 1e-12 ? 0 : value;
}
