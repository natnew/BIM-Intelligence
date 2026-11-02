import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from 'react';

import { ApiError } from '../api/client';
import {
  DOCUMENT_FILE_EXTENSIONS,
  MAX_REVIEW_OBJECTIVE_LENGTH,
  ModelVersionMismatchError,
  classifyUploadFile,
  explainFinding,
  fetchElement,
  fetchRequirements,
  isExecutableRequirement,
  loadModel,
  loadReviewWorkspace,
  startObjectiveReview,
  startStandardReview,
  uploadDocument,
  type VersionedModel,
} from '../api/bim';
import type { Explanation, Finding, Requirement, ReviewRun } from '../api/generated/types';
import { useHealth } from '../state/useHealth';
import {
  ViewerCanvas,
  type ViewerCanvasHandle,
  type ViewerLoadState,
} from '../viewer/ViewerCanvas';
import { AppHeader } from './AppHeader';
import {
  EvidenceInspector,
  type ElementLoadState,
  type ExplanationState,
} from './EvidenceInspector';
import { FindingRegister } from './FindingRegister';
import { ModelBrowser } from './ModelBrowser';
import { rememberRecentSession } from './ProjectHome';
import { ReviewCoverage } from './ReviewCoverage';

interface ModelWorkspaceProps {
  readonly sessionId: string;
  readonly initialRunId: string | null;
  readonly onRunChanged: (runId: string) => void;
  readonly onReturnHome: () => void;
}

type ModelState =
  | { readonly kind: 'loading' }
  | { readonly kind: 'ready'; readonly model: VersionedModel }
  | { readonly kind: 'error'; readonly message: string };

type ReviewState =
  | { readonly kind: 'none' }
  | { readonly kind: 'loading'; readonly runId: string }
  | { readonly kind: 'running'; readonly objective: string | null }
  | {
      readonly kind: 'ready';
      readonly run: ReviewRun;
      readonly findings: Finding[];
      /** Objective sent for this run; `null` for a standard review or a run opened by id. */
      readonly submittedObjective: string | null;
    }
  | { readonly kind: 'mismatch'; readonly runId: string; readonly message: string }
  | { readonly kind: 'error'; readonly message: string };

type RequirementsState =
  | { readonly kind: 'loading' }
  | { readonly kind: 'ready'; readonly items: Requirement[] }
  | { readonly kind: 'error'; readonly message: string };

type DocumentUploadState =
  | { readonly kind: 'idle' }
  | { readonly kind: 'uploading'; readonly filename: string }
  | { readonly kind: 'done'; readonly filename: string; readonly executable: number }
  | { readonly kind: 'error'; readonly message: string };

const NO_FINDINGS: Finding[] = [];

/** Explanations are cached per (session, run, model version, finding) for the workspace lifetime. */
function explanationCacheKey(
  sessionId: string,
  runId: string,
  etag: string,
  findingId: string,
): string {
  return `${sessionId}\u0000${runId}\u0000${etag}\u0000${findingId}`;
}

