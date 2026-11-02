import type { ReactNode } from 'react';

import { boxFaces, projection, type Point3, type Projection } from './isometric';

export type WorkflowIllustrationKind = 'import' | 'validate' | 'investigate' | 'interpret';

interface WorkflowIllustrationProps {
  readonly kind: WorkflowIllustrationKind;
}

/**
 * Original isometric line drawings for the Project Home workflow cards (UI-005B). They are
 * decorative: each card's heading and text carry the meaning, so the SVG is hidden from
 * assistive technology. Solid outlines denote deterministic artefacts; the dashed outline in the
 * interpretation drawing marks AI output as separate from evidence.
 */
export function WorkflowIllustration({ kind }: WorkflowIllustrationProps) {
  return (
    <svg
      className="iso"
      viewBox="0 0 200 120"
      aria-hidden="true"
      focusable="false"
      data-illustration={kind}
    >
      {DRAWINGS[kind]()}
    </svg>
  );
}

const DRAWINGS: Record<WorkflowIllustrationKind, () => ReactNode> = {
  import: ImportDrawing,
  validate: ValidateDrawing,
  investigate: InvestigateDrawing,
  interpret: InterpretDrawing,
};

interface BoxProps {
  readonly p: Projection;
  readonly at: Point3;
  readonly size: Point3;
  readonly accent?: boolean;
}

function Box({ p, at, size, accent = false }: BoxProps) {
  const faces = boxFaces(p, at, size);
  return (
    <g className={accent ? 'iso-box iso-box--accent' : 'iso-box'}>
      <polygon className="iso-face iso-face--left" points={faces.left} />
      <polygon className="iso-face iso-face--right" points={faces.right} />
      <polygon className="iso-face iso-face--top" points={faces.top} />
    </g>
  );
}

interface SegProps {
  readonly p: Projection;
  readonly from: Point3;
  readonly to: Point3;
  readonly className?: string;
}

function Seg({ p, from, to, className = 'iso-line' }: SegProps) {
  const [x1, y1] = p.point(from);
  const [x2, y2] = p.point(to);
  return <line className={className} x1={x1} y1={y1} x2={x2} y2={y2} />;
}

function ImportDrawing() {
  const p = projection(99.4, 71.3, 7);
  const document: Point3[] = [
    [2, 5, 0.3],
    [5, 5, 0.3],
    [5, 5, 3.9],
    [4.3, 5, 4.6],
    [2, 5, 4.6],
  ];
  return (
    <>
      <Box p={p} at={[-6, -5, 0]} size={[12, 10, 0.3]} />
      <Box p={p} at={[-4, -3, 0.3]} size={[5, 4, 5]} />
      {[1.6, 2.9, 4.2].map((z) => (
        <Seg key={`l${z}`} p={p} from={[-3.5, 1, z]} to={[0.5, 1, z]} />
      ))}
      <Box p={p} at={[1, -3, 0.3]} size={[3, 3, 2.5]} />
      {[1.2, 2].map((z) => (
        <Seg key={`w${z}`} p={p} from={[1.5, 0, z]} to={[3.5, 0, z]} />
      ))}
      <polygon className="iso-sheet" points={p.points(document)} />
      <polygon
        className="iso-sheet iso-sheet--fold"
        points={p.points([
          [4.3, 5, 4.6],
          [4.3, 5, 3.9],
          [5, 5, 3.9],
        ])}
      />
      {[3.4, 2.7, 2.0, 1.3].map((z, index) => (
        <Seg
          key={`d${z}`}
          p={p}
          from={[2.5, 5, z]}
          to={[index === 3 ? 3.6 : 4.5, 5, z]}
          className="iso-line iso-line--accent"
        />
      ))}
    </>
  );
}

