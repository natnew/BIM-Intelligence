import type { ReactNode } from 'react';

export type AppView = 'home' | 'workspace';

interface AppHeaderProps {
  readonly view: AppView;
  readonly sessionId: string | null;
  readonly onNavigateHome: () => void;
  readonly onNavigateWorkspace: (() => void) | null;
  readonly children?: ReactNode;
}

export function AppHeader({
  view,
  sessionId,
  onNavigateHome,
  onNavigateWorkspace,
  children,
}: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="app-header__brand">
        <span className="app-header__mark" aria-hidden="true">
          BI
        </span>
        <div>
          <p className="app-header__title">BIM Intelligence</p>
          <p className="app-header__subtitle">Architectural model review</p>
        </div>
      </div>
      <nav className="app-header__nav" aria-label="Application sections">
        <button
          type="button"
          className="app-header__nav-link"
          aria-current={view === 'home' ? 'page' : undefined}
          onClick={onNavigateHome}
        >
          Project Home
        </button>
        <button
          type="button"
          className="app-header__nav-link"
          aria-current={view === 'workspace' ? 'page' : undefined}
          disabled={onNavigateWorkspace === null}
          title={onNavigateWorkspace === null ? 'Create or open a session first' : undefined}
          onClick={onNavigateWorkspace ?? undefined}
        >
          Review workspace
        </button>
      </nav>
      <div className="app-header__context">
        {sessionId && (
          <p className="app-header__session">
            <span className="app-header__session-label">Session</span>{' '}
            <code title={sessionId}>{sessionId.slice(0, 8)}</code>
          </p>
        )}
        {children}
      </div>
    </header>
  );
}