export function ModelWorkspace({
  sessionId,
  initialRunId,
  onRunChanged,
  onReturnHome,
}: ModelWorkspaceProps) {
  const [modelState, setModelState] = useState<ModelState>({ kind: 'loading' });
  const [reviewState, setReviewState] = useState<ReviewState>(
    initialRunId ? { kind: 'loading', runId: initialRunId } : { kind: 'none' },
  );
  const [requirementsState, setRequirementsState] = useState<RequirementsState>({
    kind: 'loading',
  });
  const [documentUpload, setDocumentUpload] = useState<DocumentUploadState>({ kind: 'idle' });
  const [objective, setObjective] = useState('');
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [selectedGlobalIds, setSelectedGlobalIds] = useState<string[]>([]);
  const [elementState, setElementState] = useState<ElementLoadState>({ kind: 'idle' });
  const [explanationState, setExplanationState] = useState<ExplanationState>({ kind: 'idle' });
  const [viewerError, setViewerError] = useState<string | null>(null);
  const [viewerLoadState, setViewerLoadState] = useState<ViewerLoadState>('preparing');
  const health = useHealth();
  const llmMode = health.kind === 'success' ? health.data.llm_mode : null;

  const reviewRequestRef = useRef<AbortController | null>(null);
  const elementRequestRef = useRef<AbortController | null>(null);
  const explanationRequestRef = useRef<AbortController | null>(null);
  const explanationCacheRef = useRef<Map<string, Explanation>>(new Map());
  const viewerRef = useRef<ViewerCanvasHandle | null>(null);
  // Refs let the viewer callbacks stay referentially stable, so the WebGL viewer is created once
  // per model version rather than on every state change.
  const etagRef = useRef<string | null>(null);
  const findingsRef = useRef<Finding[]>(NO_FINDINGS);

  const findings = reviewState.kind === 'ready' ? reviewState.findings : NO_FINDINGS;
  const run = reviewState.kind === 'ready' ? reviewState.run : null;
  const submittedObjective = reviewState.kind === 'ready' ? reviewState.submittedObjective : null;
  const model = modelState.kind === 'ready' ? modelState.model : null;

  useEffect(() => {
    etagRef.current = model?.etag ?? null;
    findingsRef.current = findings;
  }, [model, findings]);

  // Record the session as soon as it opens, and the run only once it has actually loaded, so a
  // stale or missing run id is never remembered as reopenable.
  useEffect(() => {
    rememberRecentSession(sessionId, run?.id ?? null);
  }, [sessionId, run]);

  const selectedFinding = findings.find((finding) => finding.id === selectedFindingId) ?? null;
  const explanationKey =
    model && run && selectedFinding
      ? explanationCacheKey(sessionId, run.id, model.etag, selectedFinding.id)
      : null;

  // Selection or version changes abort any in-flight request and can only ever show a cached
  // result for the new identity; nothing is requested without an explicit user action.
  useEffect(() => {
    explanationRequestRef.current?.abort();
    explanationRequestRef.current = null;
    const cached = explanationKey ? explanationCacheRef.current.get(explanationKey) : undefined;
    setExplanationState(
      cached ? { kind: 'ready', explanation: cached, fromCache: true } : { kind: 'idle' },
    );
  }, [explanationKey]);
  const highlightedGlobalIds = useMemo(
    () =>
      selectedFinding?.elements.flatMap((element) =>
        element.global_id ? [element.global_id] : [],
      ) ?? [],
    [selectedFinding],
  );
  const relatedFindings = useMemo(
    () =>
      selectedGlobalIds.length === 0
        ? []
        : findings.filter((finding) =>
            finding.elements.some(
              (element) =>
                element.global_id !== null && selectedGlobalIds.includes(element.global_id),
            ),
          ),
    [findings, selectedGlobalIds],
  );
  const executableCount =
    requirementsState.kind === 'ready'
      ? requirementsState.items.filter(isExecutableRequirement).length
      : null;

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;

    async function load() {
      try {
        if (initialRunId) {
          try {
            const loaded = await loadReviewWorkspace(sessionId, initialRunId, signal);
            if (signal.aborted) {
              return;
            }
            setModelState({
              kind: 'ready',
              model: { summary: loaded.summary, etag: loaded.etag, bytes: loaded.bytes },
            });
            setReviewState({
              kind: 'ready',
              run: loaded.run,
              findings: loaded.findings,
              submittedObjective: null,
            });
            return;
          } catch (caught) {
            if (signal.aborted) {
              return;
            }
            const fallback = await loadModel(sessionId, signal);
            if (signal.aborted) {
              return;
            }
            setModelState({ kind: 'ready', model: fallback });
            setReviewState(
              caught instanceof ModelVersionMismatchError
                ? { kind: 'mismatch', runId: initialRunId, message: caught.message }
                : { kind: 'error', message: messageForError(caught) },
            );
            return;
          }
        }
        const loaded = await loadModel(sessionId, signal);
        if (!signal.aborted) {
          setModelState({ kind: 'ready', model: loaded });
        }
      } catch (caught) {
        if (!signal.aborted) {
          setModelState({ kind: 'error', message: messageForError(caught) });
        }
      }
    }

    void load();
    void fetchRequirements(sessionId, signal)
      .then((items) => {
        if (!signal.aborted) {
          setRequirementsState({ kind: 'ready', items });
        }
      })
      .catch((caught: unknown) => {
        if (!signal.aborted) {
          setRequirementsState({ kind: 'error', message: messageForError(caught) });
        }
      });

    return () => {
      controller.abort();
      reviewRequestRef.current?.abort();
      elementRequestRef.current?.abort();
      explanationRequestRef.current?.abort();
    };
  }, [sessionId, initialRunId]);

  const loadElement = useCallback(
    (globalId: string | null) => {
      elementRequestRef.current?.abort();
      const etag = etagRef.current;
      if (!globalId || !etag) {
        setElementState({ kind: 'idle' });
        return;
      }
      const controller = new AbortController();
      elementRequestRef.current = controller;
      setElementState({ kind: 'loading', globalId });
      void fetchElement(sessionId, globalId, etag, controller.signal)
        .then((element) => {
          if (!controller.signal.aborted) {
            setElementState({ kind: 'ready', element });
          }
        })
        .catch((caught: unknown) => {
          if (!controller.signal.aborted) {
            setElementState({ kind: 'error', globalId, message: messageForError(caught) });
          }
        });
    },
    [sessionId],
  );

  const selectFromViewer = useCallback(
    (globalIds: string[]) => {
      const uniqueIds = [...new Set(globalIds)];
      const finding = findingsRef.current.find((candidate) =>
        candidate.elements.some(
          (element) => element.global_id !== null && uniqueIds.includes(element.global_id),
        ),
      );
      setSelectedGlobalIds(uniqueIds);
      setSelectedFindingId(finding?.id ?? null);
      loadElement(uniqueIds[0] ?? null);
    },
    [loadElement],
  );

  const handleViewerError = useCallback((message: string) => setViewerError(message), []);
  const handleViewerLoadStateChange = useCallback(
    (state: ViewerLoadState) => setViewerLoadState(state),
    [],
  );

  function runViewerAction(action: (viewer: ViewerCanvasHandle) => Promise<void>) {
    const viewer = viewerRef.current;
    if (!viewer) {
      return;
    }
    setViewerError(null);
    void action(viewer).catch((error: unknown) => handleViewerError(messageForError(error)));
  }

  function selectFinding(finding: Finding) {
    const globalIds = finding.elements.flatMap((element) =>
      element.global_id ? [element.global_id] : [],
    );
    setSelectedFindingId(finding.id);
    setSelectedGlobalIds(globalIds);
    loadElement(globalIds[0] ?? null);
  }

  function clearSelection() {
    elementRequestRef.current?.abort();
    if (viewerLoadState === 'ready') {
      runViewerAction((viewer) => viewer.clearSelection());
    }
    setSelectedFindingId(null);
    setSelectedGlobalIds([]);
    setElementState({ kind: 'idle' });
  }

  async function runReview() {
    reviewRequestRef.current?.abort();
    const controller = new AbortController();
    reviewRequestRef.current = controller;
    clearSelection();
    // A blank optional objective selects the standard deterministic review unchanged.
    const trimmedObjective = objective.trim();
    const requestedObjective = trimmedObjective.length > 0 ? trimmedObjective : null;
    setReviewState({ kind: 'running', objective: requestedObjective });
    try {
      const started =
        requestedObjective === null
          ? await startStandardReview(sessionId, controller.signal)
          : await startObjectiveReview(sessionId, requestedObjective, controller.signal);
      const loaded = await loadReviewWorkspace(sessionId, started.id, controller.signal);
      if (controller.signal.aborted) {
        return;
      }
      setModelState((previous) =>
        previous.kind === 'ready' && previous.model.summary.model_hash === loaded.summary.model_hash
          ? previous
          : {
              kind: 'ready',
              model: { summary: loaded.summary, etag: loaded.etag, bytes: loaded.bytes },
            },
      );
      setReviewState({
        kind: 'ready',
        run: loaded.run,
        findings: loaded.findings,
        submittedObjective: requestedObjective,
      });
      onRunChanged(started.id);
    } catch (caught) {
      if (!controller.signal.aborted) {
        setReviewState(
          caught instanceof ModelVersionMismatchError
            ? { kind: 'mismatch', runId: 'new run', message: caught.message }
            : { kind: 'error', message: messageForError(caught) },
        );
      }
    }
  }

  function requestExplanation() {
    if (!model || !run || !selectedFinding || !explanationKey) {
      return;
    }
    if (run.input_manifest.model_hash !== model.summary.model_hash) {
      return;
    }
    explanationRequestRef.current?.abort();
    const controller = new AbortController();
    explanationRequestRef.current = controller;
    const key = explanationKey;
    setExplanationState({ kind: 'loading' });
    void explainFinding(sessionId, run.id, selectedFinding.id, model.etag, controller.signal)
      .then((explanation) => {
        if (controller.signal.aborted) {
          return;
        }
        explanationCacheRef.current.set(key, explanation);
        setExplanationState({ kind: 'ready', explanation, fromCache: false });
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setExplanationState({
          kind: 'error',
          message: messageForError(caught),
          status: caught instanceof ApiError ? caught.status : undefined,
        });
      });
  }

  async function handleDocumentChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) {
      return;
    }
    const kind = classifyUploadFile(file.name);
    if (kind !== 'ids' && kind !== 'narrative') {
      setDocumentUpload({
        kind: 'error',
        message: `"${file.name}" is not a supported requirements document. Use ${DOCUMENT_FILE_EXTENSIONS.join(', ')}.`,
      });
      return;
    }
    setDocumentUpload({ kind: 'uploading', filename: file.name });
    try {
      const imported = await uploadDocument(sessionId, file);
      const items = await fetchRequirements(sessionId);
      setRequirementsState({ kind: 'ready', items });
      setDocumentUpload({
        kind: 'done',
        filename: file.name,
        executable: imported.requirements.filter(isExecutableRequirement).length,
      });
    } catch (caught) {
      setDocumentUpload({ kind: 'error', message: messageForError(caught) });
    }
  }

  const reviewBusy = reviewState.kind === 'running' || reviewState.kind === 'loading';
  const hasObjective = objective.trim().length > 0;
  const objectiveLength = [...objective].length;
  const canRun =
    model !== null &&
    !reviewBusy &&
    documentUpload.kind !== 'uploading' &&
    (executableCount === null || executableCount > 0);
  const runVersionMatches =
    model !== null && run !== null && run.input_manifest.model_hash === model.summary.model_hash;

  return (
    <div className="workspace-shell">
      <AppHeader
        view="workspace"
        sessionId={sessionId}
        onNavigateHome={onReturnHome}
        onNavigateWorkspace={null}
      >
        <button
          type="button"
          className="button button--primary"
          disabled={!canRun}
          onClick={() => void runReview()}
          title={
            executableCount === 0
              ? 'Add an IDS with confirmed requirements before running a review'
              : hasObjective
                ? 'Starts an objective-aware review; the plan may be narrowed to suit the objective'
                : 'Starts the deterministic default review'
          }
        >
          {reviewState.kind === 'running'
            ? 'Running review…'
            : hasObjective
              ? 'Run review with objective'
              : 'Run review'}
        </button>
      </AppHeader>

      <div className="review-bar" aria-label="Review status">
        {model ? (
          <>
            <span className="review-bar__item">
              <span className="review-bar__label">Model</span>{' '}
              {model.summary.project_name ?? 'Unnamed project'} · {model.summary.ifc_schema} ·{' '}
              <code title={model.summary.model_hash}>{model.summary.model_hash.slice(0, 12)}</code>
            </span>
            <ReviewStatusChip state={reviewState} executableCount={executableCount} />
          </>
        ) : (
          <span className="review-bar__item">
            {modelState.kind === 'loading'
              ? 'Loading the active model version…'
              : 'Model unavailable'}
          </span>
        )}
        <button type="button" className="button button--ghost" onClick={onReturnHome}>
          Return to Project Home
        </button>
      </div>

      {modelState.kind === 'loading' && (
        <p role="status" className="notice workspace-shell__notice">
          {reviewState.kind === 'loading'
            ? 'Downloading model and loading the review data for the requested run…'
            : 'Downloading model…'}
        </p>
      )}
      {modelState.kind === 'error' && (
        <div className="workspace-shell__notice">
          <p role="alert" className="notice notice--error">
            Failed to load model: {modelState.message}
          </p>
          <p className="notice">
            The session may have no uploaded model yet. Return to Project Home to upload one or open
            a different session.
          </p>
        </div>
      )}

      {model && (
        <main className="workspace-grid" id="main">
          <ModelBrowser summary={model.summary} />

          <section className="viewport" aria-labelledby="viewport-heading">
            <div className="viewport__head">
              <h2 id="viewport-heading">3D model</h2>
              <p className="viewport__hints">
                Left-drag orbit · right-drag pan · wheel zoom · click an element to inspect it.
              </p>
              <div className="viewport__actions" role="group" aria-label="Camera controls">
                <button
                  type="button"
                  className="button button--ghost"
                  disabled={viewerLoadState !== 'ready'}
                  onClick={() => runViewerAction((viewer) => viewer.fitModel())}
                >
                  Fit model
                </button>
                <button
                  type="button"
                  className="button button--ghost"
                  disabled={viewerLoadState !== 'ready'}
                  onClick={() => runViewerAction((viewer) => viewer.resetView())}
                >
                  Reset view
                </button>
                <button
                  type="button"
                  className="button button--ghost"
                  disabled={viewerLoadState !== 'ready' || selectedGlobalIds.length === 0}
                  onClick={() =>
                    runViewerAction((viewer) => viewer.focusSelection(selectedGlobalIds))
                  }
                >
                  Focus selected
                </button>
              </div>
              {selectedGlobalIds.length > 0 && (
                <button type="button" className="button button--ghost" onClick={clearSelection}>
                  Clear selection
                </button>
              )}
            </div>
            {viewerError && (
              <p role="alert" className="notice notice--error viewport__error">
                {viewerError}
              </p>
            )}
            <ViewerCanvas
              ref={viewerRef}
              bytes={model.bytes}
              modelId={model.summary.model_hash}
              selectedGlobalIds={selectedGlobalIds}
              highlightedGlobalIds={highlightedGlobalIds}
              onGlobalIdsSelected={selectFromViewer}
              onViewerError={handleViewerError}
              onLoadStateChange={handleViewerLoadStateChange}
            />
            {reviewState.kind === 'ready' ? (
              <FindingRegister
                findings={findings}
                selectedFindingId={selectedFindingId}
                onSelect={selectFinding}
              />
            ) : (
              <section className="register register--empty" aria-labelledby="findings-heading">
                <div className="panel-heading">
                  <h2 id="findings-heading">Findings</h2>
                </div>
                <ReviewPlaceholder state={reviewState} executableCount={executableCount} />
              </section>
            )}
          </section>

          <div className="workspace-side">
            <section className="review-controls" aria-labelledby="review-controls-heading">
              <div className="panel-heading">
                <h3 id="review-controls-heading">Requirements</h3>
                <span className="panel-heading__hint">
                  {requirementsState.kind === 'loading' && 'Loading…'}
                  {requirementsState.kind === 'error' && 'Unavailable'}
                  {requirementsState.kind === 'ready' &&
                    `${executableCount ?? 0} executable of ${requirementsState.items.length}`}
                </span>
              </div>
              {requirementsState.kind === 'error' && (
                <p role="alert" className="notice notice--error">
                  {requirementsState.message}
                </p>
              )}
              {requirementsState.kind === 'ready' && executableCount === 0 && (
                <p className="notice">
                  No confirmed executable requirements. The model can be viewed, but no
                  deterministic review can run until an IDS is added.
                </p>
              )}
              <label className="file-field file-field--compact">
                <span className="file-field__label">Add requirements document</span>
                <input
                  type="file"
                  accept=".ids,.md,.txt"
                  disabled={documentUpload.kind === 'uploading' || reviewBusy}
                  onChange={(event) => void handleDocumentChange(event)}
                />
              </label>
              {documentUpload.kind === 'uploading' && (
                <p role="status" className="notice">
                  Uploading {documentUpload.filename}…
                </p>
              )}
              {documentUpload.kind === 'done' && (
                <p role="status" className="notice">
                  {documentUpload.filename} imported ·{' '}
                  {documentUpload.executable > 0
                    ? `${documentUpload.executable} executable requirement${documentUpload.executable === 1 ? '' : 's'}`
                    : 'stored as source text; no requirements created'}
                  .
                </p>
              )}
              {documentUpload.kind === 'error' && (
                <p role="alert" className="notice notice--error">
                  {documentUpload.message}
                </p>
              )}
            </section>

            <section className="review-objective" aria-labelledby="review-objective-heading">
              <div className="panel-heading">
                <h3 id="review-objective-heading">Review objective</h3>
                <span className="panel-heading__hint">Optional</span>
              </div>
              <label className="review-objective__label" htmlFor="review-objective">
                Review objective (optional)
              </label>
              <textarea
                id="review-objective"
                className="review-objective__input"
                name="objective"
                rows={3}
                maxLength={MAX_REVIEW_OBJECTIVE_LENGTH}
                value={objective}
                disabled={reviewBusy}
                aria-describedby="review-objective-help review-objective-count"
                placeholder="e.g. Focus on fire-rating completeness for the ground-floor walls."
                onChange={(event) => setObjective(event.target.value)}
              />
              <p id="review-objective-help" className="review-objective__help">
                An objective can only narrow the confirmed checks that run; it never changes their
                criteria and never creates findings. Leave blank to run every confirmed check
                deterministically. The plan source shown after the run reports what actually
                happened.
              </p>
              <p id="review-objective-count" className="review-objective__count">
                {objectiveLength} / {MAX_REVIEW_OBJECTIVE_LENGTH}
              </p>
            </section>

            {run && model && (
              <ReviewCoverage
                run={run}
                findingCount={findings.length}
                activeModelHash={model.summary.model_hash}
                submittedObjective={submittedObjective}
                llmMode={llmMode}
              />
            )}

            <EvidenceInspector
              selectedFinding={selectedFinding}
              elementState={elementState}
              selectedGlobalIds={selectedGlobalIds}
              relatedFindings={relatedFindings}
              requirements={requirementsState.kind === 'ready' ? requirementsState.items : null}
              runModelHash={run?.input_manifest.model_hash ?? null}
              explanation={
                run
                  ? {
                      state: explanationState,
                      versionMatches: runVersionMatches,
                      llmMode,
                      onRequest: requestExplanation,
                    }
                  : null
              }
              onSelectFinding={selectFinding}
            />
          </div>
        </main>
      )}
    </div>
  );
}

