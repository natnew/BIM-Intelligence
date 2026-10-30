import type { CheckResult, ReviewRun } from '../api/generated/types';

interface ReviewCoverageProps {
  readonly run: ReviewRun;
  readonly findingCount: number;
  readonly activeModelHash: string;
}

const STATUS_LABEL: Record<ReviewRun['status'], string> = {
  queued: 'Queued',
  running: 'Running',
  completed: 'Complete',
  partial: 'Complete · partial coverage',
  failed: 'Failed',
  interrupted: 'Interrupted',
};

export function ReviewCoverage({ run, findingCount, activeModelHash }: ReviewCoverageProps) {
  const totals = countByStatus(run.check_results);
  const executed = totals.passed + totals.failed;
  const notRun = totals.error + totals.skipped + totals.not_applicable;
  const versionMatches = run.input_manifest.model_hash === activeModelHash;

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
            {executed} of {run.check_results.length}
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
          <dt>Findings</dt>
          <dd>{findingCount}</dd>
        </div>
        <div>
          <dt>Plan source</dt>
          <dd>{run.plan_source === 'default' ? 'Deterministic default' : 'AI-selected plan'}</dd>
        </div>
      </dl>

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

function countByStatus(results: CheckResult[]): Record<CheckResult['status'], number> {
  const totals: Record<CheckResult['status'], number> = {
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
