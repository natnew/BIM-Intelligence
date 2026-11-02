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

/**
 * One recently opened session as remembered by this browser. Only server identifiers and a
 * timestamp are stored: never model bytes, file names, project names or any model metadata.
 */
interface RecentSession {
  readonly sessionId: string;
  readonly runId: string | null;
  readonly openedAt: string;
}

const RECENT_SESSIONS_STORAGE_KEY = 'bimi.recent-sessions.v1';
const MAX_RECENT_SESSIONS = 8;
const MAX_IDENTIFIER_LENGTH = 128;

function storage(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage;
  } catch {
    return null;
  }
}

function isIdentifier(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0 && value.length <= MAX_IDENTIFIER_LENGTH;
}

/** Reads the remembered sessions, discarding anything malformed rather than trusting it. */
function readRecentSessions(): RecentSession[] {
  const store = storage();
  if (!store) {
    return [];
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(store.getItem(RECENT_SESSIONS_STORAGE_KEY) ?? '[]');
  } catch {
    return [];
  }
  if (!Array.isArray(parsed)) {
    return [];
  }
  const seen = new Set<string>();
  const entries: RecentSession[] = [];
  for (const item of parsed) {
    if (typeof item !== 'object' || item === null) {
      continue;
    }
    const candidate = item as Record<string, unknown>;
    if (!isIdentifier(candidate.sessionId) || seen.has(candidate.sessionId)) {
      continue;
    }
    if (candidate.runId !== null && !isIdentifier(candidate.runId)) {
      continue;
    }
    if (typeof candidate.openedAt !== 'string') {
      continue;
    }
    seen.add(candidate.sessionId);
    entries.push({
      sessionId: candidate.sessionId,
      runId: candidate.runId,
      openedAt: candidate.openedAt,
    });
  }
  return entries.slice(0, MAX_RECENT_SESSIONS);
}

function writeRecentSessions(entries: readonly RecentSession[]): void {
  const store = storage();
  if (!store) {
    return;
  }
  try {
    store.setItem(
      RECENT_SESSIONS_STORAGE_KEY,
      JSON.stringify(entries.slice(0, MAX_RECENT_SESSIONS)),
    );
  } catch {
    // Storage may be full or disabled; recent sessions are a convenience, not a record.
  }
}

/**
 * Moves the session to the front, keeping a known run id when the new entry has none. Exported
 * for the workspace, which records the session and its latest run as they are opened; the
 * FINAL-UI-001 path allow-list keeps this helper beside the component that reads it.
 */
// oxlint-disable-next-line react/only-export-components
export function rememberRecentSession(sessionId: string, runId: string | null): void {
  if (!isIdentifier(sessionId) || (runId !== null && !isIdentifier(runId))) {
    return;
  }
  const existing = readRecentSessions();
  const previous = existing.find((entry) => entry.sessionId === sessionId);
  const entry: RecentSession = {
    sessionId,
    runId: runId ?? previous?.runId ?? null,
    openedAt: new Date().toISOString(),
  };
  writeRecentSessions([entry, ...existing.filter((item) => item.sessionId !== sessionId)]);
}

function forgetRecentSession(sessionId: string): void {
  writeRecentSessions(readRecentSessions().filter((entry) => entry.sessionId !== sessionId));
}

function clearRecentSessions(): void {
  writeRecentSessions([]);
}

type RecentCheck =
  | { readonly kind: 'checking' }
  | { readonly kind: 'available'; readonly session: Session }
  | { readonly kind: 'missing' }
  | { readonly kind: 'error'; readonly message: string };

interface RecentEntry extends RecentSession {
  readonly check: RecentCheck;
}

function withCheck(entries: RecentEntry[], sessionId: string, check: RecentCheck): RecentEntry[] {
  return entries.map((entry) => (entry.sessionId === sessionId ? { ...entry, check } : entry));
}

