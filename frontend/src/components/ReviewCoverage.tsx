import type { Requirement, ReviewRun } from '../api/generated/types';

interface ReviewCoverageProps {
  readonly run: ReviewRun;
  readonly findingCount: number;
  readonly activeModelHash: string;
  /** The objective text the user submitted for this run; `null` when none was sent or unknown. */
  readonly submittedObjective: string | null;
  readonly requirements: Requirement[];
}

const STATUS_LABEL: Record<ReviewRun['status'], string> = {
  queued: 'Queued',
  running: 'Running',
  completed: 'Complete',
  partial: 'Complete · partial coverage',
  failed: 'Failed',
  interrupted: 'Interrupted',
};

function planSourceLabel(run: ReviewRun): string {
  if (run.provenance === null) {
    return 'Historical run · provenance not recorded';
  }
  if (run.plan_source === 'llm') {
    return 'AI-selected plan';
  }
  if (run.provenance.outcome === 'continued_without_ai') {
    return 'User continued without AI';
  }
  if (run.provenance.deterministic_fallback) {
    return 'Deterministic fallback';
  }
  return 'Deterministic default';
}

function fallbackCauseLabel(run: ReviewRun): string {
  const provenance = run.provenance;
  if (provenance === null) {
    return 'Not recorded';
  }
  if (provenance.fallback_reason === null) {
    return 'None';
  }
  switch (provenance.fallback_reason) {
    case 'user_selected_continue_without_ai':
      return 'User continued without AI';
    case 'provider_unavailable':
      return provenance.mode === 'off' ? 'AI mode is Off' : 'Provider unavailable';
    case 'provider_failure':
      return 'Provider request failed';
    case 'budget_limit':
      return 'Configured spend or call limit reached';
    case 'budget_state':
      return 'Budget state could not be verified';
    case 'token_limit':
      return 'Configured token limit reached';
    case 'invalid_output':
      return 'AI response did not match the permitted schema';
    case 'plan_rejected':
      return 'Proposed plan could not be accepted';
    case 'unsupported_scope':
      return 'Objective is not represented by the selected checks';
    case 'replay_mismatch':
      return 'No matching Replay response';
    default:
      return provenance.fallback_reason;
  }
}

function checkLabel(checkId: string, run: ReviewRun, requirements: Requirement[]): string {
  const requirement = requirements.find(
    (candidate) =>
      candidate.check.id === checkId &&
      run.input_manifest.requirement_revisions[candidate.id] === candidate.revision,
  );
  return requirement ? `${requirement.id} · ${requirement.title}` : checkId;
}

