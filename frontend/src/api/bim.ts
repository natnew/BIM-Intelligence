import type {
  DocumentImport,
  ElementRecord,
  Finding,
  ModelSummary,
  ProblemDetail,
  Requirement,
  ReviewRun,
  Session,
} from './generated/types';
import { API_BASE_URL, ApiError } from './client';

export interface VersionedModel {
  readonly summary: ModelSummary;
  readonly etag: string;
  readonly bytes: ArrayBuffer;
}

export interface ReviewWorkspaceData extends VersionedModel {
  readonly sessionId: string;
  readonly runId: string;
  readonly run: ReviewRun;
  readonly findings: Finding[];
}

/** Raised when a run, file or summary names a different model version than the active one. */
export class ModelVersionMismatchError extends ApiError {
  constructor(message: string) {
    super(message, 412);
    this.name = 'ModelVersionMismatchError';
  }
}

/** The only extensions the backend upload routes accept (api/model.py, api/documents.py). */
export const MODEL_FILE_EXTENSIONS: readonly string[] = ['.ifc'];
export const DOCUMENT_FILE_EXTENSIONS: readonly string[] = ['.ids', '.md', '.txt'];

export type UploadKind = 'model' | 'ids' | 'narrative';

/** Classifies a filename by its extension; `null` means the backend would reject it (415). */
export function classifyUploadFile(filename: string): UploadKind | null {
  const leaf = filename.split(/[\\/]/).pop() ?? '';
  const dot = leaf.lastIndexOf('.');
  if (dot <= 0) {
    return null;
  }
  const extension = leaf.slice(dot).toLowerCase();
  if (MODEL_FILE_EXTENSIONS.includes(extension)) {
    return 'model';
  }
  if (extension === '.ids') {
    return 'ids';
  }
  if (DOCUMENT_FILE_EXTENSIONS.includes(extension)) {
    return 'narrative';
  }
  return null;
}

/** A review executes only requirements whose confirmed revision is the current revision. */
export function isExecutableRequirement(requirement: Requirement): boolean {
  return (
    requirement.confirmed_revision !== null &&
    requirement.confirmed_revision === requirement.revision
  );
}

function sessionPath(sessionId: string): string {
  return `${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}`;
}

function requestOptions(signal?: AbortSignal, headers?: HeadersInit): RequestInit {
  const options: RequestInit = {};
  if (headers) {
    options.headers = headers;
  }
  if (signal) {
    options.signal = signal;
  }
  return options;
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(path, { ...init, signal: init.signal ?? null });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error;
    }
    if (error instanceof TypeError) {
      throw new ApiError('Backend unreachable. Is the API running on port 8000?');
    }
    throw error;
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const problem = (await response.json()) as ProblemDetail;
      detail = problem.detail ?? problem.title ?? detail;
    } catch (error) {
      if (!(error instanceof SyntaxError)) {
        throw error;
      }
    }
    if (response.status === 412) {
      throw new ModelVersionMismatchError(detail);
    }
    throw new ApiError(detail, response.status);
  }

  return response;
}

export async function createSession(signal?: AbortSignal): Promise<Session> {
  const options = requestOptions(signal);
  options.method = 'POST';
  const response = await request(`${API_BASE_URL}/sessions`, options);
  return (await response.json()) as Session;
}

export async function fetchSession(sessionId: string, signal?: AbortSignal): Promise<Session> {
  const response = await request(sessionPath(sessionId), requestOptions(signal));
  const session = (await response.json()) as Session;
  if (session.id !== sessionId) {
    throw new ApiError('The returned session does not match the requested session.');
  }
  return session;
}

/** Uploads one `.ifc` file; the backend stores it byte-for-byte and publishes a new version. */
export async function uploadModel(
  sessionId: string,
  file: File,
  signal?: AbortSignal,
): Promise<{ summary: ModelSummary; etag: string }> {
  if (classifyUploadFile(file.name) !== 'model') {
    throw new ApiError(
      `Only ${MODEL_FILE_EXTENSIONS.join(', ')} files can be uploaded as a model.`,
    );
  }
  const form = new FormData();
  form.append('file', file, file.name);
  const options = requestOptions(signal);
  options.method = 'POST';
  options.body = form;
  const response = await request(`${sessionPath(sessionId)}/model`, options);
  const summary = (await response.json()) as ModelSummary;
  const etag = response.headers.get('ETag');
  if (etag !== `"${summary.model_hash}"`) {
    throw new ApiError('The uploaded model returned an invalid version ETag.');
  }
  return { summary, etag };
}

