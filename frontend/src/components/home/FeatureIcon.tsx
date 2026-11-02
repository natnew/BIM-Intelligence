import type { ReactNode } from 'react';

export type FeatureIconKind = 'viewer' | 'validation' | 'evidence' | 'interpretation';

const DRAWINGS: Record<FeatureIconKind, ReactNode> = {
  viewer: (
    <>
      <path d="M20 24 40 13 60 24 40 35 20 24Z" />
      <path d="M20 24v32l20 11 20-11V24M40 35v32" />
      <path d="m20 35 20 11 20-11M20 46l20 11 20-11" />
      <path d="M51 31v-6h6M68 25h6v6M74 51v6h-6M57 57h-6v-6" />
    </>
  ),
  validation: (
    <>
      <path d="M14 30 28 22 42 30 28 38 14 30Z" />
      <path d="M14 30v27l14 8 14-8V30M28 38v27" />
      <path d="m14 40 14 8 14-8M14 49l14 8 14-8" />
      <path d="M52 14h18l7 7v42H52zM70 14v7h7" />
      <path d="m57 30 2 2 4-5M66 30h6M57 41l2 2 4-5M66 41h6" />
      <path d="M57 50h5v5h-5zM66 53h6" />
    </>
  ),
  evidence: (
    <>
      <path d="M15 14h18l7 7v42H15zM33 14v7h7" />
      <path d="M21 29h13M21 36h13M21 43h9M21 50h8" />
      <path d="m58 31 12-7 12 7-12 7-12-7zM58 31v16l12 7 12-7V31M70 38v16" />
      <path d="m40 47 5 3M53 51l5-4" />
      <circle cx="49" cy="52" r="4" />
      <circle cx="70" cy="38" r="2" />
    </>
  ),
  interpretation: (
    <>
      <path d="M15 14h20l7 7v42H15zM35 14v7h7" />
      <path d="M21 29h15M21 36h15M21 43h11M21 50h9" />
      <path d="M45 39h10" strokeDasharray="2.5 3.5" />
      <circle cx="70" cy="39" r="14" />
      <path d="m63 42 5-7 6 6 4-8" />
      <circle cx="63" cy="42" r="1.5" />
      <circle cx="68" cy="35" r="1.5" />
      <circle cx="74" cy="41" r="1.5" />
      <circle cx="78" cy="33" r="1.5" />
    </>
  ),
};

interface FeatureIconProps {
  readonly kind: FeatureIconKind;
}

export function FeatureIcon({ kind }: FeatureIconProps) {
  return (
    <svg
      className="feature-icon"
      viewBox="0 0 96 76"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {DRAWINGS[kind]}
    </svg>
  );
}
