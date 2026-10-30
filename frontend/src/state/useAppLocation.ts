import { useCallback, useEffect, useState } from 'react';

export type AppLocation =
  | { readonly kind: 'home' }
  | { readonly kind: 'workspace'; readonly sessionId: string; readonly runId: string | null };

/** Reads the view from the query string; `session_id` opens the workspace, `run_id` is optional. */
export function parseAppLocation(search: string): AppLocation {
  const params = new URLSearchParams(search);
  const sessionId = params.get('session_id')?.trim() ?? '';
  if (!sessionId) {
    return { kind: 'home' };
  }
  const runId = params.get('run_id')?.trim() ?? '';
  return { kind: 'workspace', sessionId, runId: runId || null };
}

export function searchForLocation(location: AppLocation): string {
  if (location.kind === 'home') {
    return '';
  }
  const params = new URLSearchParams({ session_id: location.sessionId });
  if (location.runId) {
    params.set('run_id', location.runId);
  }
  return `?${params.toString()}`;
}

/**
 * Minimal history-backed view state: the query string is the only persisted navigation state,
 * so a page refresh reopens the same session and run without any client-side storage.
 */
export function useAppLocation(): readonly [
  AppLocation,
  (next: AppLocation, mode?: 'push' | 'replace') => void,
] {
  const [location, setLocation] = useState<AppLocation>(() =>
    parseAppLocation(window.location.search),
  );

  useEffect(() => {
    function handlePopState() {
      setLocation(parseAppLocation(window.location.search));
    }
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = useCallback((next: AppLocation, mode: 'push' | 'replace' = 'push') => {
    const url = `${window.location.pathname}${searchForLocation(next)}`;
    if (mode === 'push') {
      window.history.pushState(null, '', url);
    } else {
      window.history.replaceState(null, '', url);
    }
    setLocation(next);
  }, []);

  return [location, navigate] as const;
}
