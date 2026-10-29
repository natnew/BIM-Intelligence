import { useEffect, useRef, useState } from 'react';

import type { IfcViewer } from './IfcViewer';

interface ViewerCanvasProps {
  readonly bytes: ArrayBuffer;
  readonly modelId: string;
  readonly highlightedGlobalIds: string[];
  readonly onGlobalIdsSelected: (globalIds: string[]) => void;
  readonly onViewerError: (message: string) => void;
}

type ViewerState =
  | { readonly kind: 'loading' }
  | { readonly kind: 'ready' }
  | { readonly kind: 'error'; readonly message: string };

export function ViewerCanvas({
  bytes,
  modelId,
  highlightedGlobalIds,
  onGlobalIdsSelected,
  onViewerError,
}: ViewerCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<IfcViewer | null>(null);
  const [state, setState] = useState<ViewerState>({ kind: 'loading' });

  useEffect(() => {
    let cancelled = false;

    const container = containerRef.current;
    if (!container) {
      setState({ kind: 'error', message: 'The viewer container is unavailable.' });
      return;
    }

    setState({ kind: 'loading' });
    void import('./IfcViewer')
      .then(({ IfcViewer: Viewer }) =>
        Viewer.create(container, bytes, modelId, {
          onGlobalIdsSelected,
          onError: (message) => {
            onViewerError(message);
          },
        }),
      )
      .then((viewer) => {
        if (cancelled) {
          viewer.dispose();
          return;
        }
        viewerRef.current = viewer;
        setState({ kind: 'ready' });
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        const message =
          error instanceof Error ? error.message : 'The IFC viewer could not be initialised.';
        setState({ kind: 'error', message });
      });

    return () => {
      cancelled = true;
      viewerRef.current?.dispose();
      viewerRef.current = null;
    };
  }, [bytes, modelId, onGlobalIdsSelected, onViewerError]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || state.kind !== 'ready') {
      return;
    }
    void viewer.highlightGlobalIds(highlightedGlobalIds).catch((error: unknown) => {
      const message =
        error instanceof Error ? error.message : 'The selected GlobalId could not be highlighted.';
      onViewerError(message);
    });
  }, [highlightedGlobalIds, onViewerError, state.kind]);

  return (
    <section className="viewer" aria-label="Interactive IFC viewer">
      {state.kind === 'loading' && (
        <p role="status" className="viewer__status">
          Converting IFC geometry for the viewer…
        </p>
      )}
      {state.kind === 'error' && (
        <p role="alert" className="viewer__status viewer__status--error">
          {state.message}
        </p>
      )}
      <div
        ref={containerRef}
        className="viewer__canvas"
        aria-label="3D IFC model; click an element to inspect it"
      />
    </section>
  );
}