/** Uploads one `.ids`, `.md` or `.txt` requirements document. */
export async function uploadDocument(
  sessionId: string,
  file: File,
  signal?: AbortSignal,
): Promise<DocumentImport> {
  const kind = classifyUploadFile(file.name);
  if (kind !== 'ids' && kind !== 'narrative') {
    throw new ApiError(
      `Only ${DOCUMENT_FILE_EXTENSIONS.join(', ')} files can be uploaded as requirements.`,
    );
  }
  const form = new FormData();
  form.append('file', file, file.name);
  const options = requestOptions(signal);
  options.method = 'POST';
  options.body = form;
  const response = await request(`${sessionPath(sessionId)}/documents`, options);
  return (await response.json()) as DocumentImport;
}

export async function fetchRequirements(
  sessionId: string,
  signal?: AbortSignal,
): Promise<Requirement[]> {
  const response = await request(`${sessionPath(sessionId)}/requirements`, requestOptions(signal));
  return (await response.json()) as Requirement[];
}

async function getModelSummary(
  sessionId: string,
  etag?: string,
  signal?: AbortSignal,
): Promise<{ summary: ModelSummary; etag: string }> {
  const headers = etag ? { 'If-Match': etag } : undefined;
  const response = await request(
    `${sessionPath(sessionId)}/model/summary`,
    requestOptions(signal, headers),
  );
  const summary = (await response.json()) as ModelSummary;
  const responseEtag = response.headers.get('ETag');
  if (responseEtag !== `"${summary.model_hash}"`) {
    throw new ApiError('Model summary returned an invalid version ETag.');
  }
  return { summary, etag: responseEtag };
}

export async function loadModel(sessionId: string, signal?: AbortSignal): Promise<VersionedModel> {
  const { summary, etag } = await getModelSummary(sessionId, undefined, signal);
  const bytes = await getModelBytes(sessionId, etag, signal);
  await getModelSummary(sessionId, etag, signal);
  return { summary, etag, bytes };
}

export async function loadReviewWorkspace(
  sessionId: string,
  runId: string,
  signal?: AbortSignal,
): Promise<ReviewWorkspaceData> {
  const { summary, etag } = await getModelSummary(sessionId, undefined, signal);
  const run = await fetchReviewRun(sessionId, runId, signal);
  if (run.id !== runId || run.session_id !== sessionId) {
    throw new ApiError('The selected review run does not match the requested session and run.');
  }
  if (run.input_manifest.model_hash !== summary.model_hash) {
    throw new ModelVersionMismatchError('This review run belongs to a different model version.');
  }

  const [bytes, findings] = await Promise.all([
    getModelBytes(sessionId, etag, signal),
    fetchFindings(sessionId, runId, signal),
  ]);
  await getModelSummary(sessionId, etag, signal);
  return { sessionId, runId, summary, etag, bytes, run, findings };
}

async function getModelBytes(
  sessionId: string,
  etag: string,
  signal?: AbortSignal,
): Promise<ArrayBuffer> {
  const response = await request(
    `${sessionPath(sessionId)}/model/file`,
    requestOptions(signal, { 'If-Match': etag }),
  );
  if (response.headers.get('ETag') !== etag) {
    throw new ApiError('Model file version did not match its summary.');
  }
  return response.arrayBuffer();
}

export async function fetchFindings(
  sessionId: string,
  runId: string,
  signal?: AbortSignal,
): Promise<Finding[]> {
  const query = new URLSearchParams({ run_id: runId });
  const response = await request(
    `${sessionPath(sessionId)}/findings?${query}`,
    requestOptions(signal),
  );
  return (await response.json()) as Finding[];
}

export async function fetchReviewRun(
  sessionId: string,
  runId: string,
  signal?: AbortSignal,
): Promise<ReviewRun> {
  const response = await request(
    `${sessionPath(sessionId)}/reviews/${encodeURIComponent(runId)}`,
    requestOptions(signal),
  );
  return (await response.json()) as ReviewRun;
}

export async function startStandardReview(
  sessionId: string,
  signal?: AbortSignal,
): Promise<ReviewRun> {
  const { etag } = await getModelSummary(sessionId, undefined, signal);
  const options = requestOptions(signal, { 'If-Match': etag });
  options.method = 'POST';
  const response = await request(`${sessionPath(sessionId)}/reviews`, options);
  const run = (await response.json()) as ReviewRun;
  if (run.session_id !== sessionId) {
    throw new ApiError('The started review does not match the requested session.');
  }
  return run;
}

export async function fetchElement(
  sessionId: string,
  globalId: string,
  etag: string,
  signal?: AbortSignal,
): Promise<ElementRecord> {
  const response = await request(
    `${sessionPath(sessionId)}/elements/${encodeURIComponent(globalId)}`,
    requestOptions(signal, { 'If-Match': etag }),
  );
  return (await response.json()) as ElementRecord;
}
