import * as OBC from '@thatopen/components';
import * as OBF from '@thatopen/components-front';
import { RenderedFaces } from '@thatopen/fragments';
import * as THREE from 'three';
import fragmentsWorkerUrl from '@thatopen/fragments/worker?url';
import {
  excludeIssueGlobalIdsFromNeutralSelection,
  shouldPropagateSelectionClear,
} from './highlightSelection';

const ISSUE_STYLE = 'deterministic-issue';
const APPLICATION_SELECTION_STYLE = 'application-selection';
const POINTER_SELECTION_STYLE = 'select';

type CameraControls = NonNullable<OBC.OrthoPerspectiveCamera['controls']>;

interface CameraFrame {
  readonly sphere: THREE.Sphere;
  readonly centre: THREE.Vector3;
  readonly canonicalPosition: THREE.Vector3;
}

export interface IfcViewerCallbacks {
  readonly onGlobalIdsSelected: (globalIds: string[]) => void;
  readonly onError: (message: string) => void;
}

export class IfcViewer {
  private readonly components: OBC.Components;
  private readonly model: Awaited<ReturnType<OBC.IfcLoader['load']>>;
  private readonly highlighter: OBF.Highlighter;
  private readonly controls: CameraControls;
  private readonly cameraFrame: CameraFrame;
  private highlightRevision = 0;
  private focusRevision = 0;
  private selectionRevision = 0;
  private highlightQueue: Promise<void> = Promise.resolve();
  private focusQueue: Promise<void> = Promise.resolve();
  private suppressSelectionEvents = false;
  private disposed = false;

