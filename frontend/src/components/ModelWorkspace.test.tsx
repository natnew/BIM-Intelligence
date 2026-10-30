import { createElement } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  fetchElement,
  fetchRequirements,
  loadModel,
  loadReviewWorkspace,
  ModelVersionMismatchError,
  startStandardReview,
  uploadDocument,
  type ReviewWorkspaceData,
  type VersionedModel,
} from '../api/bim';
import type { ElementRecord, Finding, Requirement } from '../api/generated/types';
import { ModelWorkspace } from './ModelWorkspace';

const globalId = '0QWMtUzsnUUONCUGc8Sqsa';
const modelHash = 'a'.repeat(64);
const etag = `"${modelHash}"`;
const finding: Finding = {
  id: 'finding-id',
  check_id: 'check-id',
  requirement_id: 'REQ-001',
  rule_id: 'ids:FireRating',
  rule_version: 'rule-v1',
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
const secondFinding: Finding = {
  ...finding,
  id: 'finding-2',
  severity: 'warning',
  rule_id: 'ids:LoadBearing',
  elements: [
    { global_id: 'other-gid', express_id: 60, ifc_type: 'IfcDoor', name: 'D-001', storey: 'L01' },
  ],
  observed: 'LoadBearing is missing.',
  expected: 'LoadBearing must be present.',
};
const element: ElementRecord = {
  classifications: [],
  container: null,
  object_type: null,
  predefined_type: null,
  psets: {
    Pset_WallCommon: {
      FireRating: { inherited: false, value: '60' },
      LoadBearing: { inherited: true, value: true },
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
const requirement: Requirement = {
  id: 'REQ-001',
  title: 'Fire rating present',
  statement: 'Every wall shall declare a FireRating.',
  origin: 'ids',
  status: 'confirmed',
  revision: 1,
  confirmed_revision: 1,
  confirmed_at: '2026-10-29T00:00:00Z',
  confirmed_by: 'ids-import',
  confidence: null,
  source: null,
  check: {
    id: 'check-id',
    kind: 'ids',
    rule_id: 'ids:FireRating',
    rule_version: 'rule-v1',
    params: {},
    ids_specification: null,
  },
};
const model: VersionedModel = {
  summary: {
    ifc_schema: 'IFC4',
    model_hash: modelHash,
    project_name: 'Minimal fixture',
    counts: { IfcWall: 3, IfcBuildingStorey: 1 },
    storeys: [
      {
        global_id: 'storey-gid',
        express_id: 10,
        ifc_type: 'IfcBuildingStorey',
        name: 'L00',
        storey: null,
      },
    ],
  },
  etag,
  bytes: new ArrayBuffer(3),
};
const workspace: ReviewWorkspaceData = {
  ...model,
  sessionId: 'session-id',
  runId: 'run-id',
  run: {
    id: 'run-id',
    session_id: 'session-id',
    status: 'completed',
    plan: { checks: [{ check_id: 'check-id', reason: 'default' }] },
    plan_source: 'default',
    check_results: [
      {
        check_id: 'check-id',
        requirement_id: 'REQ-001',
        status: 'failed',
        applicable_count: 3,
        finding_ids: ['finding-id'],
        diagnostics: [],
      },
    ],
    input_manifest: {
      model_hash: modelHash,
      ids_hashes: [],
      requirement_revisions: { 'REQ-001': 1 },
      rule_versions: {},
    },
    created_at: '2026-10-29T00:00:00Z',
    finished_at: '2026-10-29T00:00:01Z',
  },
  findings: [finding],
};

vi.mock('../api/bim', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/bim')>()),
  fetchElement: vi.fn(),
  fetchRequirements: vi.fn(),
  loadModel: vi.fn(),
  loadReviewWorkspace: vi.fn(),
  startStandardReview: vi.fn(),
  uploadDocument: vi.fn(),
}));

vi.mock('../viewer/ViewerCanvas', () => ({
  ViewerCanvas: (props: {
    readonly modelId: string;
    readonly highlightedGlobalIds: string[];
    readonly onGlobalIdsSelected: (globalIds: string[]) => void;
  }) =>
    createElement(
      'div',
      { 'data-testid': 'viewer', 'data-model-id': props.modelId },
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

function renderWorkspace(initialRunId: string | null = 'run-id') {
  const onRunChanged = vi.fn();
  const onReturnHome = vi.fn();
  render(
    <ModelWorkspace
      sessionId="session-id"
      initialRunId={initialRunId}
      onRunChanged={onRunChanged}
      onReturnHome={onReturnHome}
    />,
  );
  return { onRunChanged, onReturnHome };
}

describe('ModelWorkspace model loading', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(loadModel).mockResolvedValue(model);
    vi.mocked(loadReviewWorkspace).mockResolvedValue(workspace);
    vi.mocked(startStandardReview).mockResolvedValue(workspace.run);
    vi.mocked(fetchElement).mockResolvedValue(element);
    vi.mocked(fetchRequirements).mockResolvedValue([requirement]);
  });

  it('loads the active model version for a session without a run and shows real summary data', async () => {
    renderWorkspace(null);

    expect(screen.getByRole('status')).toHaveTextContent(/checking the active model version/i);
    expect(await screen.findByTestId('viewer')).toHaveAttribute('data-model-id', modelHash);
    expect(loadModel).toHaveBeenCalledWith('session-id', expect.any(AbortSignal));
    expect(loadReviewWorkspace).not.toHaveBeenCalled();

    const summary = screen.getByLabelText('Model summary');
    expect(summary).toHaveTextContent('Minimal fixture');
    expect(summary).toHaveTextContent('IFC4');
    expect(summary).toHaveTextContent(modelHash.slice(0, 12));
    expect(summary).toHaveTextContent('4 across 2 IFC classes');
    expect(screen.getByRole('list', { name: 'Building storeys in file order' })).toHaveTextContent(
      'L00',
    );
    expect(screen.getByRole('list', { name: 'Instance counts by IFC class' })).toHaveTextContent(
      'IfcWall3',
    );
    expect(
      screen.getByText('No review has run for this model version', { exact: false }),
    ).toBeInTheDocument();
  });

  it('shows the model error without a success-shaped workspace when the model cannot load', async () => {
    vi.mocked(loadModel).mockRejectedValue(new Error('Session has no model.'));
    renderWorkspace(null);

    expect(await screen.findByRole('alert')).toHaveTextContent('Session has no model.');
    expect(screen.queryByTestId('viewer')).not.toBeInTheDocument();
  });

  it('returns to Project Home from the review bar', async () => {
    const { onReturnHome } = renderWorkspace(null);
    await screen.findByTestId('viewer');

    fireEvent.click(screen.getByRole('button', { name: 'Return to Project Home' }));

    expect(onReturnHome).toHaveBeenCalledTimes(1);
  });
});

describe('ModelWorkspace selection coordination', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(loadModel).mockResolvedValue(model);
    vi.mocked(loadReviewWorkspace).mockResolvedValue(workspace);
    vi.mocked(startStandardReview).mockResolvedValue(workspace.run);
    vi.mocked(fetchElement).mockResolvedValue(element);
    vi.mocked(fetchRequirements).mockResolvedValue([requirement]);
  });

  it('selects and highlights an affected model element when a finding is chosen', async () => {
    renderWorkspace();

    const findingButton = await screen.findByRole('button', { name: /W-002/ });
    fireEvent.click(findingButton);

    expect(await screen.findByText('FireRating')).toBeInTheDocument();
    expect(findingButton).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('highlighted-global-ids')).toHaveTextContent(globalId);
    expect(fetchElement).toHaveBeenCalledWith(
      'session-id',
      globalId,
      etag,
      expect.any(AbortSignal),
    );
    expect(screen.getByText('inherited from type', { exact: false })).toBeInTheDocument();
  });

  it('selects the matching finding when a model element is chosen', async () => {
    renderWorkspace();

    await screen.findByRole('button', { name: /W-002/ });
    fireEvent.click(screen.getByRole('button', { name: 'Select fixture wall' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /W-002/ })).toHaveAttribute('aria-pressed', 'true');
    });
    expect(await screen.findByText('FireRating')).toBeInTheDocument();
    expect(fetchElement).toHaveBeenCalledWith(
      'session-id',
      globalId,
      etag,
      expect.any(AbortSignal),
    );
    expect(
      screen.getByRole('list', { name: 'Findings that reference this element' }),
    ).toHaveTextContent('ids:FireRating');
  });

  it('presents the finding’s canonical identity, evidence and source requirement unchanged', async () => {
    renderWorkspace();

    fireEvent.click(await screen.findByRole('button', { name: /W-002/ }));

    const inspector = screen.getByRole('complementary', { name: 'Evidence inspector' });
    expect(inspector).toHaveTextContent('finding-id');
    expect(inspector).toHaveTextContent('REQ-001');
    expect(inspector).toHaveTextContent('check-id');
    expect(inspector).toHaveTextContent('rule-v1');
    expect(inspector).toHaveTextContent('FireRating is missing.');
    expect(inspector).toHaveTextContent('FireRating must be present.');
    expect(inspector).toHaveTextContent('Deterministic finding · method ids');
    expect(inspector).toHaveTextContent('Every wall shall declare a FireRating.');
    expect(inspector).toHaveTextContent(/no narrative quotation/i);
    expect(inspector).toHaveTextContent(/AI explanation · not connected/i);
  });

  it('filters the register client-side without altering the run’s findings', async () => {
    vi.mocked(loadReviewWorkspace).mockResolvedValue({
      ...workspace,
      findings: [finding, secondFinding],
    });
    renderWorkspace();

    await screen.findByRole('button', { name: /W-002/ });
    expect(screen.getByRole('button', { name: /D-001/ })).toBeInTheDocument();

    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by severity' }), {
      target: { value: 'warning' },
    });

    expect(screen.queryByRole('button', { name: /W-002/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /D-001/ })).toBeInTheDocument();
    expect(screen.getByText(/Showing 1 of 2 findings/)).toBeInTheDocument();
    expect(screen.getByLabelText('2 findings in this run')).toHaveTextContent('2');
  });
});

