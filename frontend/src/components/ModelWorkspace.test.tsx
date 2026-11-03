/// <reference types="node" />

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createElement, forwardRef, useEffect, useImperativeHandle } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  AIReviewRequestError,
  explainFinding,
  fetchElement,
  fetchRequirements,
  loadModel,
  loadReviewWorkspace,
  ModelVersionMismatchError,
  startObjectiveReview,
  startStandardReview,
  uploadDocument,
  type ReviewWorkspaceData,
  type VersionedModel,
} from '../api/bim';
import type {
  AIReviewFailure,
  ElementRecord,
  Explanation,
  Finding,
  Requirement,
} from '../api/generated/types';
import type { ViewerCanvasHandle } from '../viewer/ViewerCanvas';
import { ModelWorkspace } from './ModelWorkspace';

const globalId = '0QWMtUzsnUUONCUGc8Sqsa';
const w003GlobalId = '2qvnbd6oPPKR1ac5HegGTJ';
const w001GlobalId = '21KH8X9wHPWw7JLiY2NtSZ';
const modelHash = 'a'.repeat(64);
const etag = `"${modelHash}"`;
const viewerActions = vi.hoisted(() => ({
  fitModel: vi.fn(async () => undefined),
  resetView: vi.fn(async () => undefined),
  clearSelection: vi.fn(async () => undefined),
  focusSelection: vi.fn(async (_globalIds: readonly string[]) => undefined),
  syncHighlights: vi.fn(
    async (_selected: readonly string[], _issues: readonly string[]) => undefined,
  ),
}));
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
const w003Finding: Finding = {
  ...finding,
  id: 'finding-w003',
  requirement_id: 'REQ-002',
  rule_id: 'ids:Classification',
  elements: [
    {
      global_id: w003GlobalId,
      express_id: 60,
      ifc_type: 'IfcWall',
      name: 'W-003',
      storey: 'L00',
    },
  ],
  observed: 'Classification is missing.',
  expected: 'A classification reference must be present.',
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
const w003Element: ElementRecord = {
  ...element,
  ref: { ...element.ref, global_id: w003GlobalId, express_id: 60, name: 'W-003' },
};
const w001Element: ElementRecord = {
  ...element,
  ref: { ...element.ref, global_id: w001GlobalId, express_id: 58, name: 'W-001' },
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
    provenance: null,
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
  explainFinding: vi.fn(),
  fetchElement: vi.fn(),
  fetchRequirements: vi.fn(),
  loadModel: vi.fn(),
  loadReviewWorkspace: vi.fn(),
  startObjectiveReview: vi.fn(),
  startStandardReview: vi.fn(),
  uploadDocument: vi.fn(),
}));

