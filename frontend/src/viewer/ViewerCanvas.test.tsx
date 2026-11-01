import { createRef } from 'react';
import { act, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { IfcViewer } from './IfcViewer';
import { ViewerCanvas, type ViewerCanvasHandle } from './ViewerCanvas';

const viewerModule = vi.hoisted(() => ({ create: vi.fn() }));
vi.mock('./IfcViewer', () => ({ IfcViewer: { create: viewerModule.create } }));

const viewer = {
  syncHighlights: vi.fn(async (_selected: readonly string[], _issues: readonly string[]) => {}),
  clearSelection: vi.fn(async () => {}),
  fitModel: vi.fn(async () => {}),
  resetView: vi.fn(async () => {}),
  focusSelection: vi.fn(async (_globalIds: readonly string[]) => {}),
  dispose: vi.fn(),
} satisfies Pick<
  IfcViewer,
  'syncHighlights' | 'clearSelection' | 'fitModel' | 'resetView' | 'focusSelection' | 'dispose'
>;

const baseProps = {
  bytes: new ArrayBuffer(1),
  modelId: 'model-hash',
  selectedGlobalIds: [],
  highlightedGlobalIds: [],
  onGlobalIdsSelected: vi.fn(),
  onViewerError: vi.fn(),
  onLoadStateChange: vi.fn(),
};

describe('ViewerCanvas loading and controls', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('exposes geometry preparation and ready as observed loading states', async () => {
    let resolveViewer: (value: typeof viewer) => void = () => {
      throw new Error('Viewer creation was not requested.');
    };
    viewerModule.create.mockReturnValue(
      new Promise((resolve) => {
        resolveViewer = resolve;
      }),
    );

    render(<ViewerCanvas {...baseProps} />);

    expect(screen.getByRole('status')).toHaveTextContent('Preparing geometry');
    expect(baseProps.onLoadStateChange).toHaveBeenLastCalledWith('preparing');

    await act(async () => resolveViewer(viewer));

    expect(screen.getByRole('status')).toHaveTextContent('Ready');
    expect(baseProps.onLoadStateChange).toHaveBeenLastCalledWith('ready');
  });

  it('exposes a failed viewer state and preserves the error message', async () => {
    viewerModule.create.mockRejectedValue(new Error('Worker initialisation failed.'));

    render(<ViewerCanvas {...baseProps} />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Failed');
    expect(screen.getByRole('alert')).toHaveTextContent('Worker initialisation failed.');
    expect(baseProps.onLoadStateChange).toHaveBeenLastCalledWith('failed');
  });

  it('synchronizes application selection and issue highlights after changes', async () => {
    viewerModule.create.mockResolvedValue(viewer);
    const { rerender } = render(<ViewerCanvas {...baseProps} />);

    await screen.findByText('Ready');
    await act(async () => {
      rerender(
        <ViewerCanvas
          {...baseProps}
          selectedGlobalIds={['w-003']}
          highlightedGlobalIds={['w-003']}
        />,
      );
    });

    expect(viewer.syncHighlights).toHaveBeenLastCalledWith(['w-003'], ['w-003']);
  });

  it('forwards camera actions through its imperative control handle', async () => {
    viewerModule.create.mockResolvedValue(viewer);
    const ref = createRef<ViewerCanvasHandle>();

    render(<ViewerCanvas {...baseProps} ref={ref} />);
    await screen.findByText('Ready');

    await act(async () => {
      await ref.current?.fitModel();
      await ref.current?.resetView();
      await ref.current?.focusSelection(['w-002']);
      await ref.current?.clearSelection();
    });

    expect(viewer.fitModel).toHaveBeenCalledOnce();
    expect(viewer.resetView).toHaveBeenCalledOnce();
    expect(viewer.focusSelection).toHaveBeenCalledWith(['w-002']);
    expect(viewer.clearSelection).toHaveBeenCalledOnce();
  });
});
