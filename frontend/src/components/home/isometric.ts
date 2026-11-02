/**
 * Minimal isometric projection for the Project Home workflow illustrations (UI-005B).
 * Pure functions only: model-space units become SVG point strings for a 200 × 120 viewBox.
 * The x axis runs down-right, y down-left and z up, so faces at the maximum x and y are visible.
 */

export type Point3 = readonly [x: number, y: number, z: number];

export interface Projection {
  readonly point: (p: Point3) => readonly [number, number];
  readonly points: (ps: readonly Point3[]) => string;
}

const COS_30 = Math.cos(Math.PI / 6);

export function projection(originX: number, originY: number, scale: number): Projection {
  const point = ([x, y, z]: Point3): readonly [number, number] => [
    round(originX + (x - y) * COS_30 * scale),
    round(originY + (x + y) * 0.5 * scale - z * scale),
  ];
  return {
    point,
    points: (ps) => ps.map((p) => point(p).join(',')).join(' '),
  };
}

export interface BoxFaces {
  readonly top: string;
  readonly left: string;
  readonly right: string;
}

/** The three visible faces of an axis-aligned box with its minimum corner at (x, y, z). */
export function boxFaces({ points }: Projection, [x, y, z]: Point3, [w, d, h]: Point3): BoxFaces {
  return {
    top: points([
      [x, y, z + h],
      [x + w, y, z + h],
      [x + w, y + d, z + h],
      [x, y + d, z + h],
    ]),
    left: points([
      [x, y + d, z],
      [x + w, y + d, z],
      [x + w, y + d, z + h],
      [x, y + d, z + h],
    ]),
    right: points([
      [x + w, y, z],
      [x + w, y + d, z],
      [x + w, y + d, z + h],
      [x + w, y, z + h],
    ]),
  };
}

function round(value: number): number {
  return Math.round(value * 10) / 10;
}
