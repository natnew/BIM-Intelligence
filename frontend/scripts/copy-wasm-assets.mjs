import { copyFile, mkdir } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendDirectory = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const webIfcDirectory = join(frontendDirectory, 'node_modules', 'web-ifc');
const outputDirectory = join(frontendDirectory, 'public', 'web-ifc');

await mkdir(outputDirectory, { recursive: true });

for (const asset of ['web-ifc.wasm', 'web-ifc-mt.wasm']) {
  await copyFile(join(webIfcDirectory, asset), join(outputDirectory, asset));
}
