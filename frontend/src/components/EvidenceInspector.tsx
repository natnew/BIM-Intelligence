import type {
  ElementRecord,
  Explanation,
  Finding,
  PropertyValue,
  Requirement,
} from '../api/generated/types';

export type ElementLoadState =
  | { readonly kind: 'idle' }
  | { readonly kind: 'loading'; readonly globalId: string }
  | { readonly kind: 'ready'; readonly element: ElementRecord }
  | { readonly kind: 'error'; readonly globalId: string; readonly message: string };

export type ExplanationState =
  | { readonly kind: 'idle' }
  | { readonly kind: 'loading' }
  | { readonly kind: 'ready'; readonly explanation: Explanation; readonly fromCache: boolean }
  | { readonly kind: 'error'; readonly message: string; readonly status: number | undefined };

/** Everything the inspector needs to offer and render an explanation for the selected finding. */
export interface ExplanationRequest {
  readonly state: ExplanationState;
  /** False when the loaded run's model version differs from the active model; requests refused. */
  readonly versionMatches: boolean;
  readonly onRequest: () => void;
}

const FALLBACK_REASON_TEXT: Record<NonNullable<Explanation['fallback_reason']>, string> = {
  ai_disabled: 'AI is off.',
  unsupported_evidence:
    'This finding cannot be grounded safely, for example a multi-element finding.',
  budget_limit: 'The spend or call limit was reached.',
  ai_request_failed: 'The AI request failed.',
  ai_output_invalid: 'The AI response was invalid.',
  grounding_failed: 'The AI text cited facts outside the evidence and was discarded.',
};

interface EvidenceInspectorProps {
  readonly selectedFinding: Finding | null;
  readonly elementState: ElementLoadState;
  readonly selectedGlobalIds: string[];
  readonly relatedFindings: Finding[];
  readonly requirements: Requirement[] | null;
  readonly runModelHash: string | null;
  readonly explanation: ExplanationRequest | null;
  readonly onSelectFinding: (finding: Finding) => void;
}

