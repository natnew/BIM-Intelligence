import { AppHeader } from './components/AppHeader';
import { ModelWorkspace } from './components/ModelWorkspace';
import { ProjectHome } from './components/ProjectHome';
import { useAppLocation } from './state/useAppLocation';

export function App() {
  const [location, navigate] = useAppLocation();

  if (location.kind === 'workspace') {
    return (
      <ModelWorkspace
        key={`${location.sessionId}:${location.runId ?? ''}`}
        sessionId={location.sessionId}
        initialRunId={location.runId}
        onRunChanged={(runId) =>
          // Keep the URL shareable without remounting the workspace for the run it just produced.
          window.history.replaceState(
            null,
            '',
            `${window.location.pathname}?${new URLSearchParams({ session_id: location.sessionId, run_id: runId }).toString()}`,
          )
        }
        onReturnHome={() => navigate({ kind: 'home' })}
      />
    );
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <AppHeader
        view="home"
        sessionId={null}
        onNavigateHome={() => undefined}
        onNavigateWorkspace={null}
      />
      <ProjectHome
        onOpenWorkspace={(sessionId, runId) => navigate({ kind: 'workspace', sessionId, runId })}
      />
    </div>
  );
}