export function ReviewCoverage({
  run,
  findingCount,
  activeModelHash,
  submittedObjective,
  requirements,
}: ReviewCoverageProps) {
  const totals = countByStatus(run.check_results);
  const provenance = run.provenance;
  const selectedIds = provenance?.selected_check_ids ?? [];
  const plannedIds = run.plan.checks.map((check) => check.check_id);
  const executed =
    provenance?.executed_check_ids.length ??
    run.check_results.filter(
      (result) =>
        result.status === 'passed' || result.status === 'failed' || result.status === 'error',
    ).length;
  const notRun = totals.error + totals.skipped + totals.not_applicable;
  const versionMatches = run.input_manifest.model_hash === activeModelHash;
  const modeLabel =
    provenance === null
      ? 'Not recorded'
      : provenance.mode === 'live'
        ? 'Live'
        : provenance.mode === 'replay'
          ? 'Replay'
          : 'Off';
  const planSource = planSourceLabel(run);
  const fallbackCause = fallbackCauseLabel(run);

  return (
    <section className="coverage" aria-labelledby="coverage-heading">
      <div className="panel-heading">
        <h3 id="coverage-heading">Review coverage</h3>
        <span className={`run-status run-status--${run.status}`} role="status">
          {STATUS_LABEL[run.status]}
        </span>
      </div>

      <dl className="coverage__grid">
        <div>
          <dt>Checks executed</dt>
          <dd>
            {executed} of {run.plan.checks.length} planned
          </dd>
        </div>
        <div>
          <dt>Passed</dt>
          <dd>{totals.passed}</dd>
        </div>
        <div>
          <dt>Failed</dt>
          <dd>{totals.failed}</dd>
        </div>
        <div>
          <dt>Not run</dt>
          <dd>
            {notRun}
            {notRun > 0 && (
              <span className="coverage__detail">
                {' '}
                ({totals.error} error · {totals.skipped} skipped · {totals.not_applicable} n/a)
              </span>
            )}
          </dd>
        </div>
        <div>
          <dt>Execution errors</dt>
          <dd>{totals.error}</dd>
        </div>
        <div>
          <dt>Findings</dt>
          <dd>{findingCount}</dd>
        </div>
      </dl>

      <dl className="coverage__provenance">
        <div>
          <dt>Selected scope</dt>
          <dd>
            {provenance === null
              ? 'Not recorded for this historical run'
              : `${selectedIds.length} confirmed check${selectedIds.length === 1 ? '' : 's'}`}
          </dd>
        </div>
        <div>
          <dt>Plan selected</dt>
          <dd>
            {plannedIds.length} check{plannedIds.length === 1 ? '' : 's'}
          </dd>
        </div>
        <div>
          <dt>Plan source</dt>
          <dd data-testid="plan-source">{planSource}</dd>
        </div>
        <div>
          <dt>Mode</dt>
          <dd>{modeLabel}</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd>{provenance?.model ? <code>{provenance.model}</code> : 'Not recorded'}</dd>
        </div>
        <div>
          <dt>Fallback cause</dt>
          <dd>
            {fallbackCause}
            {provenance?.fallback_reason && (
              <>
                {' '}
                (<code>{provenance.fallback_reason}</code>)
              </>
            )}
          </dd>
        </div>
      </dl>

      <details className="coverage__checks">
        <summary>Scope and check selection</summary>
        {selectedIds.length > 0 && (
          <ul className="coverage__check-list" aria-label="User-selected check scope">
            {selectedIds.map((checkId) => (
              <li key={checkId}>{checkLabel(checkId, run, requirements)}</li>
            ))}
          </ul>
        )}
        {plannedIds.length > 0 && (
          <ul className="coverage__check-list" aria-label="Checks selected by the plan">
            {plannedIds.map((checkId) => (
              <li key={checkId}>{checkLabel(checkId, run, requirements)}</li>
            ))}
          </ul>
        )}
        {provenance?.mode === 'replay' && run.plan_source === 'llm' && (
          <p className="notice" role="status">
            This plan used a recorded response; no live call in Replay mode.
          </p>
        )}
      </details>

      {submittedObjective !== null && (
        <div className="coverage__objective" data-testid="coverage-objective">
          <p className="coverage__objective-label">Review objective submitted</p>
          <blockquote className="source-quote">“{submittedObjective}”</blockquote>
          {run.plan_source === 'default' && (
            <p className="notice" role="status">
              The objective was not used to select a plan. The plan source and fallback cause above
              describe what happened.
            </p>
          )}
        </div>
      )}

      <p className="coverage__note">
        Coverage and findings are separate. Zero findings or an incomplete run is not a compliance
        conclusion.
      </p>

      {!versionMatches && (
        <p role="alert" className="notice notice--error">
          This run was executed against model version{' '}
          <code>{run.input_manifest.model_hash.slice(0, 12)}</code>, not the active version{' '}
          <code>{activeModelHash.slice(0, 12)}</code>.
        </p>
      )}

      <details className="coverage__checks" open={run.check_results.length <= 6}>
        <summary>Check results ({run.check_results.length})</summary>
        <ul aria-label="Check coverage" className="check-result-list">
          {run.check_results.map((result) => (
            <li key={result.check_id} className={`check-result check-result--${result.status}`}>
              <span className="check-result__status">{result.status}</span>
              <span className="check-result__body">
                <code>{result.requirement_id}</code>
                <span className="check-result__meta">
                  {' '}
                  · {result.applicable_count} applicable · {result.finding_ids.length} finding
                  {result.finding_ids.length === 1 ? '' : 's'}
                </span>
                {result.diagnostics.length > 0 && (
                  <span className="check-result__diagnostics">{result.diagnostics.join(' ')}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}

function countByStatus(
  results: ReviewRun['check_results'],
): Record<ReviewRun['check_results'][number]['status'], number> {
  const totals: Record<ReviewRun['check_results'][number]['status'], number> = {
    passed: 0,
    failed: 0,
    error: 0,
    skipped: 0,
    not_applicable: 0,
  };
  for (const result of results) {
    totals[result.status] += 1;
  }
  return totals;
}
