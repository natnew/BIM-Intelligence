import { describe, expect, it } from 'vitest';

// Patterns that would indicate a credential or a direct model-provider call in frontend code.
// The frontend must only ever talk to the local API base URL (AGENTS.md §8).
const FORBIDDEN_PATTERNS: readonly RegExp[] = [
  /MODEL_API_KEY\s*[:=]/,
  /Authorization\s*:\s*['"`]Bearer\s+\S/,
  /\bsk-[A-Za-z0-9]{16,}/,
  /api\.llama\.com|graph\.facebook\.com|openai\.com\/v1|api\.openai\.com/,
  /LLM_BASE_URL/,
];

// Vite resolves this at transform time, so the test needs no Node file-system access.
const SOURCES = import.meta.glob(
  ['../**/*.ts', '../**/*.tsx', '../**/*.css', '!../**/*.test.ts', '!../**/*.test.tsx'],
  { query: '?raw', import: 'default', eager: true },
) as Record<string, string>;

describe('frontend source hygiene', () => {
  it('scans the application sources', () => {
    expect(Object.keys(SOURCES).length).toBeGreaterThan(10);
    expect(Object.keys(SOURCES).some((path) => path.endsWith('/ModelWorkspace.tsx'))).toBe(true);
  });

  it('contains no credentials or direct model-provider endpoints', () => {
    const offenders = Object.entries(SOURCES).flatMap(([path, text]) =>
      FORBIDDEN_PATTERNS.filter((pattern) => pattern.test(text)).map(
        (pattern) => `${path}: ${String(pattern)}`,
      ),
    );
    expect(offenders).toEqual([]);
  });
});
