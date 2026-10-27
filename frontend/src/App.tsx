import { HealthPanel } from './components/HealthPanel';

export function App() {
  return (
    <main className="app">
      <header className="app__header">
        <h1>BIM Intelligence</h1>
        <p className="app__tagline">
          AI-native architectural BIM review — deterministic findings, grounded explanations.
        </p>
      </header>
      <section aria-labelledby="status-heading" className="app__section">
        <h2 id="status-heading">Backend status</h2>
        <HealthPanel />
      </section>
      <footer className="app__footer">
        <p>
          Development build. No review functionality is implemented yet; see{' '}
          <code>docs/IMPLEMENTATION_PLAN.md</code>.
        </p>
      </footer>
    </main>
  );
}
