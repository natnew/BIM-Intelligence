// FED-001 viewer-frame probe (feasibility only; not part of the production viewer).
//
// Loads each IFC with the installed web-ifc using the settings the existing viewer path uses
// (@thatopen/components IfcLoader -> FRAGS.IfcImporter with COORDINATE_TO_ORIGIN: true), then
// applies the @thatopen/fragments 3.6.0 `autoCoordinate` rule: every model after the first is
// translated by (base coordinates - own coordinates), where coordinates are the translation of
// web-ifc's GetCoordinationMatrix. It prints per-element axis-aligned bounds in that shared
// viewer frame so the Python runner can compare them with IfcOpenShell world geometry.
//
// Usage: node tests/feasibility/webifc_viewer_probe.mjs <modelId>=<path.ifc> [<modelId>=<path.ifc>]
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const frontendRequire = createRequire(resolve(here, '..', '..', 'frontend', 'package.json'));
const WebIFC = frontendRequire('web-ifc');
const wasmDir = dirname(frontendRequire.resolve('web-ifc'));
const webIfcVersion = JSON.parse(readFileSync(resolve(wasmDir, 'package.json'), 'utf8')).version;

function transformPoint(m, x, y, z) {
  return [
    m[0] * x + m[4] * y + m[8] * z + m[12],
    m[1] * x + m[5] * y + m[9] * z + m[13],
    m[2] * x + m[6] * y + m[10] * z + m[14],
  ];
}

function loadModel(api, modelId, path) {
  const bytes = new Uint8Array(readFileSync(path));
  const handle = api.OpenModel(bytes, { COORDINATE_TO_ORIGIN: true });
  const elements = new Map();
  api.StreamAllMeshes(handle, (mesh) => {
    const line = api.GetLine(handle, mesh.expressID);
    const record = elements.get(mesh.expressID) ?? {
      express_id: mesh.expressID,
      global_id: line.GlobalId?.value ?? null,
      ifc_type: api.GetNameFromTypeCode(line.type),
      min: [Infinity, Infinity, Infinity],
      max: [-Infinity, -Infinity, -Infinity],
    };
    const placed = mesh.geometries;
    for (let i = 0; i < placed.size(); i += 1) {
      const pg = placed.get(i);
      const geometry = api.GetGeometry(handle, pg.geometryExpressID);
      const vertices = api.GetVertexArray(geometry.GetVertexData(), geometry.GetVertexDataSize());
      for (let v = 0; v < vertices.length; v += 6) {
        const p = transformPoint(
          pg.flatTransformation,
          vertices[v],
          vertices[v + 1],
          vertices[v + 2],
        );
        for (let axis = 0; axis < 3; axis += 1) {
          record.min[axis] = Math.min(record.min[axis], p[axis]);
          record.max[axis] = Math.max(record.max[axis], p[axis]);
        }
      }
      geometry.delete();
    }
    elements.set(mesh.expressID, record);
  });
  const coordination = Array.from(api.GetCoordinationMatrix(handle));
  api.CloseModel(handle);
  return { model_id: modelId, coordination_matrix: coordination, elements: [...elements.values()] };
}

async function main() {
  const inputs = process.argv.slice(2).map((arg) => {
    const separator = arg.indexOf('=');
    if (separator <= 0) {
      throw new Error(`Expected <modelId>=<path>, received ${arg}`);
    }
    return { modelId: arg.slice(0, separator), path: arg.slice(separator + 1) };
  });
  if (inputs.length === 0) {
    throw new Error('At least one <modelId>=<path> argument is required.');
  }
  const api = new WebIFC.IfcAPI();
  api.SetWasmPath(`${wasmDir}/`, true);
  await api.Init();

  const models = inputs.map((input) => loadModel(api, input.modelId, input.path));
  // @thatopen/fragments autoCoordinate: the first loaded model defines the base coordinates.
  const base = models[0].coordination_matrix.slice(12, 15);
  for (const model of models) {
    const own = model.coordination_matrix.slice(12, 15);
    const delta = [base[0] - own[0], base[1] - own[1], base[2] - own[2]];
    model.fragments_translation = delta;
    for (const element of model.elements) {
      element.min = element.min.map((value, axis) => value + delta[axis]);
      element.max = element.max.map((value, axis) => value + delta[axis]);
    }
    model.elements.sort((a, b) => a.express_id - b.express_id);
  }
  process.stdout.write(
    `${JSON.stringify({
      web_ifc_version: webIfcVersion,
      import_settings: { COORDINATE_TO_ORIGIN: true },
      coordination_rule: '@thatopen/fragments autoCoordinate: translate by base - own',
      models,
    })}\n`,
  );
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(1);
});
