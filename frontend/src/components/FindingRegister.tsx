import { useId, useMemo, useState } from 'react';

import type { Finding } from '../api/generated/types';

interface FindingRegisterProps {
  readonly findings: Finding[];
  readonly selectedFindingId: string | null;
  readonly onSelect: (finding: Finding) => void;
}

type SeverityFilter = 'all' | Finding['severity'];

export function FindingRegister({ findings, selectedFindingId, onSelect }: FindingRegisterProps) {
  const [query, setQuery] = useState('');
  const [severity, setSeverity] = useState<SeverityFilter>('all');
  const searchId = useId();
  const severityId = useId();

  // Filters hide rows only; the source list, its order and each record stay untouched.
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return findings.filter((finding) => {
      if (severity !== 'all' && finding.severity !== severity) {
        return false;
      }
      if (!needle) {
        return true;
      }
      const haystack = [
        finding.id,
        finding.rule_id,
        finding.requirement_id,
        finding.category,
        finding.observed,
        finding.expected,
        ...finding.elements.flatMap((element) => [
          element.name ?? '',
          element.global_id ?? '',
          element.ifc_type,
          element.storey ?? '',
        ]),
      ]
        .join(' ')
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [findings, query, severity]);

  const filtered = visible.length !== findings.length;

  return (
    <section className="register" aria-labelledby="findings-heading">
      <div className="register__heading">
        <div className="panel-heading">
          <h2 id="findings-heading">Findings</h2>
          <span className="finding-count" aria-label={`${findings.length} findings in this run`}>
            {findings.length}
          </span>
        </div>
        <div className="register__filters">
          <label className="register__filter">
            <span className="visually-hidden" id={searchId}>
              Search findings
            </span>
            <input
              type="search"
              aria-labelledby={searchId}
              placeholder="Search rule, requirement, element or GlobalId"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              disabled={findings.length === 0}
            />
          </label>
          <label className="register__filter">
            <span className="visually-hidden" id={severityId}>
              Filter by severity
            </span>
            <select
              aria-labelledby={severityId}
              value={severity}
              onChange={(event) => setSeverity(event.target.value as SeverityFilter)}
              disabled={findings.length === 0}
            >
              <option value="all">All severities</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </label>
        </div>
      </div>

      <div className="register__classes">
        <p>
          <strong>Information quality</strong>
          <span> · IDS and native property/classification checks</span>
        </p>
        <p className="register__unavailable">
          <strong>Geometric clashes</strong>
          <span> · not available: no clash-detection engine is implemented</span>
        </p>
      </div>

      {findings.length === 0 ? (
        <p className="notice register__empty">
          No findings were returned for this review run. This does not by itself establish
          compliance; check the coverage panel for skipped or errored checks.
        </p>
      ) : visible.length === 0 ? (
        <p className="notice register__empty" role="status">
          No findings match the current filter. {findings.length} finding
          {findings.length === 1 ? '' : 's'} remain in the run.
        </p>
      ) : (
        <>
          {filtered && (
            <p className="register__filtered" role="status">
              Showing {visible.length} of {findings.length} findings. Filters hide rows only; the
              run’s findings are unchanged.
            </p>
          )}
          <div className="register__columns" aria-hidden="true">
            <span>Severity · method</span>
            <span>Finding and check</span>
            <span>Model element</span>
            <span>Observed → expected</span>
          </div>
          <ul className="finding-list">
            {visible.map((finding) => {
              const first = finding.elements[0];
              const extra = finding.elements.length - 1;
              return (
                <li key={finding.id}>
                  <button
                    type="button"
                    className="finding-row"
                    aria-pressed={finding.id === selectedFindingId}
                    onClick={() => onSelect(finding)}
                  >
                    <span className="finding-row__severity">
                      <span className={`severity severity--${finding.severity}`}>
                        {finding.severity}
                      </span>
                      <span className="method-label">{finding.method}</span>
                    </span>
                    <span className="finding-row__check">
                      <span className="finding-row__title">{first?.name ?? finding.category}</span>
                      <span className="finding-row__meta">
                        <code>{finding.requirement_id}</code> · <code>{finding.rule_id}</code>
                      </span>
                    </span>
                    <span className="finding-row__element">
                      <span>
                        {first
                          ? `${first.ifc_type}${first.storey ? ` · ${first.storey}` : ''}`
                          : '—'}
                      </span>
                      <span className="finding-row__meta">
                        <code>{first?.global_id ?? 'no GlobalId'}</code>
                        {extra > 0 && ` +${extra} more`}
                      </span>
                    </span>
                    <span className="finding-row__evidence">
                      <span className="finding-row__observed">{finding.observed}</span>
                      <span className="finding-row__expected">{finding.expected}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}
