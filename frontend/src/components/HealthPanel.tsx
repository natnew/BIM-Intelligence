import { useHealth } from '../state/useHealth';

export function HealthPanel() {
  const state = useHealth();

  if (state.kind === 'loading') {
    return (
      <p role="status" aria-live="polite" className="panel panel--muted">
        Checking backend…
      </p>
    );
  }

  if (state.kind === 'error') {
    return (
      <p role="alert" className="panel panel--error">
        {state.message}
      </p>
    );
  }

  const { data } = state;
  return (
    <dl className="panel panel--grid" aria-label="Backend health">
      <dt>Status</dt>
      <dd>{data.status}</dd>
      <dt>API version</dt>
      <dd>{data.version}</dd>
      <dt>LLM mode</dt>
      <dd>
        <code>{data.llm_mode}</code>
        {data.llm_mode === 'off' && (
          <span className="badge" title="Deterministic pipeline only; no model calls">
            degraded
          </span>
        )}
      </dd>
      <dt>Model</dt>
      <dd>
        <code>{data.llm_model}</code> {data.llm_configured ? '(key configured)' : '(no key)'}
      </dd>
      <dt>IfcOpenShell</dt>
      <dd>{data.libraries.ifcopenshell ?? 'not installed'}</dd>
      <dt>IfcTester</dt>
      <dd>{data.libraries.ifctester ?? 'not installed'}</dd>
    </dl>
  );
}
