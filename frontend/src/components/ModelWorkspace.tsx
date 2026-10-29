import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';

import { ApiError } from '../api/client';
import {
  fetchElement,
  loadReviewWorkspace,
  startStandardReview,
  type ReviewWorkspaceData,
} from '../api/bim';
import type { ElementRecord, Finding, PropertyValue } from '../api/generated/types';
import { ViewerCanvas } from '../viewer/ViewerCanvas';

interface ModelWorkspaceProps {
  readonly initialSessionId: string;
  readonly initialRunId: string;
}

export function ModelWorkspace({ initialSessionId, initialRunId }: ModelWorkspaceProps) {
  const [sessionId, setSessionId] = useState(initialSessionId);
  const [runId, setRunId] = useState(initialRunId);
  const [workspace, setWorkspace] = useState<ReviewWorkspaceData | null>(null);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [selectedGlobalIds, setSelectedGlobalIds] = useState<string[]>([]);
  const [selectedElement, setSelectedElement] = useState<ElementRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadRequestRef = useRef<AbortController | null>(null);
  const elementRequestRef = useRef<AbortController | null>(null);
  const selectedFinding = workspace?.findings.find((finding) => finding.id === selectedFindingId);
  const highlightedGlobalIds = useMemo(
    () =>
      selectedFinding?.elements.flatMap((element) =>
        element.global_id ? [element.global_id] : [],
      ) ?? [],
    [selectedFinding],
  );

  useEffect(
    () => () => {
      loadRequestRef.current?.abort();
      elementRequestRef.current?.abort();
    },
    [],
  );

  async function connectToReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    loadRequestRef.current?.abort();
    elementRequestRef.current?.abort();
    const controller = new AbortController();
    loadRequestRef.current = controller;
    setLoading(true);
    setError(null);
    setWorkspace(null);
    setSelectedFindingId(null);
    setSelectedGlobalIds([]);
    setSelectedElement(null);

    try {
      const loaded = await loadReviewWorkspace(sessionId.trim(), runId.trim(), controller.signal);
      if (!controller.signal.aborted) {
        setWorkspace(loaded);
      }
    } catch (caught) {
      if (!controller.signal.aborted) {
        setError(messageForError(caught));
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }

  async function runStandardReview() {
    const activeSessionId = sessionId.trim();
    if (!activeSessionId) {
      return;
    }

    loadRequestRef.current?.abort();
    elementRequestRef.current?.abort();
    const controller = new AbortController();
    loadRequestRef.current = controller;
    setLoading(true);
    setError(null);
    setWorkspace(null);
    setSelectedFindingId(null);
    setSelectedGlobalIds([]);
    setSelectedElement(null);

    try {
      const run = await startStandardReview(activeSessionId, controller.signal);
      const loaded = await loadReviewWorkspace(activeSessionId, run.id, controller.signal);
      if (!controller.signal.aborted) {
        setRunId(run.id);
        setWorkspace(loaded);
      }
    } catch (caught) {
      if (!controller.signal.aborted) {
        setError(messageForError(caught));
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }

  const loadElement = useCallback(
    async (globalId: string | null) => {
      elementRequestRef.current?.abort();
      if (!globalId || !workspace) {
        setSelectedElement(null);
        return;
      }

      const controller = new AbortController();
      elementRequestRef.current = controller;
      setSelectedElement(null);
      setError(null);
      try {
        const element = await fetchElement(
          workspace.sessionId,
          globalId,
          workspace.etag,
          controller.signal,
        );
        if (!controller.signal.aborted) {
          setSelectedElement(element);
          setError(null);
        }
      } catch (caught) {
        if (!controller.signal.aborted) {
          setSelectedElement(null);
          setError(messageForError(caught));
        }
      }
    },
    [workspace],
  );

  const selectFromViewer = useCallback(
    (globalIds: string[]) => {
      const uniqueIds = [...new Set(globalIds)];
      const finding = workspace?.findings.find((candidate) =>
        candidate.elements.some(
          (element) => element.global_id !== null && uniqueIds.includes(element.global_id),
        ),
      );
      setSelectedGlobalIds(uniqueIds);
      setSelectedFindingId(finding?.id ?? null);
      void loadElement(uniqueIds[0] ?? null);
    },
    [loadElement, workspace],
  );

  function selectFinding(finding: Finding) {
    const globalIds = finding.elements.flatMap((element) =>
      element.global_id ? [element.global_id] : [],
    );
    setError(null);
    setSelectedFindingId(finding.id);
    setSelectedGlobalIds(globalIds);
    void loadElement(globalIds[0] ?? null);
  }

  return (
    <section className="workspace" aria-labelledby="model-heading">
      <div className="workspace__heading">
        <div>
          <p className="eyebrow">T-3/T-4 · Review workspace</p>
          <h2 id="model-heading">Model viewer</h2>
        </div>
        {workspace && <span className="version-badge">Version pinned</span>}
      </div>

      <form className="review-form" onSubmit={(event) => void connectToReview(event)}>
        <div className="review-form__field">
          <label htmlFor="session-id">Session ID</label>
          <input
            id="session-id"
            name="session_id"
            autoComplete="off"
            value={sessionId}
            onChange={(event) => setSessionId(event.target.value)}
            placeholder="Paste a session UUID"
            required
          />
        </div>
        <div className="review-form__field">
          <label htmlFor="run-id">Review run ID</label>
          <input
            id="run-id"
            name="run_id"
            autoComplete="off"
            value={runId}
            onChange={(event) => setRunId(event.target.value)}
            placeholder="Paste a completed run ID"
            required
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Loading review…' : 'Load review'}
        </button>
        <button
          type="button"
          disabled={loading || !sessionId.trim()}
          onClick={() => void runStandardReview()}
        >
          {loading ? 'Running review…' : 'Run standard review'}
        </button>
      </form>

      {error && (
        <p role="alert" className="notice notice--error">
          {error}
        </p>
      )}
      {!workspace && !loading && !error && (
        <p className="notice workspace__notice">
          Load an existing review or run a standard review for a session. Model and findings are
          read from version-aware API endpoints.
        </p>
      )}
      {loading && (
        <p role="status" className="notice workspace__notice">
          Checking the run’s model version and loading review data…
        </p>
      )}

      {workspace && (
        <div className="workspace__content">
          <div className="workspace__model">
            <dl className="model-summary" aria-label="Model summary">
              <div>
                <dt>Project</dt>
                <dd>{workspace.summary.project_name ?? 'Untitled project'}</dd>
              </div>
              <div>
                <dt>Schema</dt>
                <dd>{workspace.summary.ifc_schema}</dd>
              </div>
              <div>
                <dt>Model hash</dt>
                <dd>
                  <code>{workspace.summary.model_hash.slice(0, 12)}</code>
                </dd>
              </div>
              <div>
                <dt>Deterministic findings</dt>
                <dd>{workspace.findings.length}</dd>
              </div>
            </dl>
            <ViewerCanvas
              bytes={workspace.bytes}
              modelId={workspace.summary.model_hash}
              highlightedGlobalIds={highlightedGlobalIds}
              onGlobalIdsSelected={selectFromViewer}
              onViewerError={setError}
            />
          </div>

          <aside className="review-panel" aria-label="Findings and element details">
            <p className="notice" role="status">
              Review status: {workspace.run.status}
            </p>
            <section aria-labelledby="check-coverage-heading">
              <h3 id="check-coverage-heading">Check coverage</h3>
              <ul aria-label="Check coverage" className="check-result-list">
                {workspace.run.check_results.map((result) => (
                  <li key={result.check_id}>
                    <code>{result.requirement_id}</code> · {result.status}
                    {result.diagnostics.length > 0 && <p>{result.diagnostics.join(' ')}</p>}
                  </li>
                ))}
              </ul>
            </section>
            <section aria-labelledby="findings-heading">
              <div className="panel-heading">
                <h3 id="findings-heading">Findings</h3>
                <span className="finding-count">{workspace.findings.length}</span>
              </div>
              {workspace.findings.length === 0 ? (
                <p className="notice">No findings were returned for this review run.</p>
              ) : (
                <ul className="finding-list">
                  {workspace.findings.map((finding) => (
                    <li key={finding.id}>
                      <button
                        type="button"
                        className="finding-list__item"
                        aria-pressed={finding.id === selectedFindingId}
                        onClick={() => selectFinding(finding)}
                      >
                        <span className="finding-list__meta">
                          <span className={`severity severity--${finding.severity}`}>
                            {finding.severity}
                          </span>
                          <code>{finding.rule_id}</code>
                        </span>
                        <span className="finding-list__name">
                          {finding.elements[0]?.name ?? finding.category}
                        </span>
                        <span className="finding-list__summary">{finding.expected}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {selectedFinding && (
              <section className="detail-section" aria-labelledby="finding-detail-heading">
                <h3 id="finding-detail-heading">Finding details</h3>
                <p className="verification-label">
                  Deterministically verified · {selectedFinding.method}
                </p>
                <dl className="detail-list">
                  <dt>Observed</dt>
                  <dd>{selectedFinding.observed}</dd>
                  <dt>Expected</dt>
                  <dd>{selectedFinding.expected}</dd>
                  <dt>Requirement</dt>
                  <dd>
                    <code>{selectedFinding.requirement_id}</code>
                  </dd>
                  <dt>Rule version</dt>
                  <dd>
                    <code>{selectedFinding.rule_version}</code>
                  </dd>
                </dl>
              </section>
            )}

            <section className="detail-section" aria-labelledby="element-heading">
              <h3 id="element-heading">Selected element</h3>
              {selectedElement ? (
                <ElementDetails element={selectedElement} />
              ) : (
                <p className="notice">
                  Select a finding or click an element in the model to inspect its GlobalId and
                  properties.
                </p>
              )}
              {selectedGlobalIds.length > 1 && (
                <p className="selection-count">
                  {selectedGlobalIds.length} affected elements selected in the model.
                </p>
              )}
            </section>
          </aside>
        </div>
      )}
    </section>
  );
}

function ElementDetails({ element }: { readonly element: ElementRecord }) {
  const properties = Object.entries(element.psets).flatMap(([setName, values]) =>
    Object.entries(values ?? {}).flatMap(([name, value]) =>
      value ? [{ name: `${setName}.${name}`, value }] : [],
    ),
  );

  return (
    <>
      <p className="element-panel__name">{element.ref.name ?? element.ref.ifc_type}</p>
      <dl className="detail-list">
        <dt>GlobalId</dt>
        <dd>
          <code>{element.ref.global_id}</code>
        </dd>
        <dt>IFC type</dt>
        <dd>{element.ref.ifc_type}</dd>
        <dt>Storey</dt>
        <dd>{element.ref.storey ?? 'Not assigned'}</dd>
      </dl>
      {properties.length > 0 && (
        <div className="property-list" aria-label="Element properties">
          <h4>Properties</h4>
          {properties.slice(0, 12).map((property) => (
            <div className="property-list__row" key={property.name}>
              <span>{property.name}</span>
              <span>
                {formatPropertyValue(property.value)}
                {property.value.inherited && <span className="inherited-label"> · inherited</span>}
              </span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function formatPropertyValue(property: PropertyValue): string {
  const value = property.value;
  if (typeof value === 'string') {
    return value;
  }
  return JSON.stringify(value) ?? String(value);
}

function messageForError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return error instanceof Error ? error.message : 'The review request failed.';
}
