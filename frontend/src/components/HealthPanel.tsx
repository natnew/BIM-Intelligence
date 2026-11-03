import { useHealth } from '../state/useHealth';

export function HealthPanel() {
  const state = useHealth();

  if (state.kind === 'loading') {
    return (
      <section className="panel health-panel" aria-label="System status">
        <p role="status" aria-live="polite">
          Checking backend connection…
        </p>
      </section>
    );
  }

  if (state.kind === 'error') {
    return (
      <section className="panel health-panel" aria-label="System status">
        <p role="alert" className="health-panel__unavailable">
          Backend unavailable: {state.message}
        </p>
        <p>AI review status is unknown until the backend reconnects.</p>
      </section>
    );
  }

  const { data } = state;
  return (
    <section className="panel health-panel" aria-label="System status">
      <dl className="health-panel__summary">
        <div>
          <dt>Backend</dt>
          <dd>Backend connected</dd>
        </div>
        <div>
          <dt>AI-assisted review</dt>
          <dd>{aiReviewStatus(data.llm_mode, data.llm_configured)}</dd>
        </div>
      </dl>

      <details className="health-panel__details">
        <summary>Technical details</summary>
        <dl className="health-panel__technical">
          <dt>API version</dt>
          <dd>{data.version}</dd>
          <dt>Configured mode</dt>
          <dd>
            <code>{data.llm_mode}</code>
          </dd>
          <dt>Model identifier</dt>
          <dd>
            <code>{data.llm_model}</code>
          </dd>
          <dt>IfcOpenShell</dt>
          <dd>{data.libraries.ifcopenshell ?? 'not installed'}</dd>
          <dt>IfcTester</dt>
          <dd>{data.libraries.ifctester ?? 'not installed'}</dd>
        </dl>
      </details>
    </section>
  );
}

function aiReviewStatus(mode: 'live' | 'replay' | 'off', configured: boolean): string {
  if (mode === 'off') {
    return 'AI review unavailable in the current mode; deterministic reviews remain available.';
  }
  if (mode === 'replay') {
    return 'AI review configured for recorded responses; no live provider call.';
  }
  return configured
    ? 'AI review configured; provider reachability has not been tested.'
    : 'AI review unavailable because the live configuration is incomplete.';
}