function ValidateDrawing() {
  const p = projection(82, 57, 8.4);
  const rows = [-2.4, 0, 2.4];
  return (
    <>
      <Box p={p} at={[-5, -4, 0]} size={[10, 8, 0.4]} />
      {rows.map((c, index) => {
        const square = p.points([
          [-4.2, c - 0.7, 0.4],
          [-2.8, c - 0.7, 0.4],
          [-2.8, c + 0.7, 0.4],
          [-4.2, c + 0.7, 0.4],
        ]);
        const checked = index < 2;
        return (
          <g key={c}>
            <polygon
              className={checked ? 'iso-check' : 'iso-check iso-check--open'}
              points={square}
            />
            {checked && (
              <polyline
                className="iso-tick"
                points={p.points([
                  [-3.9, c + 0.1, 0.4],
                  [-3.4, c + 0.4, 0.4],
                  [-3.0, c - 0.5, 0.4],
                ])}
              />
            )}
            <Seg p={p} from={[-2, c - 0.2, 0.4]} to={[3.8, c - 0.2, 0.4]} />
            <Seg p={p} from={[-2, c + 0.5, 0.4]} to={[1.6, c + 0.5, 0.4]} />
          </g>
        );
      })}
      <Box p={p} at={[7, -4.5, 0]} size={[2.6, 2.6, 3]} />
      <Box p={p} at={[7, -1.4, 0]} size={[2.6, 2.6, 1.6]} accent />
    </>
  );
}

function InvestigateDrawing() {
  const p = projection(94.4, 71.9, 7.56);
  const columns: Point3[] = [
    [-3.6, -2.6, 0.5],
    [-3.6, 1.9, 0.5],
    [2.9, -2.6, 0.5],
  ];
  const [cx, cy] = p.point([3.25, 2.25, 2.3]);
  return (
    <>
      <Box p={p} at={[-4, -3, 0]} size={[8, 6, 0.5]} />
      {columns.map((at) => (
        <Box key={at.join()} p={p} at={at} size={[0.7, 0.7, 3.5]} />
      ))}
      <Box p={p} at={[2.9, 1.9, 0.5]} size={[0.7, 0.7, 3.5]} accent />
      <Box p={p} at={[-4, -3, 4]} size={[8, 6, 0.5]} />
      <g className="iso-selection">
        <Box p={p} at={[2.6, 1.6, 0.5]} size={[1.3, 1.3, 3.5]} />
      </g>
      <circle className="iso-lens" cx={cx + 25} cy={cy + 5.5} r={18} />
      <line className="iso-lens-handle" x1={cx + 37.7} y1={cy + 18.2} x2={cx + 51} y2={cy + 31.5} />
      <line
        className="iso-line iso-line--accent"
        x1={cx + 4}
        y1={cy}
        x2={cx + 12.5}
        y2={cy + 2.8}
      />
    </>
  );
}

function InterpretDrawing() {
  const p = projection(111.5, 82, 7.28);
  const card: Point3[] = [
    [-3, -2.8, 2.6],
    [3, -2.8, 2.6],
    [3, -2.8, 6.8],
    [-3, -2.8, 6.8],
  ];
  const cited = [0.4, 2.2];
  return (
    <>
      <Box p={p} at={[-5, -2, 0]} size={[8, 6.4, 0.3]} />
      {[-0.8, 0.4, 1.3, 2.2, 3.1].map((y) => (
        <Seg
          key={y}
          p={p}
          from={[-4.2, y, 0.3]}
          to={[2.2, y, 0.3]}
          className={cited.includes(y) ? 'iso-line iso-line--accent' : 'iso-line'}
        />
      ))}
      {cited.map((y, index) => {
        const [ex, ey] = p.point([2.2, y, 0.3]);
        return (
          <g key={y}>
            <Seg
              p={p}
              from={[index === 0 ? -1.2 : 1.4, -2.8, 2.6]}
              to={[2.2, y, 0.3]}
              className="iso-line iso-line--link"
            />
            <circle className="iso-node" cx={ex} cy={ey} r={1.8} />
          </g>
        );
      })}
      <polygon className="iso-sheet iso-sheet--interpretation" points={p.points(card)} />
      {[5.9, 5.1, 4.3, 3.5].map((z, index) => (
        <Seg key={z} p={p} from={[-2.3, -2.8, z]} to={[index === 3 ? 0.2 : 2.3, -2.8, z]} />
      ))}
    </>
  );
}
