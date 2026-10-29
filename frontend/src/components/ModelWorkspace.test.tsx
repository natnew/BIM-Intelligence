import { createElement } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { fetchElement, loadReviewWorkspace, type ReviewWorkspaceData } from '../api/bim';
import type { ElementRecord, Finding } from '../api/generated/types';
import { ModelWorkspace } from './ModelWorkspace';

const globalId = '0QWMtUzsnUUONCUGc8Sqsa';
const etag = `"${'a'.repeat(64)}"`;
const finding: Finding = {
  id: 'finding-id',
  check_id: 'check-id',
  requirement_id: 'REQ-001',
  rule_id: 'ids:FireRating',
  rule_version: '1',
  facet_index: 0,
  severity: 'error',
  category: 'property_requirement',
  elements: [
    {
      global_id: globalId,
      express_id: 59,
      ifc_type: 'IfcWall',
      name: 'W-002',
      storey: 'L00',
    },
  ],
  observed: 'FireRating is missing.',
  expected: 'FireRating must be present.',
  method: 'ids',
};
const element: ElementRecord = {
  classifications: [],
  container: null,
  object_type: null,
  predefined_type: null,
  psets: {
    Pset_WallCommon: {
      FireRating: { inherited: false, value: '60' },
    },
  },
  ref: {
    global_id: globalId,
    express_id: 59,
    ifc_type: 'IfcWall',
    name: 'W-002',
    storey: 'L00',
  },
  type_ref: null,
};
const workspace: ReviewWorkspaceData = {
  sessionId: 'session-id',
  runId: 'run-id',
  summary: {
    ifc_schema: 'IFC4',
    model_hash: 'a'.repeat(64),
    project_name: 'Minimal fixture',
    counts: { IfcWall: 3 },
    storeys: [],
  },
  etag,
  bytes: new ArrayBuffer(3),
  run: {
    id: 'run-id',
    session_id: 'session-id',
    status: 'completed',
    plan: { checks: [] },
    plan_source: 'default',
    check_results: [],
    input_manifest: {
      model_hash: 'a'.repeat(64),
      ids_hashes: [],
      requirement_revisions: {},
      rule_versions: {},
    },
    created_at: '2026-10-29T00:00:00Z',
    finished_at: '2026-10-29T00:00:01Z',
  },
  findings: [finding],
};

vi.mock('../api/bim', () => ({
  fetchElement: vi.fn(),
  loadReviewWorkspace: vi.fn(),
}));

vi.mock('../viewer/ViewerCanvas', () => ({
  ViewerCanvas: (props: {
    readonly highlightedGlobalIds: string[];
    readonly onGlobalIdsSelected: (globalIds: string[]) => void;
  }) =>
    createElement(
      'div',
      { 'data-testid': 'viewer' },
      createElement(
        'output',
        { 'data-testid': 'highlighted-global-ids' },
        props.highlightedGlobalIds.join(','),
      ),
      createElement(
        'button',
        { onClick: () => props.onGlobalIdsSelected([globalId]) },
        'Select fixture wall',
      ),
    ),
}));

describe('ModelWorkspace selection coordination', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(loadReviewWorkspace).mockResolvedValue(workspace);
    vi.mocked(fetchElement).mockResolvedValue(element);
  });

  it('selects and highlights an affected model element when a finding is chosen', async () => {
    render(<ModelWorkspace initialSessionId="session-id" initialRunId="run-id" />);

    fireEvent.click(screen.getByRole('button', { name: 'Load review' }));
    const findingButton = await screen.findByRole('button', { name: /W-002/ });
    fireEvent.click(findingButton);

    expect(await screen.findByText('Pset_WallCommon.FireRating')).toBeInTheDocument();
    expect(findingButton).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('highlighted-global-ids')).toHaveTextContent(globalId);
    expect(fetchElement).toHaveBeenCalledWith(
      'session-id',
      globalId,
      etag,
      expect.any(AbortSignal),
    );
  });

  it('selects the matching finding when a model element is chosen', async () => {
    render(<ModelWorkspace initialSessionId="session-id" initialRunId="run-id" />);

    fireEvent.click(screen.getByRole('button', { name: 'Load review' }));
    await screen.findByRole('button', { name: /W-002/ });
    fireEvent.click(screen.getByRole('button', { name: 'Select fixture wall' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /W-002/ })).toHaveAttribute('aria-pressed', 'true');
    });
    expect(await screen.findByText('Pset_WallCommon.FireRating')).toBeInTheDocument();
    expect(fetchElement).toHaveBeenCalledWith(
      'session-id',
      globalId,
      etag,
      expect.any(AbortSignal),
    );
  });

  it('announces loading while the version-pinned review workspace is fetched', async () => {
    let resolveWorkspace: (value: ReviewWorkspaceData) => void = () => {
      throw new Error('Review request was not started.');
    };
    vi.mocked(loadReviewWorkspace).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveWorkspace = resolve;
        }),
    );
    render(<ModelWorkspace initialSessionId="session-id" initialRunId="run-id" />);

    fireEvent.click(screen.getByRole('button', { name: 'Load review' }));
    expect(screen.getByRole('status')).toHaveTextContent(/checking the run’s model version/i);

    resolveWorkspace(workspace);
    expect(await screen.findByRole('heading', { name: 'Findings' })).toBeInTheDocument();
  });

  it('shows an explicit empty state when the review has no findings', async () => {
    vi.mocked(loadReviewWorkspace).mockResolvedValue({ ...workspace, findings: [] });
    render(<ModelWorkspace initialSessionId="session-id" initialRunId="run-id" />);

    fireEvent.click(screen.getByRole('button', { name: 'Load review' }));

    expect(
      await screen.findByText('No findings were returned for this review run.'),
    ).toBeInTheDocument();
  });

  it('shows backend or version errors without presenting an empty review as success', async () => {
    vi.mocked(loadReviewWorkspace).mockRejectedValue(
      new Error('The review model version changed.'),
    );
    render(<ModelWorkspace initialSessionId="session-id" initialRunId="run-id" />);

    fireEvent.click(screen.getByRole('button', { name: 'Load review' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('The review model version changed.');
    expect(screen.queryByRole('heading', { name: 'Findings' })).not.toBeInTheDocument();
  });
});