vi.mock('../viewer/ViewerCanvas', () => ({
  ViewerCanvas: forwardRef<
    ViewerCanvasHandle,
    {
      readonly bytes: ArrayBuffer;
      readonly modelId: string;
      readonly selectedGlobalIds: readonly string[];
      readonly highlightedGlobalIds: readonly string[];
      readonly onGlobalIdsSelected: (globalIds: string[]) => void;
      readonly onViewerError: (message: string) => void;
      readonly onLoadStateChange: (state: 'preparing' | 'ready' | 'failed') => void;
    }
  >(
    (
      { modelId, selectedGlobalIds, highlightedGlobalIds, onGlobalIdsSelected, onLoadStateChange },
      ref,
    ) => {
      useImperativeHandle(
        ref,
        () => ({
          fitModel: viewerActions.fitModel,
          resetView: viewerActions.resetView,
          clearSelection: viewerActions.clearSelection,
          focusSelection: viewerActions.focusSelection,
        }),
        [],
      );
      useEffect(() => onLoadStateChange('ready'), [onLoadStateChange]);
      useEffect(() => {
        void viewerActions.syncHighlights(selectedGlobalIds, highlightedGlobalIds);
      }, [selectedGlobalIds, highlightedGlobalIds]);
      return createElement(
        'div',
        { 'data-testid': 'viewer', 'data-model-id': modelId },
        createElement(
          'output',
          { 'data-testid': 'selected-global-ids' },
          selectedGlobalIds.join(','),
        ),
        createElement(
          'output',
          { 'data-testid': 'highlighted-global-ids' },
          highlightedGlobalIds.join(','),
        ),
        createElement(
          'button',
          { onClick: () => onGlobalIdsSelected([globalId]) },
          'Select first model element',
        ),
        createElement(
          'button',
          { onClick: () => onGlobalIdsSelected([w003GlobalId]) },
          'Select second model element',
        ),
        createElement(
          'button',
          { onClick: () => onGlobalIdsSelected([w001GlobalId]) },
          'Select third model element',
        ),
        createElement(
          'button',
          { onClick: () => onLoadStateChange('preparing') },
          'Simulate viewer preparing',
        ),
        createElement(
          'button',
          { onClick: () => onLoadStateChange('failed') },
          'Simulate viewer failed',
        ),
      );
    },
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

describe('UI-004A desktop layout', () => {
  it('lets the viewer yield height to findings on short desktop screens', () => {
    const workspaceStyles = readFileSync(
      resolve(dirname(fileURLToPath(import.meta.url)), '..', 'index.css'),
      'utf8',
    );
    expect(workspaceStyles).toContain('@media (min-width: 70rem)');
    const style = document.createElement('style');
    style.textContent = workspaceStyles;
    document.head.append(style);

    try {
      const desktop = Array.from(style.sheet?.cssRules ?? []).find(
        (rule): rule is CSSMediaRule =>
          rule instanceof CSSMediaRule && rule.conditionText === '(min-width: 70rem)',
      );
      expect(desktop).toBeDefined();
      const viewer = Array.from(desktop?.cssRules ?? []).find(
        (rule): rule is CSSStyleRule =>
          rule instanceof CSSStyleRule && rule.selectorText === '.viewer',
      );

      expect(viewer).toBeDefined();
      expect(viewer?.style.minHeight).toBe('min(22rem, 30vh)');
    } finally {
      style.remove();
    }
  });
});

describe('ModelWorkspace model loading', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(loadModel).mockResolvedValue(model);
    vi.mocked(loadReviewWorkspace).mockResolvedValue(workspace);
    vi.mocked(startStandardReview).mockResolvedValue(workspace.run);
    vi.mocked(fetchElement).mockImplementation(async (_sessionId, selectedId) => {
      if (selectedId === w003GlobalId) {
        return w003Element;
      }
      if (selectedId === w001GlobalId) {
        return w001Element;
      }
      return element;
    });
    vi.mocked(fetchRequirements).mockResolvedValue([requirement]);
  });

  it('loads the active model version for a session without a run and shows real summary data', async () => {
    renderWorkspace(null);

    expect(screen.getByText('Downloading model…')).toBeInTheDocument();
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

    expect(await screen.findByRole('alert')).toHaveTextContent(/failed/i);
    expect(screen.getByRole('alert')).toHaveTextContent('Session has no model.');
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
    vi.mocked(fetchElement).mockImplementation(async (_sessionId, selectedId) => {
      if (selectedId === w003GlobalId) {
        return w003Element;
      }
      if (selectedId === w001GlobalId) {
        return w001Element;
      }
      return element;
    });
    vi.mocked(fetchRequirements).mockResolvedValue([requirement]);
  });

  it('selects and highlights an affected model element when a finding is chosen', async () => {
    renderWorkspace();

    const findingButton = await screen.findByRole('button', { name: /W-002/ });
    fireEvent.click(findingButton);

    await waitFor(() =>
      expect(fetchElement).toHaveBeenCalledWith(
        'session-id',
        globalId,
        etag,
        expect.any(AbortSignal),
      ),
    );
    expect(await screen.findByText('FireRating')).toBeInTheDocument();
    expect(findingButton).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('selected-global-ids')).toHaveTextContent(globalId);
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
    fireEvent.click(screen.getByRole('button', { name: 'Select first model element' }));

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

  it('clears finding and viewer selection together without resetting the camera', async () => {
    const user = userEvent.setup();
    renderWorkspace();

    const findingButton = await screen.findByRole('button', { name: /W-002/ });
    await user.click(findingButton);
    expect(await screen.findByText('FireRating')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Clear selection' }));

    expect(findingButton).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByTestId('selected-global-ids')).toBeEmptyDOMElement();
    expect(screen.getByTestId('highlighted-global-ids')).toBeEmptyDOMElement();
    expect(screen.queryByText('FireRating')).not.toBeInTheDocument();
    expect(viewerActions.clearSelection).toHaveBeenCalledOnce();
    expect(viewerActions.resetView).not.toHaveBeenCalled();
  });

  it.each(['preparing', 'failed'] as const)(
    'clears application selection while the viewer is %s',
    async (viewerState) => {
      const user = userEvent.setup();
      renderWorkspace();

      const findingButton = await screen.findByRole('button', { name: /W-002/ });
      await user.click(findingButton);
      await user.click(screen.getByRole('button', { name: `Simulate viewer ${viewerState}` }));
      await user.click(screen.getByRole('button', { name: 'Clear selection' }));

      expect(findingButton).toHaveAttribute('aria-pressed', 'false');
      expect(screen.getByTestId('selected-global-ids')).toBeEmptyDOMElement();
      expect(screen.getByTestId('highlighted-global-ids')).toBeEmptyDOMElement();
      expect(viewerActions.clearSelection).not.toHaveBeenCalled();
    },
  );

  it('clears model selection styling and inspector after a W-003 pointer selection', async () => {
    vi.mocked(loadReviewWorkspace).mockResolvedValue({
      ...workspace,
      findings: [finding, w003Finding],
    });
    const user = userEvent.setup();
    renderWorkspace();

    const w003FindingButton = await screen.findByRole('button', { name: /W-003/ });
    await user.click(screen.getByRole('button', { name: 'Select second model element' }));

    const inspector = screen.getByRole('complementary', { name: 'Evidence inspector' });
    await waitFor(() => expect(inspector).toHaveTextContent('W-003'));
    expect(w003FindingButton).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('selected-global-ids')).toHaveTextContent(w003GlobalId);
    expect(screen.getByTestId('highlighted-global-ids')).toHaveTextContent(w003GlobalId);

    await user.click(screen.getByRole('button', { name: 'Clear selection' }));

    expect(w003FindingButton).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByTestId('selected-global-ids')).toBeEmptyDOMElement();
    expect(screen.getByTestId('highlighted-global-ids')).toBeEmptyDOMElement();
    expect(inspector).not.toHaveTextContent('W-003');

    await user.click(w003FindingButton);
    expect(w003FindingButton).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('selected-global-ids')).toHaveTextContent(w003GlobalId);
    await user.click(screen.getByRole('button', { name: 'Clear selection' }));
    expect(w003FindingButton).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByTestId('selected-global-ids')).toBeEmptyDOMElement();
    expect(screen.getByTestId('highlighted-global-ids')).toBeEmptyDOMElement();
    expect(inspector).not.toHaveTextContent('W-003');
  });

  it('keeps W-001 selectable without assigning it a finding', async () => {
    vi.mocked(loadReviewWorkspace).mockResolvedValue({
      ...workspace,
      findings: [finding, w003Finding],
    });
    const user = userEvent.setup();
    renderWorkspace();

    await screen.findByRole('button', { name: /W-002/ });
    await user.click(screen.getByRole('button', { name: 'Select third model element' }));

    await waitFor(() =>
      expect(screen.getByTestId('selected-global-ids')).toHaveTextContent(w001GlobalId),
    );
    expect(await screen.findByText('W-001')).toBeInTheDocument();
    expect(screen.getByTestId('selected-global-ids')).toHaveTextContent(w001GlobalId);
    expect(screen.getByTestId('highlighted-global-ids')).toBeEmptyDOMElement();
    expect(screen.getByRole('complementary', { name: 'Evidence inspector' })).toHaveTextContent(
      'No finding in the loaded run references this element.',
    );
    expect(screen.queryByRole('button', { name: /W-001/ })).not.toBeInTheDocument();
  });

  it('keeps the latest selection while switching between finding and model paths', async () => {
    vi.mocked(loadReviewWorkspace).mockResolvedValue({
      ...workspace,
      findings: [finding, w003Finding],
    });
    const user = userEvent.setup();
    renderWorkspace();

    const w002FindingButton = await screen.findByRole('button', { name: /W-002/ });
    const w003FindingButton = screen.getByRole('button', { name: /W-003/ });
    await user.click(w002FindingButton);
    await user.click(screen.getByRole('button', { name: 'Select second model element' }));
    await user.click(w002FindingButton);

    expect(w002FindingButton).toHaveAttribute('aria-pressed', 'true');
    expect(w003FindingButton).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByTestId('selected-global-ids')).toHaveTextContent(globalId);
    expect(screen.getByTestId('highlighted-global-ids')).toHaveTextContent(globalId);
    expect(await screen.findByText('FireRating')).toBeInTheDocument();
  });

  it('supports keyboard activation of Fit, Reset and Focus Selected controls', async () => {
    const user = userEvent.setup();
    renderWorkspace();

    await screen.findByRole('button', { name: /W-002/ });
    const fitButton = screen.getByRole('button', { name: 'Fit model' });
    await waitFor(() => expect(fitButton).toBeEnabled());
    fitButton.focus();
    await user.keyboard('{Enter}');
    expect(viewerActions.fitModel).toHaveBeenCalledTimes(1);

    const resetButton = screen.getByRole('button', { name: 'Reset view' });
    resetButton.focus();
    await user.keyboard(' ');
    expect(viewerActions.resetView).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: /W-002/ }));
    const focusButton = screen.getByRole('button', { name: 'Focus selected' });
    focusButton.focus();
    await user.keyboard('{Enter}');
    expect(viewerActions.focusSelection).toHaveBeenCalledWith([globalId]);
  });

  it('focuses W-002 and W-003 using their selected model identities', async () => {
    const user = userEvent.setup();
    vi.mocked(loadReviewWorkspace).mockResolvedValue({
      ...workspace,
      findings: [finding, w003Finding],
    });
    renderWorkspace();

    const focusButton = await screen.findByRole('button', { name: 'Focus selected' });
    await user.click(screen.getByRole('button', { name: /W-002/ }));
    await user.click(focusButton);
    await user.click(screen.getByRole('button', { name: /W-003/ }));
    await user.click(focusButton);

    expect(viewerActions.focusSelection).toHaveBeenNthCalledWith(1, [globalId]);
    expect(viewerActions.focusSelection).toHaveBeenNthCalledWith(2, [w003GlobalId]);
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
    expect(inspector).toHaveTextContent(/Interpretation · not a Finding/i);
    expect(screen.getByRole('button', { name: 'Explain finding' })).toBeEnabled();
    expect(explainFinding).not.toHaveBeenCalled();
    expect(screen.queryByTestId('explanation-result')).not.toBeInTheDocument();
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

    expect(screen.queryByRole('button', { name: /ids:FireRating/ })).not.toBeInTheDocument();
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

    await act(async () => resolveWorkspace(workspace));
    expect(await screen.findByRole('button', { name: /W-002/ })).toBeInTheDocument();
  });

  it('does not request a plan until the user runs the default all-requirements objective', async () => {
    const { onRunChanged } = renderWorkspace(null);
    await screen.findByTestId('viewer');

    expect(startObjectiveReview).not.toHaveBeenCalled();
    expect(startStandardReview).not.toHaveBeenCalled();
    expect(screen.getByRole('radio', { name: 'Review all confirmed requirements' })).toBeChecked();
    vi.mocked(startObjectiveReview).mockResolvedValue(workspace.run);
    fireEvent.click(screen.getByRole('button', { name: 'Run AI Review' }));

    expect(await screen.findByRole('button', { name: /W-002/ })).toBeInTheDocument();
    expect(startObjectiveReview).toHaveBeenCalledWith(
      'session-id',
      'Review all confirmed requirements',
      expect.any(AbortSignal),
      {
        ai_required: true,
        continue_without_ai: false,
        selected_checks: [
          { check_id: 'check-id', requirement_id: 'REQ-001', requirement_revision: 1 },
        ],
      },
    );
    expect(startStandardReview).not.toHaveBeenCalled();
    expect(loadReviewWorkspace).toHaveBeenCalledWith(
      'session-id',
      'run-id',
      expect.any(AbortSignal),
    );
    expect(onRunChanged).toHaveBeenCalledWith('run-id');
    const coverage = screen.getByRole('region', { name: 'Review coverage' });
    expect(coverage).toHaveTextContent('Complete');
    expect(coverage).toHaveTextContent('Checks executed1 of 1');
    expect(coverage).toHaveTextContent(/provenance.*not recorded/i);
    expect(screen.getByRole('list', { name: 'Check coverage' })).toHaveTextContent('REQ-001');
    expect(coverage).toHaveTextContent(/not a compliance conclusion/i);
  });

  it('offers only current executable requirements and pins a custom objective to the selected scope', async () => {
    const secondRequirement: Requirement = {
      ...requirement,
      id: 'REQ-002',
      title: 'Classification reference present',
      check: { ...requirement.check, id: 'check-id-2', rule_id: 'ids:Classification' },
    };
    const unconfirmed: Requirement = {
      ...requirement,
      id: 'REQ-003',
      title: 'Unconfirmed requirement',
      status: 'proposed',
      confirmed_revision: null,
    };
    const stale: Requirement = {
      ...requirement,
      id: 'REQ-004',
      title: 'Outdated confirmation',
      revision: 2,
      confirmed_revision: 1,
    };
    vi.mocked(fetchRequirements).mockResolvedValue([
      requirement,
      secondRequirement,
      unconfirmed,
      stale,
    ]);
    vi.mocked(startObjectiveReview).mockResolvedValue(workspace.run);
    renderWorkspace(null);
    await screen.findByTestId('viewer');

    fireEvent.click(screen.getByRole('radio', { name: 'Choose requirements' }));
    expect(screen.getByRole('button', { name: 'Run AI Review' })).toBeDisabled();
    expect(screen.getByLabelText('Fire rating present')).toBeInTheDocument();
    expect(screen.getByLabelText('Classification reference present')).toBeInTheDocument();
    expect(screen.queryByLabelText('Unconfirmed requirement')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Outdated confirmation')).not.toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Classification reference present'));
    fireEvent.change(screen.getByLabelText('Describe another review objective'), {
      target: { value: 'Check classification data only' },
    });
    expect(startObjectiveReview).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Run AI Review' }));

    await screen.findByRole('button', { name: /W-002/ });
    expect(startObjectiveReview).toHaveBeenCalledWith(
      'session-id',
      'Check classification data only',
      expect.any(AbortSignal),
      {
        ai_required: true,
        continue_without_ai: false,
        selected_checks: [
          { check_id: 'check-id-2', requirement_id: 'REQ-002', requirement_revision: 1 },
        ],
      },
    );
  });

  it('deduplicates requirements that reference the same executable check', async () => {
    vi.mocked(fetchRequirements).mockResolvedValue([
      requirement,
      { ...requirement, id: 'REQ-DUPLICATE', title: 'Duplicate requirement' },
    ]);
    vi.mocked(startObjectiveReview).mockResolvedValue(workspace.run);
    renderWorkspace(null);
    await screen.findByTestId('viewer');

    expect(screen.getByText('1 of 1 confirmed checks in scope')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Run AI Review' }));

    await screen.findByRole('button', { name: /W-002/ });
    expect(startObjectiveReview).toHaveBeenCalledWith(
      'session-id',
      'Review all confirmed requirements',
      expect.any(AbortSignal),
      expect.objectContaining({
        selected_checks: [
          { check_id: 'check-id', requirement_id: 'REQ-001', requirement_revision: 1 },
        ],
      }),
    );
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
    expect(screen.queryByRole('button', { name: /ids:FireRating/ })).not.toBeInTheDocument();
    expect(loadModel).toHaveBeenCalledWith('session-id', expect.any(AbortSignal));
  });

  it('shows review errors without presenting an empty review as success', async () => {
    vi.mocked(startObjectiveReview).mockRejectedValue(
      new Error('Session has no executable checks.'),
    );
    renderWorkspace(null);
    await screen.findByTestId('viewer');

    fireEvent.click(screen.getByRole('button', { name: 'Run AI Review' }));

    expect(await screen.findByText('Session has no executable checks.')).toBeInTheDocument();
    expect(
      screen.getByText(/No findings are shown because the review did not complete/),
    ).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Review coverage' })).not.toBeInTheDocument();
  });

  it('disables AI review and explains how to add requirements when none are executable', async () => {
    vi.mocked(fetchRequirements).mockResolvedValue([
      { ...requirement, confirmed_revision: null, status: 'proposed' },
    ]);
    renderWorkspace(null);
    await screen.findByTestId('viewer');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Run AI Review' })).toBeDisabled();
    });
    expect(
      screen.getByText(
        'Add an IDS requirements file to run an information-quality review. You can still explore the IFC model in 3D.',
      ),
    ).toBeInTheDocument();
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
      expect(screen.getByRole('button', { name: 'Run AI Review' })).toBeDisabled();
    });

    const input = screen.getByLabelText('Add requirements document');
    fireEvent.change(input, { target: { files: [new File(['<ids/>'], 'minimal.ids')] } });

    expect(
      await screen.findByText(/minimal\.ids imported · 1 executable requirement/),
    ).toBeInTheDocument();
    expect(uploadDocument).toHaveBeenCalledWith('session-id', expect.any(File));
    expect(screen.getByRole('button', { name: 'Run AI Review' })).toBeEnabled();
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

