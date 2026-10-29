import { HealthPanel } from './components/HealthPanel';
import { ModelWorkspace } from './components/ModelWorkspace';

export function App() {
  const search = new URLSearchParams(window.location.search);
  const initialSessionId = search.get('session_id') ?? '';
  const initialRunId = search.get('run_id') ?? '';

  return (
    <main className="app">
      <header className="app__header">
        <h1>BIM Intelligence</h1>
        <p className="app__tagline">
          Explore an IFC model and inspect deterministic review evidence by GlobalId.
        </p>
      </header>
      <section aria-labelledby="status-heading" className="app__section app__section--status">
        <h2 id="status-heading">Backend status</h2>
        <HealthPanel />
      </section>
      <ModelWorkspace initialSessionId={initialSessionId} initialRunId={initialRunId} />
      <footer className="app__footer">
        <p>IFC files remain read-only. The viewer uses local WASM and worker assets.</p>
      </footer>
    </main>
  );
}