export function ProjectHome({ onOpenWorkspace }: ProjectHomeProps) {
  const [state, setState] = useState<StartState>({ kind: 'idle' });
  const [existingSessionId, setExistingSessionId] = useState('');
  const [existingRunId, setExistingRunId] = useState('');
  const [recents, setRecents] = useState<RecentEntry[]>(() =>
    readRecentSessions().map((entry) => ({ ...entry, check: { kind: 'checking' } })),
  );
  const requestRef = useRef<AbortController | null>(null);

  useEffect(() => () => requestRef.current?.abort(), []);

  // Revalidate each remembered session against the server; the stored list is never trusted as
  // proof that a session still exists.
  useEffect(() => {
    const controller = new AbortController();
    for (const entry of readRecentSessions()) {
      void fetchSession(entry.sessionId, controller.signal)
        .then((session) => {
          if (!controller.signal.aborted) {
            setRecents((previous) =>
              withCheck(previous, entry.sessionId, { kind: 'available', session }),
            );
          }
        })
        .catch((caught: unknown) => {
          if (controller.signal.aborted) {
            return;
          }
          const check: RecentCheck =
            caught instanceof ApiError && caught.status === 404
              ? { kind: 'missing' }
              : { kind: 'error', message: messageForError(caught) };
          setRecents((previous) => withCheck(previous, entry.sessionId, check));
        });
    }
    return () => controller.abort();
  }, []);

  function reopenRecent(entry: RecentEntry) {
    if (entry.check.kind !== 'available') {
      return;
    }
    if (entry.check.session.status === 'model_ready') {
      onOpenWorkspace(entry.sessionId, entry.runId);
    } else {
      setState({ kind: 'setup', session: entry.check.session });
    }
  }

  function forgetRecent(sessionId: string) {
    forgetRecentSession(sessionId);
    setRecents((previous) => previous.filter((entry) => entry.sessionId !== sessionId));
  }

  function clearRecents() {
    clearRecentSessions();
    setRecents([]);
  }

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
      <div className="home-banner">
        {/* The alt text repeats the words embedded in the image (WCAG 1.1.1, images of text). */}
        <img
          className="home-banner__image"
          src="/images/home/bim-intelligence-hero.webp"
          width={2172}
          height={724}
          alt="BIM Intelligence: AI-native Architectural and Engineering BIM Model Review. Review buildings and infrastructure in 3D."
          decoding="async"
          fetchPriority="high"
        />
      </div>

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
            registered native rules only. An optional review objective can narrow the checks, and an
            AI explanation can be requested per finding; neither is ever presented as evidence.
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
            An <abbr title="Information Delivery Specification (buildingSMART)">IDS</abbr> file is
            the machine-readable requirements format that produces executable checks.
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

          <article className="route-card" aria-labelledby="recent-heading">
            <span className="route-card__tag">This browser</span>
            <h3 id="recent-heading">Recent sessions</h3>
            {recents.length === 0 ? (
              <p>
                Sessions you open in this browser appear here for quick continuation. Only the
                session and run identifiers are stored locally; model files and project data stay on
                the server.
              </p>
            ) : (
              <ul className="recent-list" aria-label="Recently opened sessions">
                {recents.map((entry) => (
                  <li key={entry.sessionId} className="recent-list__item">
                    <div className="recent-list__identity">
                      <code title={entry.sessionId}>{entry.sessionId.slice(0, 8)}</code>
                      {entry.runId && (
                        <span className="recent-list__meta">
                          {' '}
                          · run <code title={entry.runId}>{entry.runId.slice(0, 8)}</code>
                        </span>
                      )}
                      <span className="recent-list__meta">
                        {' '}
                        · opened {formatOpenedAt(entry.openedAt)}
                      </span>
                    </div>
                    <RecentCheckPill check={entry.check} />
                    <div className="recent-list__actions">
                      <button
                        type="button"
                        className="button"
                        disabled={busy || entry.check.kind !== 'available'}
                        onClick={() => reopenRecent(entry)}
                        aria-label={`Reopen session ${entry.sessionId.slice(0, 8)}`}
                      >
                        Reopen
                      </button>
                      <button
                        type="button"
                        className="button button--ghost"
                        onClick={() => forgetRecent(entry.sessionId)}
                        aria-label={`Forget session ${entry.sessionId.slice(0, 8)}`}
                      >
                        Forget
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <p className="recent-list__note">
              A synthetic sample project is not yet available from this page: the fixtures are not
              served to the browser. Use New review with <code>minimal.ifc</code> and{' '}
              <code>minimal.ids</code> from <code>tests/fixtures</code>.
            </p>
            {recents.length > 0 && (
              <button type="button" className="button button--ghost" onClick={clearRecents}>
                Clear recent sessions
              </button>
            )}
          </article>
        </div>
      </section>

      <footer className="home__footer">
        <p>
          IFC files remain read-only. The viewer uses local WASM and worker assets; findings are
          produced deterministically by IfcTester and registered native rules. AI explanations, when
          requested, are interpretations labelled separately from findings.
        </p>
      </footer>
    </main>
  );
}

function RecentCheckPill({ check }: { readonly check: RecentCheck }) {
  switch (check.kind) {
    case 'checking':
      return (
        <span className="status-pill status-pill--active" role="status">
          Checking
        </span>
      );
    case 'available':
      return (
        <span className="status-pill status-pill--done">
          {check.session.status === 'model_ready' ? 'Model ready' : 'No model yet'}
        </span>
      );
    case 'missing':
      return (
        <span
          className="status-pill status-pill--error"
          title="The server no longer has this session"
        >
          Not on server
        </span>
      );
    case 'error':
      return (
        <span className="status-pill status-pill--error" title={check.message}>
          Unavailable
        </span>
      );
  }
}

function formatOpenedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'unknown time';
  }
  return date.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });
}

function messageForError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return error instanceof Error ? error.message : 'The request failed.';
}