const aiExplanation: Explanation = {
  finding_id: 'finding-id',
  source: 'ai_generated',
  grounding_status: 'passed',
  fallback_reason: null,
  model: 'fake-model',
  summary: 'The wall lacks a FireRating value.',
  probable_cause: 'The property set was not populated on export.',
  corrective_action: 'Populate Pset_WallCommon.FireRating before re-export.',
  citations: [
    {
      finding_id: 'finding-id',
      global_id: globalId,
      requirement_id: 'REQ-001',
      rule_id: 'ids:FireRating',
      observed: 'FireRating is missing.',
      expected: 'FireRating must be present.',
    },
  ],
};
const templateExplanation: Explanation = {
  ...aiExplanation,
  source: 'deterministic_template',
  grounding_status: 'fallback',
  fallback_reason: 'ai_disabled',
  model: null,
  summary: 'Deterministic summary of the finding.',
};

describe('UI-008 review objective dispatch and plan provenance', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(loadModel).mockResolvedValue(model);
    vi.mocked(loadReviewWorkspace).mockResolvedValue(workspace);
    vi.mocked(startStandardReview).mockResolvedValue(workspace.run);
    vi.mocked(startObjectiveReview).mockResolvedValue(workspace.run);
    vi.mocked(fetchElement).mockResolvedValue(element);
    vi.mocked(fetchRequirements).mockResolvedValue([requirement]);
  });

  it('attributes an accepted AI plan to persisted provenance on the run', async () => {
    const provenance = {
      ai_planning_requested: true,
      deterministic_fallback: false,
      executed_check_ids: ['check-id'],
      fallback_reason: null,
      mode: 'live' as const,
      model: 'muse-spark-1.3',
      outcome: 'accepted' as const,
      provider_request_attempted: true,
      selected_check_ids: ['check-id'],
    };
    vi.mocked(loadReviewWorkspace).mockResolvedValue({
      ...workspace,
      run: { ...workspace.run, plan_source: 'llm', provenance },
    });
    renderWorkspace(null);
    await screen.findByTestId('viewer');

    fireEvent.click(screen.getByRole('button', { name: 'Run AI Review' }));

    await screen.findByRole('button', { name: /W-002/ });
    const coverage = screen.getByRole('region', { name: 'Review coverage' });
    expect(coverage).toHaveTextContent('AI-selected plan');
    expect(coverage).toHaveTextContent('muse-spark-1.3');
    expect(coverage).toHaveTextContent('Live');
    expect(coverage).toHaveTextContent('Selected scope');
    expect(coverage).toHaveTextContent(/executed/i);
    fireEvent.click(screen.getByText('Scope and check selection'));
    expect(screen.getByRole('list', { name: 'User-selected check scope' })).toHaveTextContent(
      'REQ-001 · Fire rating present',
    );
    expect(screen.getByRole('list', { name: 'Checks selected by the plan' })).toHaveTextContent(
      'REQ-001 · Fire rating present',
    );
  });

  it('shows Replay from persisted run provenance', async () => {
    vi.mocked(loadReviewWorkspace).mockResolvedValue({
      ...workspace,
      run: {
        ...workspace.run,
        plan_source: 'llm',
        provenance: {
          ai_planning_requested: true,
          deterministic_fallback: false,
          executed_check_ids: ['check-id'],
          fallback_reason: null,
          mode: 'replay',
          model: 'replay-model',
          outcome: 'accepted',
          provider_request_attempted: true,
          selected_check_ids: ['check-id'],
        },
      },
    });
    renderWorkspace();

    await screen.findByRole('button', { name: /W-002/ });
    const coverage = screen.getByRole('region', { name: 'Review coverage' });
    expect(coverage).toHaveTextContent('Replay');
    expect(coverage).toHaveTextContent(/recorded response; no live call/i);
    expect(coverage).toHaveTextContent('replay-model');
    expect(coverage).not.toHaveTextContent('Live');
  });

  it('does not infer Replay for a historical run without persisted provenance', async () => {
    vi.mocked(loadReviewWorkspace).mockResolvedValue({
      ...workspace,
      run: { ...workspace.run, plan_source: 'llm', provenance: null },
    });
    renderWorkspace();

    await screen.findByRole('button', { name: /W-002/ });
    expect(screen.getByTestId('plan-source')).toHaveTextContent(/provenance not recorded/i);
    expect(screen.getByRole('region', { name: 'Review coverage' })).not.toHaveTextContent(/Replay/);
  });

  it('offers Retry AI Review and explicit deterministic continuation after a typed planning failure', async () => {
    const failure: AIReviewFailure = {
      mode: 'live',
      model: 'muse-spark-1.3',
      provider_request_attempted: true,
      reason_code: 'provider_unavailable',
    };
    vi.mocked(startObjectiveReview)
      .mockRejectedValueOnce(
        new AIReviewRequestError('The provider could not be reached.', 503, failure),
      )
      .mockRejectedValueOnce(
        new AIReviewRequestError('The provider could not be reached.', 503, failure),
      )
      .mockResolvedValueOnce(workspace.run);
    vi.mocked(loadReviewWorkspace).mockResolvedValue({
      ...workspace,
      run: {
        ...workspace.run,
        provenance: {
          ai_planning_requested: true,
          deterministic_fallback: true,
          executed_check_ids: ['check-id'],
          fallback_reason: 'user_selected_continue_without_ai',
          mode: 'off',
          model: null,
          outcome: 'continued_without_ai',
          provider_request_attempted: false,
          selected_check_ids: ['check-id'],
        },
      },
    });
    renderWorkspace(null);
    await screen.findByTestId('viewer');

    fireEvent.click(screen.getByRole('button', { name: 'Run AI Review' }));
    expect(await screen.findByText(/AI planning is unavailable/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry AI Review' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Continue without AI' })).toBeEnabled();
    expect(screen.queryByRole('region', { name: 'Review coverage' })).not.toBeInTheDocument();
    expect(startStandardReview).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Retry AI Review' }));
    await screen.findByRole('button', { name: 'Continue without AI' });
    expect(startObjectiveReview).toHaveBeenNthCalledWith(
      2,
      'session-id',
      'Review all confirmed requirements',
      expect.any(AbortSignal),
      {
        ai_required: true,
        continue_without_ai: false,
        selected_checks: [
          { check_id: 'check-id', requirement_id: 'REQ-001', requirement_revision: 1 },
        ],
      },
    );

    fireEvent.click(screen.getByRole('button', { name: 'Continue without AI' }));
    await screen.findByRole('button', { name: /W-002/ });
    expect(startObjectiveReview).toHaveBeenNthCalledWith(
      3,
      'session-id',
      'Review all confirmed requirements',
      expect.any(AbortSignal),
      {
        ai_required: true,
        continue_without_ai: true,
        selected_checks: [
          { check_id: 'check-id', requirement_id: 'REQ-001', requirement_revision: 1 },
        ],
      },
    );
    const coverage = screen.getByRole('region', { name: 'Review coverage' });
    expect(coverage).toHaveTextContent('User continued without AI');
    expect(coverage).toHaveTextContent('Off');
    expect(coverage).toHaveTextContent('user_selected_continue_without_ai');
  });

  it('explains that AI-off mode made no provider request', async () => {
    const failure: AIReviewFailure = {
      mode: 'off',
      model: null,
      provider_request_attempted: false,
      reason_code: 'provider_unavailable',
    };
    vi.mocked(startObjectiveReview).mockRejectedValue(
      new AIReviewRequestError('AI planning is unavailable in the configured mode.', 503, failure),
    );
    renderWorkspace(null);
    await screen.findByTestId('viewer');

    fireEvent.click(screen.getByRole('button', { name: 'Run AI Review' }));

    expect(
      await screen.findByText(/AI mode is Off; no provider request was made/i),
    ).toBeInTheDocument();
  });
});

