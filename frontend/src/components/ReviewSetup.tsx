import { useEffect, useRef, useState, type ChangeEvent } from 'react';

import { ApiError } from '../api/client';
import {
  DOCUMENT_FILE_EXTENSIONS,
  MODEL_FILE_EXTENSIONS,
  classifyUploadFile,
  isExecutableRequirement,
  uploadDocument,
  uploadModel,
} from '../api/bim';
import type { DocumentImport, ModelSummary, Session } from '../api/generated/types';

interface ReviewSetupProps {
  readonly session: Session;
  readonly onOpenWorkspace: (sessionId: string) => void;
  readonly onStartOver: () => void;
}

type ModelStep =
  | { readonly kind: 'idle' }
  | { readonly kind: 'uploading'; readonly filename: string }
  | { readonly kind: 'ready'; readonly filename: string; readonly summary: ModelSummary | null }
  | { readonly kind: 'error'; readonly filename: string; readonly message: string };

type DocumentStep =
  | { readonly kind: 'idle' }
  | { readonly kind: 'uploading'; readonly filename: string }
  | { readonly kind: 'error'; readonly filename: string; readonly message: string };

interface ImportedDocument {
  readonly filename: string;
  readonly result: DocumentImport;
}

export function ReviewSetup({ session, onOpenWorkspace, onStartOver }: ReviewSetupProps) {
  const [modelStep, setModelStep] = useState<ModelStep>(
    session.model_hash
      ? { kind: 'ready', filename: 'Existing model version', summary: null }
      : { kind: 'idle' },
  );
  const [documentStep, setDocumentStep] = useState<DocumentStep>({ kind: 'idle' });
  const [documents, setDocuments] = useState<ImportedDocument[]>([]);
  const requestRef = useRef<AbortController | null>(null);

  useEffect(() => () => requestRef.current?.abort(), []);

  const modelReady = modelStep.kind === 'ready';
  const busy = modelStep.kind === 'uploading' || documentStep.kind === 'uploading';
  const executableCount = documents.reduce(
    (total, item) => total + item.result.requirements.filter(isExecutableRequirement).length,
    0,
  );
  const hasNarrative = documents.some((item) => item.result.kind !== 'ids');

  async function handleModelChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) {
      return;
    }
    if (classifyUploadFile(file.name) !== 'model') {
      setModelStep({
        kind: 'error',
        filename: file.name,
        message: `"${file.name}" is not an IFC file. Only ${MODEL_FILE_EXTENSIONS.join(', ')} is accepted; native RVT, NWD and PDF files cannot be ingested.`,
      });
      return;
    }
    const controller = new AbortController();
    requestRef.current = controller;
    setModelStep({ kind: 'uploading', filename: file.name });
    try {
      const { summary } = await uploadModel(session.id, file, controller.signal);
      if (!controller.signal.aborted) {
        setModelStep({ kind: 'ready', filename: file.name, summary });
      }
    } catch (caught) {
      if (!controller.signal.aborted) {
        setModelStep({ kind: 'error', filename: file.name, message: messageForError(caught) });
      }
    }
  }

  async function handleDocumentChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) {
      return;
    }
    const kind = classifyUploadFile(file.name);
    if (kind !== 'ids' && kind !== 'narrative') {
      setDocumentStep({
        kind: 'error',
        filename: file.name,
        message: `"${file.name}" is not a supported requirements document. Use ${DOCUMENT_FILE_EXTENSIONS.join(', ')}; PDF and DOCX are not accepted.`,
      });
      return;
    }
    const controller = new AbortController();
    requestRef.current = controller;
    setDocumentStep({ kind: 'uploading', filename: file.name });
    try {
      const result = await uploadDocument(session.id, file, controller.signal);
      if (!controller.signal.aborted) {
        setDocuments((previous) => [...previous, { filename: file.name, result }]);
        setDocumentStep({ kind: 'idle' });
      }
    } catch (caught) {
      if (!controller.signal.aborted) {
        setDocumentStep({ kind: 'error', filename: file.name, message: messageForError(caught) });
      }
    }
  }

  return (
    <section className="setup" aria-labelledby="setup-heading">
      <div className="setup__heading">
        <div>
          <p className="eyebrow">Review setup</p>
          <h2 id="setup-heading">Prepare the review inputs</h2>
          <p className="setup__lede">
            Session <code>{session.id}</code> was created on the server. Sessions are unnamed; the
            backend does not persist project names or a project catalogue.
          </p>
        </div>
        <button type="button" className="button button--ghost" onClick={onStartOver}>
          Start over
        </button>
      </div>

      <ol className="setup__steps">
        <li className="setup-step setup-step--done">
          <div className="setup-step__header">
            <span className="setup-step__index" aria-hidden="true">
              1
            </span>
            <h3>Review session</h3>
            <span className="status-pill status-pill--done">Created</span>
          </div>
          <p className="setup-step__body">
            Status <code>{session.status}</code>. Uploads below are scoped to this session only.
          </p>
        </li>

        <li className={`setup-step ${modelReady ? 'setup-step--done' : ''}`}>
          <div className="setup-step__header">
            <span className="setup-step__index" aria-hidden="true">
              2
            </span>
            <h3>IFC model</h3>
            <ModelStatusPill step={modelStep} />
          </div>
          <p className="setup-step__body">
            One <code>.ifc</code> file (IFC2X3, IFC4 or IFC4X3). The file is stored byte-for-byte
            and indexed; it is never modified. Re-uploading replaces the active model version.
          </p>
          <label className="file-field">
            <span className="file-field__label">
              {modelReady ? 'Replace IFC model' : 'Choose IFC model'}
            </span>
            <input
              type="file"
              accept=".ifc"
              disabled={busy}
              onChange={(event) => void handleModelChange(event)}
            />
          </label>
          {modelStep.kind === 'uploading' && (
            <p role="status" className="notice">
              Uploading and indexing <strong>{modelStep.filename}</strong>… the backend parses the
              model synchronously, so no transfer percentage is available.
            </p>
          )}
          {modelStep.kind === 'error' && (
            <p role="alert" className="notice notice--error">
              {modelStep.message}
            </p>
          )}
          {modelStep.kind === 'ready' && modelStep.summary && (
            <>
              <p role="status" className="notice setup-confirmation">
                <strong>{modelStep.filename}</strong> was stored byte-for-byte and indexed as model
                version <code>{modelStep.summary.model_hash.slice(0, 12)}</code>. The workspace will
                show this version.
              </p>
              <dl className="setup-summary" aria-label="Uploaded model summary">
                <div>
                  <dt>File</dt>
                  <dd>{modelStep.filename}</dd>
                </div>
                <div>
                  <dt>Project</dt>
                  <dd>{modelStep.summary.project_name ?? 'Unnamed in file'}</dd>
                </div>
                <div>
                  <dt>Schema</dt>
                  <dd>{modelStep.summary.ifc_schema}</dd>
                </div>
                <div>
                  <dt>Storeys</dt>
                  <dd>{modelStep.summary.storeys.length}</dd>
                </div>
                <div>
                  <dt>Indexed instances</dt>
                  <dd>{countInstances(modelStep.summary)}</dd>
                </div>
                <div>
                  <dt>Model version</dt>
                  <dd>
                    <code>{modelStep.summary.model_hash.slice(0, 12)}</code>
                  </dd>
                </div>
              </dl>
            </>
          )}
        </li>

        <li className={`setup-step ${documents.length > 0 ? 'setup-step--done' : ''}`}>
          <div className="setup-step__header">
            <span className="setup-step__index" aria-hidden="true">
              3
            </span>
            <h3>Project requirements</h3>
            <span className="status-pill">
              {documents.length === 0
                ? 'Optional'
                : `${documents.length} document${documents.length === 1 ? '' : 's'}`}
            </span>
          </div>
          <p className="setup-step__body">
            An <abbr title="Information Delivery Specification (buildingSMART)">IDS</abbr>{' '}
            <code>.ids</code> specification becomes confirmed, <em>executable</em> requirements:
            checks the deterministic engine can run. <code>.md</code> and <code>.txt</code> briefs
            are stored as untrusted source text only; they create no requirements until separately
            interpreted and confirmed, which this interface does not yet offer.
          </p>
          <label className="file-field">
            <span className="file-field__label">Add requirements document</span>
            <input
              type="file"
              accept=".ids,.md,.txt"
              disabled={busy}
              onChange={(event) => void handleDocumentChange(event)}
            />
          </label>
          {documentStep.kind === 'uploading' && (
            <p role="status" className="notice">
              Uploading <strong>{documentStep.filename}</strong>…
            </p>
          )}
          {documentStep.kind === 'error' && (
            <p role="alert" className="notice notice--error">
              {documentStep.message}
            </p>
          )}
          {documents.length > 0 && (
            <ul className="document-list" aria-label="Imported requirements documents">
              {documents.map((item) => (
                <li key={`${item.result.sha256}-${item.filename}`} className="document-list__item">
                  <div className="document-list__summary">
                    <div>
                      <strong>{item.filename}</strong>
                      <span className="document-list__meta">
                        {' '}
                        · {item.result.kind.toUpperCase()} · {item.result.title}
                      </span>
                    </div>
                    <span className="document-list__count">
                      {item.result.kind === 'ids'
                        ? `${item.result.requirements.filter(isExecutableRequirement).length} executable requirement${item.result.requirements.filter(isExecutableRequirement).length === 1 ? '' : 's'}`
                        : 'Source text stored · no requirements created'}
                    </span>
                  </div>
                  {item.result.requirements.length > 0 && (
                    <details className="document-list__requirements">
                      <summary>
                        Requirements in this document ({item.result.requirements.length})
                      </summary>
                      <ul aria-label={`Requirements imported from ${item.filename}`}>
                        {item.result.requirements.map((requirement) => (
                          <li key={requirement.id}>
                            <code>{requirement.id}</code> {requirement.title}
                            <span className="document-list__meta">
                              {' '}
                              ·{' '}
                              {isExecutableRequirement(requirement)
                                ? 'executable'
                                : requirement.status}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </li>
              ))}
            </ul>
          )}
        </li>

        <li className="setup-step">
          <div className="setup-step__header">
            <span className="setup-step__index" aria-hidden="true">
              4
            </span>
            <h3>Open the review workspace</h3>
          </div>
          <p className="setup-step__body">
            {modelReady
              ? executableCount > 0
                ? `The model and ${executableCount} executable requirement${executableCount === 1 ? '' : 's'} are ready. Start an AI review in the workspace; its plan is limited to confirmed requirements, and findings come from deterministic checks.`
                : 'The model can be viewed now. A review needs at least one confirmed executable requirement; without an IDS, no review can be run or reported as complete.'
              : 'Upload an IFC model to continue.'}
            {hasNarrative &&
              ' Narrative documents remain source material only and do not count towards executable requirements.'}
          </p>
          <button
            type="button"
            className="button button--primary"
            disabled={!modelReady || busy}
            onClick={() => onOpenWorkspace(session.id)}
          >
            Open review workspace
          </button>
        </li>
      </ol>
    </section>
  );
}

function ModelStatusPill({ step }: { readonly step: ModelStep }) {
  switch (step.kind) {
    case 'idle':
      return <span className="status-pill">Required</span>;
    case 'uploading':
      return <span className="status-pill status-pill--active">Uploading</span>;
    case 'ready':
      return <span className="status-pill status-pill--done">Indexed</span>;
    case 'error':
      return <span className="status-pill status-pill--error">Rejected</span>;
  }
}

function countInstances(summary: ModelSummary): number {
  return Object.values(summary.counts).reduce<number>((total, count) => total + (count ?? 0), 0);
}

function messageForError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return error instanceof Error ? error.message : 'The upload failed.';
}
