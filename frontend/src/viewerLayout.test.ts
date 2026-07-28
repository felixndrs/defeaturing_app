import { describe, expect, it } from "vitest";
import {
  clipPlanes,
  floorLevels,
  footprintCorners,
  labelPlacement,
  quadrantOf,
} from "./viewerLayout";

describe("clipPlanes", () => {
  it("keeps the far/near ratio small enough for the depth buffer", () => {
    for (const distance of [1, 50, 200, 5000]) {
      const { near, far } = clipPlanes(distance);
      expect(far / near).toBeLessThanOrEqual(500);
    }
  });

  it("encloses the viewed geometry", () => {
    const { near, far } = clipPlanes(200);
    expect(near).toBeLessThan(200);
    expect(far).toBeGreaterThan(200);
  });

  it("never produces a zero or negative near plane", () => {
    expect(clipPlanes(0).near).toBeGreaterThan(0);
    expect(clipPlanes(0).far).toBeGreaterThan(clipPlanes(0).near);
  });
});

describe("floorLevels", () => {
  it("puts the floor below the lowest point of the part", () => {
    const { floorY } = floorLevels(12, 80);
    expect(floorY).toBeLessThan(12);
  });

  it("separates floor and part by more than a hairline at CAD scale", () => {
    // The bug: a fixed 0.01 gap against a part 80 units across is below what
    // the depth buffer resolves, so grid and bottom face flicker.
    const { floorY } = floorLevels(0, 80);
    expect(Math.abs(floorY)).toBeGreaterThan(0.5);
  });

  it("keeps labels above the grid but below the part", () => {
    const { floorY, labelY } = floorLevels(5, 80);
    expect(labelY).toBeGreaterThan(floorY);
    expect(labelY).toBeLessThan(5);
  });

  it("falls back to the origin while no model is loaded", () => {
    expect(floorLevels(null, 80).floorY).toBeLessThan(0);
  });
});

describe("quadrantOf", () => {
  const center = { x: 10, z: 4 };

  it("maps each side of the footprint to its own quadrant", () => {
    expect(quadrantOf({ x: 10, z: 100 }, center)).toBe(0); // +Z
    expect(quadrantOf({ x: 100, z: 4 }, center)).toBe(1); // +X
    expect(quadrantOf({ x: 10, z: -100 }, center)).toBe(2); // -Z
    expect(quadrantOf({ x: -100, z: 4 }, center)).toBe(3); // -X
  });

  it("stays within 0..3 for any azimuth", () => {
    for (let deg = 0; deg < 360; deg += 7) {
      const rad = (deg * Math.PI) / 180;
      const q = quadrantOf(
        { x: center.x + Math.sin(rad) * 50, z: center.z + Math.cos(rad) * 50 },
        center,
      );
      expect([0, 1, 2, 3]).toContain(q);
    }
  });

  it("switches side only near the diagonals", () => {
    // 44° off the +Z axis still reads from the +Z edge; 46° has moved on.
    const at = (deg: number) => {
      const rad = (deg * Math.PI) / 180;
      return quadrantOf(
        { x: center.x + Math.sin(rad) * 50, z: center.z + Math.cos(rad) * 50 },
        center,
      );
    };
    expect(at(44)).toBe(0);
    expect(at(46)).toBe(1);
  });
});

describe("labelPlacement", () => {
  const size = { x: 40, z: 20 };

  it("faces the label outward on the edge matching the quadrant", () => {
    expect(labelPlacement(0, size, 1).dir).toEqual({ x: 0, z: 1 });
    expect(labelPlacement(1, size, 1).dir).toEqual({ x: 1, z: 0 });
    expect(labelPlacement(2, size, 1).dir).toEqual({ x: 0, z: -1 });
    expect(labelPlacement(3, size, 1).dir).toEqual({ x: -1, z: 0 });
  });

  it("turns the text by the same angle it moves around the part", () => {
    // Placement direction and yaw must agree, otherwise the baseline no longer
    // runs across the viewing direction and the caption reads sideways.
    for (const quadrant of [0, 1, 2, 3]) {
      const { yaw, dir } = labelPlacement(quadrant, size, 1);
      expect(dir.x).toBeCloseTo(Math.sin(yaw), 10);
      expect(dir.z).toBeCloseTo(Math.cos(yaw), 10);
    }
  });

  it("clears the footprint on the axis it sits on", () => {
    // Front/back edges are half the Z extent away, left/right half the X.
    expect(labelPlacement(0, size, 1).offset).toBeGreaterThan(size.z / 2);
    expect(labelPlacement(1, size, 1).offset).toBeGreaterThan(size.x / 2);
  });

  it("scales the caption with the edge it is written along", () => {
    const front = labelPlacement(0, size, 1); // written across x = 40
    const side = labelPlacement(1, size, 1); // written across z = 20
    expect(front.fontSize).toBeGreaterThan(side.fontSize);
  });

  it("never falls below the readable minimum on a tiny part", () => {
    expect(labelPlacement(0, { x: 0.2, z: 0.2 }, 1.5).fontSize).toBe(1.5);
  });
});

describe("footprintCorners", () => {
  it("traces a rectangle around the bounding box, in order", () => {
    const corners = footprintCorners({ x: 0, z: 0 }, { x: 10, z: 4 });
    expect(corners).toHaveLength(4);
    // Consecutive corners share exactly one coordinate -- a closed rectangle,
    // not a bow tie.
    for (let i = 0; i < 4; i++) {
      const a = corners[i];
      const b = corners[(i + 1) % 4];
      expect(a.x === b.x || a.z === b.z).toBe(true);
    }
  });

  it("pads outward so the outline clears a vertical wall", () => {
    const corners = footprintCorners({ x: 0, z: 0 }, { x: 10, z: 4 });
    const xs = corners.map((c) => c.x);
    const zs = corners.map((c) => c.z);
    expect(Math.min(...xs)).toBeLessThan(0);
    expect(Math.max(...xs)).toBeGreaterThan(10);
    expect(Math.min(...zs)).toBeLessThan(0);
    expect(Math.max(...zs)).toBeGreaterThan(4);
  });
});
