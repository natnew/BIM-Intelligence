import type {
  ElementRecord,
  Finding,
  ModelSummary,
  ProblemDetail,
  ReviewRun,
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
    throw new ApiError(detail, response.status);
  }

  return response;
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
    throw new ApiError('This review run belongs to a different model version.');
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