describe('ModelWorkspace review execution and status', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(loadModel).mockResolvedValue(model);
    vi.mocked(loadReviewWorkspace).mockResolvedValue(workspace);
    vi.mocked(startStandardReview).mockResolvedValue(workspace.run);
    vi.mocked(fetchElement).mockResolvedValue(element);
    vi.mocked(fetchRequirements).mockResolvedValue([requirement]);
  });

  it('announces loading while a version-pinned review run is fetched', async () => {
    let resolveWorkspace: (value: ReviewWorkspaceData) => void = () => {
      throw new Error('Review request was not started.');
    };
    vi.mocked(loadReviewWorkspace).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveWorkspace = resolve;
        }),
    );
    renderWorkspace();

    expect(
      screen
        .getAllByRole('status')
        .map((node) => node.textContent)
        .join(' '),
    ).toMatch(/loading the review/i);

    resolveWorkspace(workspace);
    expect(await screen.findByRole('button', { name: /W-002/ })).toBeInTheDocument();
  });

  it('runs a deterministic review through the existing endpoint and reports coverage', async () => {
    const { onRunChanged } = renderWorkspace(null);
    await screen.findByTestId('viewer');

    fireEvent.click(screen.getByRole('button', { name: 'Run review' }));

    expect(await screen.findByRole('button', { name: /W-002/ })).toBeInTheDocument();
    expect(startStandardReview).toHaveBeenCalledWith('session-id', expect.any(AbortSignal));
    expect(loadReviewWorkspace).toHaveBeenCalledWith(
      'session-id',
      'run-id',
      expect.any(AbortSignal),
    );
    expect(onRunChanged).toHaveBeenCalledWith('run-id');
    const coverage = screen.getByRole('region', { name: 'Review coverage' });
    expect(coverage).toHaveTextContent('Complete');
    expect(coverage).toHaveTextContent('Checks executed1 of 1');
    expect(coverage).toHaveTextContent('Deterministic default');
    expect(screen.getByRole('list', { name: 'Check coverage' })).toHaveTextContent('REQ-001');
    expect(coverage).toHaveTextContent(/not a compliance conclusion/i);
  });

  it('shows an explicit empty state when the review has no findings', async () => {
    vi.mocked(loadReviewWorkspace).mockResolvedValue({ ...workspace, findings: [] });
    renderWorkspace();

    expect(
      await screen.findByText(/No findings were returned for this review run/),
    ).toBeInTheDocument();
    expect(screen.getByText(/does not by itself establish compliance/)).toBeInTheDocument();
  });

  it('does not hide partial coverage', async () => {
    vi.mocked(loadReviewWorkspace).mockResolvedValue({
      ...workspace,
      run: {
        ...workspace.run,
        status: 'partial',
        check_results: [
          ...workspace.run.check_results,
          {
            check_id: 'check-2',
            requirement_id: 'REQ-002',
            status: 'skipped',
            applicable_count: 0,
            finding_ids: [],
            diagnostics: ['Tool-call cap reached.'],
          },
        ],
      },
    });
    renderWorkspace();

    await screen.findByRole('button', { name: /W-002/ });
    const coverage = screen.getByRole('region', { name: 'Review coverage' });
    expect(coverage).toHaveTextContent('Complete · partial coverage');
    expect(coverage).toHaveTextContent('Not run1');
    expect(coverage).toHaveTextContent('Tool-call cap reached.');
    expect(screen.getByText(/Review partial · 1 finding/)).toBeInTheDocument();
  });

  it('represents a model-version mismatch while keeping the model viewable', async () => {
    vi.mocked(loadReviewWorkspace).mockRejectedValue(
      new ModelVersionMismatchError('This review run belongs to a different model version.'),
    );
    renderWorkspace('stale-run');

    expect(await screen.findByTestId('viewer')).toBeInTheDocument();
    const alerts = screen.getAllByRole('alert');
    expect(alerts.map((node) => node.textContent).join(' ')).toMatch(/Model version mismatch/);
    expect(alerts.map((node) => node.textContent).join(' ')).toMatch(
      /belongs to a different model version/,
    );
    expect(screen.queryByRole('button', { name: /W-002/ })).not.toBeInTheDocument();
    expect(loadModel).toHaveBeenCalledWith('session-id', expect.any(AbortSignal));
  });

  it('shows review errors without presenting an empty review as success', async () => {
    vi.mocked(startStandardReview).mockRejectedValue(
      new Error('Session has no executable checks.'),
    );
    renderWorkspace(null);
    await screen.findByTestId('viewer');

    fireEvent.click(screen.getByRole('button', { name: 'Run review' }));

    expect(await screen.findByText('Session has no executable checks.')).toBeInTheDocument();
    expect(
      screen.getByText(/No findings are shown because the review did not complete/),
    ).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Review coverage' })).not.toBeInTheDocument();
  });

  it('disables Run review when the session has no confirmed executable requirements', async () => {
    vi.mocked(fetchRequirements).mockResolvedValue([
      { ...requirement, confirmed_revision: null, status: 'proposed' },
    ]);
    renderWorkspace(null);
    await screen.findByTestId('viewer');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Run review' })).toBeDisabled();
    });
    expect(screen.getByText(/No confirmed executable requirements/)).toBeInTheDocument();
    expect(screen.getByText(/model view only/)).toBeInTheDocument();
  });

  it('adds an IDS from the workspace and refreshes the executable requirement count', async () => {
    vi.mocked(fetchRequirements).mockResolvedValueOnce([]).mockResolvedValueOnce([requirement]);
    vi.mocked(uploadDocument).mockResolvedValue({
      sha256: 'b'.repeat(64),
      kind: 'ids',
      title: 'Minimal IDS',
      requirements: [requirement],
    });
    renderWorkspace(null);
    await screen.findByTestId('viewer');
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Run review' })).toBeDisabled();
    });

    const input = screen.getByLabelText('Add requirements document');
    fireEvent.change(input, { target: { files: [new File(['<ids/>'], 'minimal.ids')] } });

    expect(
      await screen.findByText(/minimal\.ids imported · 1 executable requirement/),
    ).toBeInTheDocument();
    expect(uploadDocument).toHaveBeenCalledWith('session-id', expect.any(File));
    expect(screen.getByRole('button', { name: 'Run review' })).toBeEnabled();
  });

  it('rejects an unsupported requirements file type in the workspace without a request', async () => {
    renderWorkspace(null);
    await screen.findByTestId('viewer');

    fireEvent.change(screen.getByLabelText('Add requirements document'), {
      target: { files: [new File(['%PDF'], 'brief.pdf')] },
    });

    expect(
      await screen.findByText(/brief\.pdf" is not a supported requirements document/),
    ).toBeInTheDocument();
    expect(uploadDocument).not.toHaveBeenCalled();
  });
});
