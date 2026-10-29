import * as OBC from '@thatopen/components';
import * as OBF from '@thatopen/components-front';
import { RenderedFaces } from '@thatopen/fragments';
import * as THREE from 'three';
import fragmentsWorkerUrl from '@thatopen/fragments/worker?url';

const ISSUE_STYLE = 'deterministic-issue';

export interface IfcViewerCallbacks {
  readonly onGlobalIdsSelected: (globalIds: string[]) => void;
  readonly onError: (message: string) => void;
}

export class IfcViewer {
  private readonly components: OBC.Components;
  private readonly model: Awaited<ReturnType<OBC.IfcLoader['load']>>;
  private readonly highlighter: OBF.Highlighter;

  private constructor(
    components: OBC.Components,
    model: Awaited<ReturnType<OBC.IfcLoader['load']>>,
    highlighter: OBF.Highlighter,
  ) {
    this.components = components;
    this.model = model;
    this.highlighter = highlighter;
  }

  static async create(
    container: HTMLElement,
    bytes: ArrayBuffer,
    modelId: string,
    callbacks: IfcViewerCallbacks,
  ): Promise<IfcViewer> {
    const components = new OBC.Components();
    try {
      const world = components
        .get(OBC.Worlds)
        .create<OBC.SimpleScene, OBC.OrthoPerspectiveCamera, OBC.SimpleRenderer>();
      world.scene = new OBC.SimpleScene(components);
      world.scene.setup();
      world.scene.three.background = new THREE.Color('#f4f6f8');
      world.renderer = new OBC.SimpleRenderer(components, container);
      world.camera = new OBC.OrthoPerspectiveCamera(components);
      components.init();
      const camera = world.camera;
      const controls = camera.controls;
      if (!controls) {
        throw new Error('The IFC viewer camera controls could not be initialised.');
      }

      const fragments = components.get(OBC.FragmentsManager);
      fragments.init(fragmentsWorkerUrl);
      controls.addEventListener('update', () => fragments.core.update());
      fragments.list.onItemSet.add(({ value: model }) => {
        model.useCamera(camera.three);
        world.scene.three.add(model.object);
        fragments.core.update(true);
      });

      const highlighter = components.get(OBF.Highlighter);
      components.get(OBC.Raycasters).get(world);
      highlighter.setup({ world, selectEnabled: true, autoHighlightOnClick: true });
      highlighter.styles.set(ISSUE_STYLE, {
        color: new THREE.Color('#d9473f'),
        opacity: 1,
        transparent: false,
        renderedFaces: RenderedFaces.TWO,
        priority: 1,
      });

      const selectionEvents = highlighter.events[highlighter.config.selectName];
      if (!selectionEvents) {
        throw new Error('The viewer selection events could not be initialised.');
      }
      selectionEvents.onHighlight.add((selection) => {
        void resolveSelectedGlobalIds(fragments, selection)
          .then(callbacks.onGlobalIdsSelected)
          .catch((error: unknown) => callbacks.onError(errorMessage(error)));
      });
      selectionEvents.onClear.add(() => callbacks.onGlobalIdsSelected([]));

      const loader = components.get(OBC.IfcLoader);
      await loader.setup({
        autoSetWasm: false,
        wasm: { path: '/web-ifc/', absolute: true },
      });
      const model = await loader.load(new Uint8Array(bytes), true, modelId);
      await fragments.core.update(true);
      await frameModel(controls, model.object);

      return new IfcViewer(components, model, highlighter);
    } catch (error) {
      components.dispose();
      throw error;
    }
  }

  async highlightGlobalIds(globalIds: string[]): Promise<void> {
    await this.highlighter.clear(ISSUE_STYLE);
    if (globalIds.length === 0) {
      return;
    }

    const uniqueIds = [...new Set(globalIds)];
    const localIds = await this.model.getLocalIdsByGuids(uniqueIds);
    const matches = localIds.filter((localId): localId is number => localId !== null);
    if (matches.length === 0) {
      throw new Error('The selected GlobalId has no renderable geometry in this IFC model.');
    }

    await this.highlighter.highlightByID(
      ISSUE_STYLE,
      { [this.model.modelId]: new Set(matches) },
      true,
      true,
    );
  }

  dispose(): void {
    this.components.dispose();
  }
}

async function resolveSelectedGlobalIds(
  fragments: OBC.FragmentsManager,
  selection: OBC.ModelIdMap,
): Promise<string[]> {
  const selectedIds: string[] = [];
  for (const [modelId, localIds] of Object.entries(selection)) {
    const model = fragments.list.get(modelId);
    if (!model) {
      continue;
    }
    const globalIds = await model.getGuidsByLocalIds([...localIds]);
    selectedIds.push(...globalIds.filter((globalId): globalId is string => globalId !== null));
  }
  return [...new Set(selectedIds)];
}

async function frameModel(
  controls: NonNullable<OBC.OrthoPerspectiveCamera['controls']>,
  object: THREE.Object3D,
): Promise<void> {
  const bounds = new THREE.Box3().setFromObject(object);
  if (bounds.isEmpty()) {
    throw new Error('The IFC model contains no renderable geometry.');
  }
  const centre = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const distance = Math.max(size.x, size.y, size.z, 1) * 1.8;
  await controls.setLookAt(
    centre.x + distance,
    centre.y + distance,
    centre.z + distance,
    centre.x,
    centre.y,
    centre.z,
    true,
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'The viewer could not resolve the selection.';
}