export function EvidenceInspector({
  selectedFinding,
  elementState,
  selectedGlobalIds,
  relatedFindings,
  requirements,
  runModelHash,
  explanation,
  onSelectFinding,
}: EvidenceInspectorProps) {
  const nothingSelected = !selectedFinding && elementState.kind === 'idle';
  const requirement =
    selectedFinding && requirements
      ? (requirements.find((candidate) => candidate.id === selectedFinding.requirement_id) ?? null)
      : null;

  return (
    <aside className="inspector" aria-labelledby="inspector-heading">
      <div className="panel-heading">
        <h2 id="inspector-heading">Evidence inspector</h2>
        <span className="panel-heading__hint">Deterministic records</span>
      </div>

      {nothingSelected && (
        <p className="notice inspector__empty">
          No finding or element selected. Choose a row in the findings register or click an element
          in the model to inspect its GlobalId, properties and any linked evidence.
        </p>
      )}

      {selectedFinding && (
        <details className="inspector__section" open>
          <summary>
            <span className="inspector__summary-title">Finding evidence</span>
            <span className={`severity severity--${selectedFinding.severity}`}>
              {selectedFinding.severity}
            </span>
          </summary>
          <p className="verification-label">
            Deterministic finding · method <code>{selectedFinding.method}</code>
          </p>
          <dl className="detail-list">
            <dt>Finding ID</dt>
            <dd>
              <code>{selectedFinding.id}</code>
            </dd>
            <dt>Observed</dt>
            <dd className="detail-list__observed">{selectedFinding.observed}</dd>
            <dt>Expected</dt>
            <dd className="detail-list__expected">{selectedFinding.expected}</dd>
            <dt>Requirement</dt>
            <dd>
              <code>{selectedFinding.requirement_id}</code>
            </dd>
            <dt>Check</dt>
            <dd>
              <code>{selectedFinding.check_id}</code>
            </dd>
            <dt>Rule</dt>
            <dd>
              <code>{selectedFinding.rule_id}</code> · version{' '}
              <code>{selectedFinding.rule_version}</code>
            </dd>
            <dt>Category</dt>
            <dd>{selectedFinding.category}</dd>
            {runModelHash && (
              <>
                <dt>Model version</dt>
                <dd>
                  <code title={runModelHash}>{runModelHash.slice(0, 12)}</code>
                </dd>
              </>
            )}
          </dl>

          <h4 className="inspector__subheading">
            Affected elements ({selectedFinding.elements.length})
          </h4>
          <ul className="element-ref-list" aria-label="Elements affected by the selected finding">
            {selectedFinding.elements.map((element) => (
              <li key={element.global_id ?? `#${element.express_id}`}>
                <span>
                  {element.name ?? element.ifc_type}
                  <span className="finding-row__meta">
                    {' '}
                    · {element.ifc_type}
                    {element.storey ? ` · ${element.storey}` : ''}
                  </span>
                </span>
                <code>{element.global_id ?? `#${element.express_id}`}</code>
              </li>
            ))}
          </ul>

          <h4 className="inspector__subheading">Source requirement</h4>
          {requirements === null ? (
            <p className="notice">Requirement details could not be loaded for this session.</p>
          ) : requirement ? (
            <dl className="detail-list">
              <dt>Title</dt>
              <dd>{requirement.title}</dd>
              <dt>Statement</dt>
              <dd>{requirement.statement}</dd>
              <dt>Origin</dt>
              <dd>
                {requirement.origin} · {requirement.status} · revision {requirement.revision}
              </dd>
              <dt>Source quote</dt>
              <dd>
                {requirement.source ? (
                  <blockquote className="source-quote">
                    “{requirement.source.quote}”
                    <footer>
                      {requirement.source.location} · document{' '}
                      <code>{requirement.source.document_id.slice(0, 12)}</code>
                    </footer>
                  </blockquote>
                ) : (
                  <span className="notice">
                    None — this requirement was compiled directly from an IDS specification or a
                    built-in rule, so there is no narrative quotation.
                  </span>
                )}
              </dd>
            </dl>
          ) : (
            <p className="notice">
              Requirement <code>{selectedFinding.requirement_id}</code> is not in the session’s
              current requirement list.
            </p>
          )}
        </details>
      )}

      {elementState.kind !== 'idle' && (
        <details className="inspector__section" open>
          <summary>
            <span className="inspector__summary-title">Selected element</span>
            {selectedGlobalIds.length > 1 && (
              <span className="selection-count">{selectedGlobalIds.length} selected</span>
            )}
          </summary>
          {elementState.kind === 'loading' && (
            <p role="status" className="notice">
              Loading element <code>{elementState.globalId}</code>…
            </p>
          )}
          {elementState.kind === 'error' && (
            <p role="alert" className="notice notice--error">
              {elementState.message}
            </p>
          )}
          {elementState.kind === 'ready' && <ElementDetails element={elementState.element} />}
          {selectedGlobalIds.length > 1 && (
            <p className="selection-count">
              {selectedGlobalIds.length} elements are selected in the model; details show the first
              GlobalId.
            </p>
          )}

          {elementState.kind === 'ready' && (
            <>
              <h4 className="inspector__subheading">Linked findings ({relatedFindings.length})</h4>
              {relatedFindings.length === 0 ? (
                <p className="notice">
                  No finding in the loaded run references this element. That is not evidence of
                  compliance beyond the executed checks.
                </p>
              ) : (
                <ul className="related-list" aria-label="Findings that reference this element">
                  {relatedFindings.map((finding) => (
                    <li key={finding.id}>
                      <button
                        type="button"
                        className="related-list__item"
                        aria-pressed={selectedFinding?.id === finding.id}
                        onClick={() => onSelectFinding(finding)}
                      >
                        <span className={`severity severity--${finding.severity}`}>
                          {finding.severity}
                        </span>
                        <span>
                          <code>{finding.rule_id}</code> · {finding.expected}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </details>
      )}

      {selectedFinding && <ExplanationPanel finding={selectedFinding} request={explanation} />}

      {!selectedFinding && !nothingSelected && (
        <p className="inspector__ai-note">
          <strong>AI explanation · findings only.</strong> Select a finding to request an
          interpretation. Nothing shown above is model-generated.
        </p>
      )}
    </aside>
  );
}

function ExplanationPanel({
  finding,
  request,
}: {
  readonly finding: Finding;
  readonly request: ExplanationRequest | null;
}) {
  const state: ExplanationState = request?.state ?? { kind: 'idle' };
  const canRequest = request !== null && request.versionMatches && state.kind !== 'loading';

  return (
    <section
      className="explanation"
      aria-labelledby="explanation-heading"
      data-testid="explanation-panel"
    >
      <div className="panel-heading">
        <h4 id="explanation-heading" className="explanation__heading">
          AI explanation
        </h4>
        <span className="panel-heading__hint">Interpretation · not a Finding</span>
      </div>
      <p className="explanation__intro">
        An explanation interprets the deterministic evidence above. It is requested only when you
        ask for it, may spend part of the per-run call allowance, and never changes or creates a
        finding.
      </p>
      <div className="explanation__actions">
        <button
          type="button"
          className="button"
          disabled={!canRequest}
          onClick={request?.onRequest}
          title={
            request === null
              ? 'Load a review run before requesting an explanation'
              : !request.versionMatches
                ? 'The run belongs to a different model version; explanations are refused'
                : undefined
          }
        >
          {state.kind === 'loading'
            ? 'Requesting explanation…'
            : state.kind === 'ready'
              ? 'Explain finding again'
              : 'Explain finding'}
        </button>
        {request !== null && !request.versionMatches && (
          <span className="explanation__version-note">
            Unavailable: the run’s model version differs from the active model.
          </span>
        )}
      </div>

      {state.kind === 'loading' && (
        <p role="status" className="notice explanation__pending">
          Requesting an explanation for <code>{finding.id}</code>…
        </p>
      )}
      {state.kind === 'error' && (
        <p role="alert" className="notice notice--error">
          Explanation request failed
          {state.status !== undefined ? ` (${state.status})` : ''}: {state.message}
        </p>
      )}
      {state.kind === 'ready' && (
        <ExplanationResult explanation={state.explanation} fromCache={state.fromCache} />
      )}
    </section>
  );
}

function ExplanationResult({
  explanation,
  fromCache,
}: {
  readonly explanation: Explanation;
  readonly fromCache: boolean;
}) {
  const aiGenerated = explanation.source === 'ai_generated';
  return (
    <div
      className={`explanation__result explanation__result--${explanation.source}`}
      data-testid="explanation-result"
      data-source={explanation.source}
    >
      <p className="explanation__provenance">
        {aiGenerated ? (
          <>
            <strong>AI interpretation</strong> · <code>{explanation.model}</code> · grounding{' '}
            {explanation.grounding_status}
          </>
        ) : (
          <>
            <strong>Deterministic template</strong> · AI not used
          </>
        )}
        {fromCache && <> · shown from this session’s earlier request</>}
      </p>
      <dl className="detail-list explanation__facts">
        <dt>Source</dt>
        <dd>
          <code>{explanation.source}</code>
        </dd>
        <dt>Grounding</dt>
        <dd>
          <code>{explanation.grounding_status}</code>
        </dd>
        <dt>Fallback</dt>
        <dd>
          {explanation.fallback_reason === null ? (
            'none'
          ) : (
            <>
              <code>{explanation.fallback_reason}</code> —{' '}
              {FALLBACK_REASON_TEXT[explanation.fallback_reason]}
            </>
          )}
        </dd>
        <dt>Model</dt>
        <dd>{explanation.model === null ? 'none' : <code>{explanation.model}</code>}</dd>
      </dl>

      <dl className="detail-list explanation__text">
        <dt>Summary</dt>
        <dd>{explanation.summary}</dd>
        <dt>Probable cause</dt>
        <dd>{explanation.probable_cause}</dd>
        <dt>Corrective action</dt>
        <dd>{explanation.corrective_action}</dd>
      </dl>

      <h5 className="inspector__subheading">Evidence cited ({explanation.citations.length})</h5>
      {explanation.citations.length === 0 ? (
        <p className="notice">This explanation cites no deterministic evidence.</p>
      ) : (
        <ul className="citation-list" aria-label="Deterministic evidence cited by the explanation">
          {explanation.citations.map((citation, index) => (
            <li key={`${citation.finding_id}-${citation.global_id}-${index}`}>
              <code>{citation.global_id}</code>
              <span className="finding-row__meta">
                {' '}
                · requirement <code>{citation.requirement_id}</code> · rule{' '}
                <code>{citation.rule_id}</code>
              </span>
              <span className="citation-list__evidence">
                <span className="detail-list__observed">{citation.observed}</span>
                {' → '}
                <span className="detail-list__expected">{citation.expected}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ElementDetails({ element }: { readonly element: ElementRecord }) {
  const psets = Object.entries(element.psets).flatMap(([setName, values]) => {
    const rows = Object.entries(values ?? {}).flatMap(([name, value]) =>
      value ? [{ name, value }] : [],
    );
    return rows.length > 0 ? [{ setName, rows }] : [];
  });

  return (
    <>
      <p className="element-panel__name">{element.ref.name ?? element.ref.ifc_type}</p>
      <dl className="detail-list">
        <dt>GlobalId</dt>
        <dd>
          <code>{element.ref.global_id ?? `#${element.ref.express_id}`}</code>
        </dd>
        <dt>IFC type</dt>
        <dd>
          {element.ref.ifc_type}
          {element.predefined_type ? ` · ${element.predefined_type}` : ''}
        </dd>
        <dt>Storey</dt>
        <dd>{element.ref.storey ?? 'Not assigned'}</dd>
        {element.object_type && (
          <>
            <dt>Object type</dt>
            <dd>{element.object_type}</dd>
          </>
        )}
        {element.type_ref && (
          <>
            <dt>Typed by</dt>
            <dd>
              {element.type_ref.name ?? element.type_ref.ifc_type}{' '}
              <code>{element.type_ref.global_id ?? `#${element.type_ref.express_id}`}</code>
            </dd>
          </>
        )}
        {element.container && (
          <>
            <dt>Container</dt>
            <dd>
              {element.container.name ?? element.container.ifc_type}{' '}
              <span className="finding-row__meta">({element.container.ifc_type})</span>
            </dd>
          </>
        )}
      </dl>

      {element.classifications.length > 0 && (
        <>
          <h4 className="inspector__subheading">Classifications</h4>
          <ul className="classification-list" aria-label="Classification references">
            {element.classifications.map((classification, index) => (
              <li key={`${classification.system ?? ''}-${classification.identification ?? index}`}>
                <code>{classification.identification ?? '—'}</code> {classification.name ?? ''}
                <span className="finding-row__meta">
                  {classification.system ? ` · ${classification.system}` : ''}
                  {classification.inherited ? ' · inherited from type' : ''}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      <h4 className="inspector__subheading">Property and quantity sets</h4>
      {psets.length === 0 ? (
        <p className="notice">The index recorded no property or quantity sets for this element.</p>
      ) : (
        psets.map((pset, index) => (
          <details className="pset" key={pset.setName} open={index < 2}>
            <summary>
              {pset.setName}
              <span className="finding-row__meta"> · {pset.rows.length}</span>
            </summary>
            <div className="property-list" aria-label={`${pset.setName} properties`}>
              {pset.rows.map((property) => (
                <div className="property-list__row" key={property.name}>
                  <span>{property.name}</span>
                  <span>
                    {formatPropertyValue(property.value)}
                    {property.value.inherited && (
                      <span className="inherited-label"> · inherited from type</span>
                    )}
                  </span>
                </div>
              ))}
            </div>
          </details>
        ))
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