describe('FINAL-UI-001 explanation requests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(loadModel).mockResolvedValue(model);
    vi.mocked(loadReviewWorkspace).mockResolvedValue({
      ...workspace,
      findings: [finding, w003Finding],
    });
    vi.mocked(startStandardReview).mockResolvedValue(workspace.run);
    vi.mocked(fetchElement).mockResolvedValue(element);
    vi.mocked(fetchRequirements).mockResolvedValue([requirement]);
    vi.mocked(explainFinding).mockResolvedValue(aiExplanation);
  });

  it('requests an explanation only on an explicit user action and renders AI provenance', async () => {
    renderWorkspace();

    fireEvent.click(await screen.findByRole('button', { name: /W-002/ }));
    expect(explainFinding).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Explain finding' }));

    const result = await screen.findByTestId('explanation-result');
    expect(explainFinding).toHaveBeenCalledTimes(1);
    expect(explainFinding).toHaveBeenCalledWith(
      'session-id',
      'run-id',
      'finding-id',
      etag,
      expect.any(AbortSignal),
    );
    expect(result).toHaveAttribute('data-source', 'ai_generated');
    expect(result).toHaveTextContent('AI interpretation · fake-model · grounding passed');
    expect(result).not.toHaveTextContent(/Replay/);
    expect(result).not.toHaveTextContent(/Meta/);
    expect(result).toHaveTextContent('The wall lacks a FireRating value.');
    expect(
      screen.getByRole('list', { name: 'Deterministic evidence cited by the explanation' }),
    ).toHaveTextContent(globalId);
    expect(screen.getByLabelText('2 findings in this run')).toHaveTextContent('2');
  });

  it('renders a deterministic template with its fallback reason and no model', async () => {
    vi.mocked(explainFinding).mockResolvedValue(templateExplanation);
    renderWorkspace();

    fireEvent.click(await screen.findByRole('button', { name: /W-002/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Explain finding' }));

    const result = await screen.findByTestId('explanation-result');
    expect(result).toHaveAttribute('data-source', 'deterministic_template');
    expect(result).toHaveTextContent('Deterministic template · AI not used');
    expect(result).toHaveTextContent('ai_disabled — AI is off.');
    expect(result).toHaveTextContent('Modelnone');
    expect(result).not.toHaveTextContent(/AI interpretation/);
  });

  it('FIX-003: describes a completion-token limit without claiming a spend or call limit', async () => {
    vi.mocked(explainFinding).mockResolvedValue({
      ...templateExplanation,
      fallback_reason: 'token_limit',
    });
    renderWorkspace();

    fireEvent.click(await screen.findByRole('button', { name: /W-002/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Explain finding' }));

    const result = await screen.findByTestId('explanation-result');
    expect(result).toHaveAttribute('data-source', 'deterministic_template');
    expect(result).toHaveTextContent('Deterministic template · AI not used');
    expect(result).toHaveTextContent(
      'token_limit — The AI explanation reached its completion-token limit. The verified finding remains available, and a deterministic explanation is shown instead.',
    );
    expect(result).not.toHaveTextContent(/spend or call limit/);
    expect(result).not.toHaveTextContent(/AI interpretation/);
    expect(result).toHaveTextContent('Modelnone');
  });

  it('does not infer Replay for an explanation from current health state', async () => {
    renderWorkspace();

    fireEvent.click(await screen.findByRole('button', { name: /W-002/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Explain finding' }));

    expect(await screen.findByTestId('explanation-result')).not.toHaveTextContent(/Replay/);
  });

  it('shows a 412 as a version error rather than an explanation', async () => {
    vi.mocked(explainFinding).mockRejectedValue(
      new ModelVersionMismatchError('The run belongs to a different model version.'),
    );
    renderWorkspace();

    fireEvent.click(await screen.findByRole('button', { name: /W-002/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Explain finding' }));

    const alert = await screen.findByText(/Explanation request failed \(412\)/);
    expect(alert).toHaveTextContent('The run belongs to a different model version.');
    expect(screen.queryByTestId('explanation-result')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Explain finding' })).toBeEnabled();
  });

  it('never displays a late explanation for a finding that is no longer selected', async () => {
    let resolveExplanation: (value: Explanation) => void = () => {
      throw new Error('Explanation request was not started.');
    };
    vi.mocked(explainFinding).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveExplanation = resolve;
        }),
    );
    renderWorkspace();

    fireEvent.click(await screen.findByRole('button', { name: /W-002/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Explain finding' }));
    expect(screen.getByText(/Requesting an explanation for/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /W-003/ }));
    await act(async () => resolveExplanation(aiExplanation));

    expect(screen.queryByTestId('explanation-result')).not.toBeInTheDocument();
    expect(screen.queryByText(/Requesting an explanation for/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Explain finding' })).toBeEnabled();
    const signal = vi.mocked(explainFinding).mock.calls[0]?.[4];
    expect(signal?.aborted).toBe(true);
  });

  it('reuses a cached explanation for the same finding without a second request', async () => {
    renderWorkspace();

    fireEvent.click(await screen.findByRole('button', { name: /W-002/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Explain finding' }));
    await screen.findByTestId('explanation-result');

    fireEvent.click(screen.getByRole('button', { name: /W-003/ }));
    expect(screen.queryByTestId('explanation-result')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /W-002/ }));
    expect(screen.getByTestId('explanation-result')).toHaveTextContent(
      /shown from this session’s earlier request/,
    );
    expect(explainFinding).toHaveBeenCalledTimes(1);
  });

  it('clears the explanation with the selection', async () => {
    renderWorkspace();

    fireEvent.click(await screen.findByRole('button', { name: /W-002/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Explain finding' }));
    await screen.findByTestId('explanation-result');

    fireEvent.click(screen.getByRole('button', { name: 'Clear selection' }));

    expect(screen.queryByTestId('explanation-panel')).not.toBeInTheDocument();
  });
});

describe('FINAL-UI-001 recent session recording', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    vi.mocked(loadModel).mockResolvedValue(model);
    vi.mocked(loadReviewWorkspace).mockResolvedValue(workspace);
    vi.mocked(startStandardReview).mockResolvedValue(workspace.run);
    vi.mocked(fetchElement).mockResolvedValue(element);
    vi.mocked(fetchRequirements).mockResolvedValue([requirement]);
  });

  it('remembers only the session and run identifiers of the opened workspace', async () => {
    renderWorkspace();
    await screen.findByRole('button', { name: /W-002/ });

    const stored = JSON.parse(window.localStorage.getItem('bimi.recent-sessions.v1') ?? '[]') as {
      sessionId: string;
      runId: string | null;
      openedAt: string;
    }[];
    expect(stored).toHaveLength(1);
    expect(stored[0]?.sessionId).toBe('session-id');
    expect(stored[0]?.runId).toBe('run-id');
    expect(Object.keys(stored[0] ?? {}).sort()).toEqual(['openedAt', 'runId', 'sessionId']);
    expect(window.localStorage.getItem('bimi.recent-sessions.v1')).not.toContain(modelHash);
    expect(window.localStorage.getItem('bimi.recent-sessions.v1')).not.toContain('Minimal fixture');
  });

  it('does not remember a run id that failed to load', async () => {
    vi.mocked(loadReviewWorkspace).mockRejectedValue(
      new ModelVersionMismatchError('This review run belongs to a different model version.'),
    );
    renderWorkspace('stale-run');
    await screen.findByTestId('viewer');

    const stored = JSON.parse(window.localStorage.getItem('bimi.recent-sessions.v1') ?? '[]') as {
      sessionId: string;
      runId: string | null;
    }[];
    expect(stored).toEqual([expect.objectContaining({ sessionId: 'session-id', runId: null })]);
  });
});
