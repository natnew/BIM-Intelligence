import { useEffect, useRef, useState, type FormEvent } from 'react';

import { ApiError } from '../api/client';
import { createSession, fetchSession } from '../api/bim';
import type { Session } from '../api/generated/types';
import { HealthPanel } from './HealthPanel';
import { ReviewSetup } from './ReviewSetup';

interface ProjectHomeProps {
  readonly onOpenWorkspace: (sessionId: string, runId: string | null) => void;
}

type StartState =
  | { readonly kind: 'idle' }
  | { readonly kind: 'creating' }
  | { readonly kind: 'opening' }
  | { readonly kind: 'error'; readonly message: string }
  | { readonly kind: 'setup'; readonly session: Session };

export function ProjectHome({ onOpenWorkspace }: ProjectHomeProps) {
  const [state, setState] = useState<StartState>({ kind: 'idle' });
  const [existingSessionId, setExistingSessionId] = useState('');
  const [existingRunId, setExistingRunId] = useState('');
  const requestRef = useRef<AbortController | null>(null);

  useEffect(() => () => requestRef.current?.abort(), []);

  const busy = state.kind === 'creating' || state.kind === 'opening';

  async function startNewReview() {
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    setState({ kind: 'creating' });
    try {
      const session = await createSession(controller.signal);
      if (!controller.signal.aborted) {
        setState({ kind: 'setup', session });
      }
    } catch (caught) {
      if (!controller.signal.aborted) {
        setState({ kind: 'error', message: messageForError(caught) });
      }
    }
  }

  async function openExisting(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const sessionId = existingSessionId.trim();
    const runId = existingRunId.trim();
    if (!sessionId) {
      return;
    }
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    setState({ kind: 'opening' });
    try {
      const session = await fetchSession(sessionId, controller.signal);
      if (controller.signal.aborted) {
        return;
      }
      if (session.status === 'model_ready') {
        onOpenWorkspace(session.id, runId || null);
      } else {
        setState({ kind: 'setup', session });
      }
    } catch (caught) {
      if (!controller.signal.aborted) {
        setState({ kind: 'error', message: messageForError(caught) });
      }
    }
  }

  if (state.kind === 'setup') {
    return (
      <main className="home" id="main">
        <ReviewSetup
          session={state.session}
          onOpenWorkspace={(sessionId) => onOpenWorkspace(sessionId, null)}
          onStartOver={() => setState({ kind: 'idle' })}
        />
      </main>
    );
  }

  return (
    <main className="home" id="main">
      <section className="hero" aria-labelledby="hero-heading">
        <div className="hero__copy">
          <p className="eyebrow">Project workspace</p>
          <h1 id="hero-heading">
            Start with the model.
            <br />
            Keep every review traceable.
          </h1>
          <p className="hero__lede">
            Upload an IFC model and its requirement documents, run a deterministic review, and
            inspect each finding against the element it concerns. Findings come from IDS and
            registered native rules only; AI explanation is never presented as evidence.
          </p>
        </div>
        <aside className="hero__aside" aria-label="Backend status">
          <h2 className="hero__aside-title">Backend status</h2>
          <HealthPanel />
        </aside>
      </section>

      <section className="routes" aria-labelledby="routes-heading">
        <div className="routes__heading">
          <h2 id="routes-heading">Choose how to begin</h2>
          <p className="routes__lede">
            Accepted inputs: <code>.ifc</code> models and <code>.ids</code>, <code>.md</code> or{' '}
            <code>.txt</code> requirement documents. Native RVT, NWD and PDF files are not ingested.
          </p>
        </div>

        {state.kind === 'error' && (
          <p role="alert" className="notice notice--error routes__alert">
            {state.message}
          </p>
        )}

        <div className="route-grid">
          <article className="route-card route-card--primary" aria-labelledby="new-review-heading">
            <span className="route-card__tag">Create session → upload → review</span>
            <h3 id="new-review-heading">New review</h3>
            <p>
              Create a review session on the server, upload one IFC model and optional requirement
              documents, then open the 3D review workspace. Sessions are unnamed; no project
              catalogue is persisted.
            </p>
            <button
              type="button"
              className="button button--primary"
              disabled={busy}
              onClick={() => void startNewReview()}
            >
              {state.kind === 'creating' ? 'Creating session…' : 'Create review session'}
            </button>
          </article>

          <article className="route-card" aria-labelledby="existing-heading">
            <span className="route-card__tag">Return to a session</span>
            <h3 id="existing-heading">Open an existing session</h3>
            <p>
              Paste a session ID from an earlier upload or API call. A review run ID is optional;
              its findings load only if the run matches the active model version.
            </p>
            <form className="existing-form" onSubmit={(event) => void openExisting(event)}>
              <label htmlFor="existing-session-id">Session ID</label>
              <input
                id="existing-session-id"
                name="session_id"
                autoComplete="off"
                required
                value={existingSessionId}
                onChange={(event) => setExistingSessionId(event.target.value)}
                placeholder="Session UUID"
              />
              <label htmlFor="existing-run-id">Review run ID (optional)</label>
              <input
                id="existing-run-id"
                name="run_id"
                autoComplete="off"
                value={existingRunId}
                onChange={(event) => setExistingRunId(event.target.value)}
                placeholder="Run ID"
              />
              <button type="submit" className="button" disabled={busy || !existingSessionId.trim()}>
                {state.kind === 'opening' ? 'Checking session…' : 'Open session'}
              </button>
            </form>
          </article>

          <article className="route-card route-card--muted" aria-labelledby="catalogue-heading">
            <span className="route-card__tag">Not available</span>
            <h3 id="catalogue-heading">Recent sessions and sample projects</h3>
            <p>
              The backend exposes individual sessions only. There is no session history endpoint and
              no curated sample catalogue, so nothing is listed here rather than showing invented
              projects.
            </p>
          </article>
        </div>
      </section>

      <footer className="home__footer">
        <p>
          IFC files remain read-only. The viewer uses local WASM and worker assets; findings are
          produced deterministically by IfcTester and registered native rules.
        </p>
      </footer>
    </main>
  );
}

function messageForError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return error instanceof Error ? error.message : 'The request failed.';
}
