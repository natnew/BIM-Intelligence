/// <reference types="node" />

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createElement, forwardRef, useEffect, useImperativeHandle } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
    expect(screen.queryByRole('button', { name: /ids:FireRating/ })).not.toBeInTheDocument();
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