function ReviewStatusChip({
  state,
  executableCount,
}: {
  readonly state: ReviewState;
  readonly executableCount: number | null;
}) {
  switch (state.kind) {
    case 'none':
      return (
        <span className="review-bar__item review-bar__chip" role="status">
          {executableCount === 0
            ? 'No executable requirements · model view only'
            : 'No review run yet'}
        </span>
      );
    case 'loading':
      return (
        <span className="review-bar__item review-bar__chip" role="status">
          Loading run <code>{state.runId.slice(0, 8)}</code>…
        </span>
      );
    case 'running':
      return (
        <span className="review-bar__item review-bar__chip review-bar__chip--active" role="status">
          {state.objective === null ? 'Deterministic review running…' : 'Objective review running…'}
        </span>
      );
    case 'ready':
      return (
        <span
          className={`review-bar__item review-bar__chip review-bar__chip--${state.run.status}`}
          role="status"
        >
          Review {state.run.status} · {state.findings.length} finding
          {state.findings.length === 1 ? '' : 's'} · run <code>{state.run.id.slice(0, 8)}</code>
        </span>
      );
    case 'mismatch':
      return (
        <span className="review-bar__item review-bar__chip review-bar__chip--failed" role="alert">
          Model version mismatch · run {state.runId.slice(0, 8)} not shown
        </span>
      );
    case 'error':
      return (
        <span className="review-bar__item review-bar__chip review-bar__chip--failed" role="alert">
          Review error
        </span>
      );
  }
}

