#!/usr/bin/env node
/**
 * Generate TypeScript contract types from the backend's exported JSON Schema (ADR-014).
 *
 *   node scripts/generate-types.mjs           # write src/api/generated/types.ts
 *   node scripts/generate-types.mjs --check   # exit 1 if types.ts is stale
 *
 * Input:  src/api/generated/bim_intelligence.schema.json (written by scripts/export_schemas.py
 *         at the repository root; the Python side has its own drift test).
 * Output: src/api/generated/types.ts (committed, so the frontend builds without Python).
 */

import { readFile, writeFile } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { compile } from 'json-schema-to-typescript';
import prettier from 'prettier';

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const schemaPath = resolve(frontendRoot, 'src/api/generated/bim_intelligence.schema.json');
const outputPath = resolve(frontendRoot, 'src/api/generated/types.ts');

const banner = `/* eslint-disable */
/**
 * GENERATED FILE — do not edit.
 *
 * Source: backend/bim_intelligence/schemas (Pydantic v2) → bim_intelligence.schema.json →
 * this file. Regenerate with \`python scripts/export_schemas.py\` at the repository root,
 * then \`npm run types:generate\` here. \`npm run types:check\` fails CI when stale.
 */`;

async function render() {
  const schema = JSON.parse(await readFile(schemaPath, 'utf8'));
  const raw = await compile(schema, schema.title, {
    bannerComment: banner,
    additionalProperties: false,
    strictIndexSignatures: true,
    format: false,
    // All contract fields are readonly on the frontend: generated API types are read-only.
    // (AGENTS.md §5)
    declareExternallyReferenced: true,
  });
  const readonly = raw.replace(/^(\s*)(?!readonly\b)(\w+\??:)/gm, '$1readonly $2');
  const prettierConfig = await prettier.resolveConfig(outputPath);
  return prettier.format(readonly, { ...prettierConfig, parser: 'typescript' });
}

async function main() {
  const check = process.argv.includes('--check');
  const rendered = await render();
  const shown = relative(frontendRoot, outputPath);

  if (check) {
    let current = null;
    try {
      current = await readFile(outputPath, 'utf8');
    } catch {
      current = null;
    }
    if (current === rendered) {
      console.log(`${shown}: up to date`);
      return 0;
    }
    console.error(`${shown}: stale - run \`npm run types:generate\``);
    return 1;
  }

  await writeFile(outputPath, rendered, 'utf8');
  console.log(`wrote ${shown} (${rendered.length} bytes)`);
  return 0;
}

process.exitCode = await main();