  private constructor(
    components: OBC.Components,
    model: Awaited<ReturnType<OBC.IfcLoader['load']>>,
    highlighter: OBF.Highlighter,
    controls: CameraControls,
    cameraFrame: CameraFrame,
  ) {
    this.components = components;
    this.model = model;
    this.highlighter = highlighter;
    this.controls = controls;
    this.cameraFrame = cameraFrame;
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
      highlighter.styles.set(POINTER_SELECTION_STYLE, {
        color: new THREE.Color('#167c79'),
        opacity: 0.48,
        transparent: true,
        renderedFaces: RenderedFaces.TWO,
        priority: 0,
      });
      highlighter.styles.set(APPLICATION_SELECTION_STYLE, {
        color: new THREE.Color('#167c79'),
        opacity: 0.48,
        transparent: true,
        renderedFaces: RenderedFaces.TWO,
        priority: 0,
      });
      highlighter.styles.set(ISSUE_STYLE, {
        color: new THREE.Color('#d9473f'),
        opacity: 1,
        transparent: false,
        renderedFaces: RenderedFaces.TWO,
        priority: 10,
      });

      const loader = components.get(OBC.IfcLoader);
      await loader.setup({
        autoSetWasm: false,
        wasm: { path: '/web-ifc/', absolute: true },
      });
      const model = await loader.load(new Uint8Array(bytes), true, modelId);
      await fragments.core.update(true);
      const cameraFrame = await frameModel(controls, model.object);

      const viewer = new IfcViewer(components, model, highlighter, controls, cameraFrame);
      viewer.connectSelectionEvents(fragments, callbacks);
      return viewer;
    } catch (error) {
      components.dispose();
      throw error;
    }
  }

  async syncHighlights(
    selectedGlobalIds: readonly string[],
    issueGlobalIds: readonly string[],
  ): Promise<void> {
    const revision = ++this.highlightRevision;
    this.focusRevision += 1;
    this.selectionRevision += 1;
    const selected = [...new Set(selectedGlobalIds)];
    const issues = [...new Set(issueGlobalIds)];
    const neutralSelection = excludeIssueGlobalIdsFromNeutralSelection(selected, issues);
    const update = async () => {
      if (!this.isCurrentHighlight(revision)) {
        return;
      }

      await this.clearPointerSelection();
      await Promise.all([
        this.highlighter.clear(APPLICATION_SELECTION_STYLE),
        this.highlighter.clear(ISSUE_STYLE),
      ]);
      if (!this.isCurrentHighlight(revision)) {
        return;
      }

      const selectionMap = await this.modelIdMapForGlobalIds(neutralSelection);
      if (!this.isCurrentHighlight(revision)) {
        return;
      }
      const issueMap = await this.modelIdMapForGlobalIds(issues);
      if (!this.isCurrentHighlight(revision)) {
        return;
      }

      if (selectionMap) {
        await this.highlighter.highlightByID(
          APPLICATION_SELECTION_STYLE,
          selectionMap,
          true,
          false,
        );
      }
      if (this.isCurrentHighlight(revision) && issueMap) {
        await this.highlighter.highlightByID(ISSUE_STYLE, issueMap, true, false);
      }
    };

    const operation = this.highlightQueue.then(update, update);
    this.highlightQueue = operation;
    return operation;
  }

  async clearSelection(): Promise<void> {
    this.selectionRevision += 1;
    await this.syncHighlights([], []);
  }

  async fitModel(): Promise<void> {
    await this.controls.fitToSphere(this.cameraFrame.sphere, true);
  }

  async resetView(): Promise<void> {
    const { canonicalPosition, centre } = this.cameraFrame;
    await this.controls.setLookAt(
      canonicalPosition.x,
      canonicalPosition.y,
      canonicalPosition.z,
      centre.x,
      centre.y,
      centre.z,
      true,
    );
  }

  focusSelection(globalIds: readonly string[]): Promise<void> {
    if (globalIds.length === 0) {
      return Promise.resolve();
    }

    const revision = ++this.focusRevision;
    const focus = async () => {
      if (!this.isCurrentFocus(revision)) {
        return;
      }

      const modelIdMap = await this.modelIdMapForGlobalIds(globalIds);
      if (!this.isCurrentFocus(revision)) {
        return;
      }
      if (!modelIdMap) {
        throw new Error('The selected GlobalId has no renderable geometry in this IFC model.');
      }

      const boxer = this.components.get(OBC.BoundingBoxer);
      boxer.list.clear();
      try {
        await boxer.addFromModelIdMap(modelIdMap);
        const bounds = boxer.get();
        if (bounds.isEmpty()) {
          throw new Error('The selected elements contain no renderable geometry.');
        }
        if (!this.isCurrentFocus(revision)) {
          return;
        }
        const sphere = bounds.getBoundingSphere(new THREE.Sphere());
        sphere.radius *= 1.45;
        await this.controls.fitToSphere(sphere, true);
      } finally {
        boxer.list.clear();
      }
    };

    const operation = this.focusQueue.then(focus, focus);
    this.focusQueue = operation;
    return operation;
  }

  dispose(): void {
    this.disposed = true;
    this.selectionRevision += 1;
    this.highlightRevision += 1;
    this.focusRevision += 1;
    this.components.dispose();
  }

  private connectSelectionEvents(
    fragments: OBC.FragmentsManager,
    callbacks: IfcViewerCallbacks,
  ): void {
    const selectionEvents = this.highlighter.events[this.highlighter.config.selectName];
    if (!selectionEvents) {
      throw new Error('The viewer selection events could not be initialised.');
    }

    selectionEvents.onHighlight.add((selection) => {
      const revision = ++this.selectionRevision;
      this.highlightRevision += 1;
      void resolveSelectedGlobalIds(fragments, selection)
        .then((globalIds) => {
          if (revision === this.selectionRevision && !this.disposed) {
            callbacks.onGlobalIdsSelected(globalIds);
          }
        })
        .catch((error: unknown) => {
          if (revision === this.selectionRevision && !this.disposed) {
            callbacks.onError(errorMessage(error));
          }
        });
    });
    selectionEvents.onClear.add(() => {
      if (!shouldPropagateSelectionClear(this.suppressSelectionEvents, this.disposed)) {
        return;
      }

      this.selectionRevision += 1;
      this.highlightRevision += 1;
      callbacks.onGlobalIdsSelected([]);
    });
  }

  private async modelIdMapForGlobalIds(
    globalIds: readonly string[],
  ): Promise<OBC.ModelIdMap | null> {
    if (globalIds.length === 0) {
      return null;
    }

    const localIds = await this.model.getLocalIdsByGuids([...new Set(globalIds)]);
    const matches = localIds.filter((localId): localId is number => localId !== null);
    if (matches.length === 0) {
      throw new Error('The selected GlobalId has no renderable geometry in this IFC model.');
    }
    return { [this.model.modelId]: new Set(matches) };
  }

  private async clearPointerSelection(): Promise<void> {
    let clearing: Promise<void>;
    this.suppressSelectionEvents = true;
    try {
      clearing = this.highlighter.clear(POINTER_SELECTION_STYLE);
    } finally {
      this.suppressSelectionEvents = false;
    }
    await clearing;
  }

  private isCurrentHighlight(revision: number): boolean {
    return revision === this.highlightRevision && !this.disposed;
  }

  private isCurrentFocus(revision: number): boolean {
    return revision === this.focusRevision && !this.disposed;
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

async function frameModel(controls: CameraControls, object: THREE.Object3D): Promise<CameraFrame> {
  const bounds = new THREE.Box3().setFromObject(object);
  if (bounds.isEmpty()) {
    throw new Error('The IFC model contains no renderable geometry.');
  }
  const centre = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const maxDimension = Math.max(size.x, size.y, size.z, 1);
  const distance = maxDimension * 1.8;
  const canonicalPosition = centre.clone().add(new THREE.Vector3(distance, distance, distance));
  const sphere = bounds.getBoundingSphere(new THREE.Sphere());

  controls.minDistance = maxDimension * 0.04;
  controls.maxDistance = maxDimension * 24;
  controls.minZoom = 0.02;
  controls.maxZoom = 50;
  controls.infinityDolly = false;
  controls.setBoundary(bounds.clone().expandByScalar(maxDimension * 4));
  await controls.setLookAt(
    canonicalPosition.x,
    canonicalPosition.y,
    canonicalPosition.z,
    centre.x,
    centre.y,
    centre.z,
    true,
  );
  return { sphere, centre, canonicalPosition };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'The viewer could not resolve the selection.';
}