function ReviewPlaceholder({
  state,
  executableCount,
}: {
  readonly state: Exclude<ReviewState, { kind: 'ready' }>;
  readonly executableCount: number | null;
}) {
  switch (state.kind) {
    case 'none':
      return (
        <p className="notice">
          {executableCount === 0
            ? 'This session has no confirmed executable requirements, so no review has run and no findings exist. Add an IDS to enable Run review.'
            : 'No review has run for this model version. Use Run review to execute the deterministic default plan.'}
        </p>
      );
    case 'loading':
      return (
        <p role="status" className="notice">
          Loading review run <code>{state.runId}</code> and its findings…
        </p>
      );
    case 'running':
      return (
        <p role="status" className="notice">
          {state.objective === null
            ? 'Running the deterministic review against the active model version…'
            : 'Running the review against the active model version. The objective may narrow the confirmed checks; the plan source will show whether it was used.'}
        </p>
      );
    case 'mismatch':
      return (
        <div>
          <p role="alert" className="notice notice--error">
            {state.message}
          </p>
          <p className="notice">
            Run <code>{state.runId}</code> was recorded against a different model version, so its
            findings are not shown with this model. Run a new review to produce findings for the
            active version.
          </p>
        </div>
      );
    case 'error':
      return (
        <div>
          <p role="alert" className="notice notice--error">
            {state.message}
          </p>
          <p className="notice">
            No findings are shown because the review did not complete. The model remains viewable.
          </p>
        </div>
      );
  }
}

function messageForError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return error instanceof Error ? error.message : 'The request failed.';
}
