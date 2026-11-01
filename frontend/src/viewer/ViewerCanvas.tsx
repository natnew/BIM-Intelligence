import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';

import type { IfcViewer } from './IfcViewer';

export type ViewerLoadState = 'preparing' | 'ready' | 'failed';

export interface ViewerCanvasHandle {
  fitModel(): Promise<void>;
  resetView(): Promise<void>;
  focusSelection(globalIds: readonly string[]): Promise<void>;
  clearSelection(): Promise<void>;
}

interface ViewerCanvasProps {
  readonly bytes: ArrayBuffer;
  readonly modelId: string;
  readonly selectedGlobalIds: readonly string[];
  readonly highlightedGlobalIds: readonly string[];
  readonly onGlobalIdsSelected: (globalIds: string[]) => void;
  readonly onViewerError: (message: string) => void;
  readonly onLoadStateChange: (state: ViewerLoadState) => void;
}

type ViewerState =
  | { readonly kind: 'preparing' }
  | { readonly kind: 'ready' }
  | { readonly kind: 'failed'; readonly message: string };

export const ViewerCanvas = forwardRef<ViewerCanvasHandle, ViewerCanvasProps>(function ViewerCanvas(
  {
    bytes,
    modelId,
    selectedGlobalIds,
    highlightedGlobalIds,
    onGlobalIdsSelected,
    onViewerError,
    onLoadStateChange,
  },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<IfcViewer | null>(null);
  const [state, setState] = useState<ViewerState>({ kind: 'preparing' });
  const requireViewer = () => {
    const viewer = viewerRef.current;
    if (!viewer) {
      throw new Error('The IFC viewer is not ready.');
    }
    return viewer;
  };

  useImperativeHandle(
    ref,
    () => ({
      fitModel: async () => requireViewer().fitModel(),
      resetView: async () => requireViewer().resetView(),
      focusSelection: async (globalIds) => requireViewer().focusSelection(globalIds),
      clearSelection: async () => requireViewer().clearSelection(),
    }),
    [],
  );

  useEffect(() => {
    let cancelled = false;

    const container = containerRef.current;
    if (!container) {
      const message = 'The viewer container is unavailable.';
      setState({ kind: 'failed', message });
      onLoadStateChange('failed');
      return;
    }

    setState({ kind: 'preparing' });
    onLoadStateChange('preparing');
    void import('./IfcViewer')
      .then(({ IfcViewer: Viewer }) =>
        Viewer.create(container, bytes, modelId, {
          onGlobalIdsSelected,
          onError: onViewerError,
        }),
      )
      .then((viewer) => {
        if (cancelled) {
          viewer.dispose();
          return;
        }
        viewerRef.current = viewer;
        setState({ kind: 'ready' });
        onLoadStateChange('ready');
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        const message =
          error instanceof Error ? error.message : 'The IFC viewer could not be initialised.';
        setState({ kind: 'failed', message });
        onLoadStateChange('failed');
      });

    return () => {
      cancelled = true;
      viewerRef.current?.dispose();
      viewerRef.current = null;
    };
  }, [bytes, modelId, onGlobalIdsSelected, onLoadStateChange, onViewerError]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || state.kind !== 'ready') {
      return;
    }
    void viewer.syncHighlights(selectedGlobalIds, highlightedGlobalIds).catch((error: unknown) => {
      const message =
        error instanceof Error ? error.message : 'The selected GlobalId could not be highlighted.';
      onViewerError(message);
    });
  }, [highlightedGlobalIds, onViewerError, selectedGlobalIds, state.kind]);

  return (
    <section className="viewer" aria-label="Interactive IFC viewer">
      {state.kind === 'preparing' && (
        <p role="status" className="viewer__status">
          Preparing geometry…
        </p>
      )}
      {state.kind === 'ready' && (
        <p role="status" className="viewer__status">
          Ready
        </p>
      )}
      {state.kind === 'failed' && (
        <p role="alert" className="viewer__status viewer__status--error">
          Failed to prepare the model viewer: {state.message}
        </p>
      )}
      <div
        ref={containerRef}
        className="viewer__canvas"
        aria-label="3D IFC model; click an element to inspect it"
      />
    </section>
  );
});
