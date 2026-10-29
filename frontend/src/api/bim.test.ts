import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from './client';
import { fetchElement, loadModel, loadReviewWorkspace, startStandardReview } from './bim';

const modelHash = 'a'.repeat(64);
const etag = `"${modelHash}"`;
const modelSummary = {
  ifc_schema: 'IFC4',
  model_hash: modelHash,
  project_name: 'Minimal fixture',
  counts: { IfcWall: 3 },
  storeys: [],
};
const reviewRun = {
  id: 'run-id',
  session_id: 'session-id',
  status: 'completed' as const,
  plan: { checks: [] },
  plan_source: 'default' as const,
  check_results: [],
  input_manifest: {
    model_hash: modelHash,
    ids_hashes: [],
    requirement_revisions: {},
    rule_versions: {},
  },
  created_at: '2026-10-29T00:00:00Z',
  finished_at: '2026-10-29T00:00:01Z',
};
const finding = {
  id: 'finding-id',
  check_id: 'check-id',
  requirement_id: 'REQ-001',
  rule_id: 'ids:FireRating',
  rule_version: 'version',
  facet_index: 0,
  severity: 'error' as const,
  category: 'property_requirement',
  elements: [
    {
      global_id: '0QWMtUzsnUUONCUGc8Sqsa',
      express_id: 59,
      ifc_type: 'IfcWall',
      name: 'W-002',
      storey: 'L00',
    },
  ],
  observed: 'FireRating is missing.',
  expected: 'FireRating must be present.',
  method: 'ids' as const,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('version-aware BIM API requests', () => {
  it('starts a standard review against the summary version and validates the session', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(Response.json(modelSummary, { headers: { ETag: etag } }))
      .mockResolvedValueOnce(Response.json(reviewRun));
    vi.stubGlobal('fetch', fetchMock);

    await expect(startStandardReview('session-id')).resolves.toEqual(reviewRun);

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining('/sessions/session-id/reviews'),
      expect.objectContaining({ method: 'POST', headers: { 'If-Match': etag } }),
    );
  });

  it('rejects a standard-review response for another session', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(Response.json(modelSummary, { headers: { ETag: etag } }))
        .mockResolvedValueOnce(Response.json({ ...reviewRun, session_id: 'other-session' })),
    );

    await expect(startStandardReview('session-id')).rejects.toMatchObject({
      message: 'The started review does not match the requested session.',
    });
  });

  it('pins model bytes to the summary ETag and rechecks the active version', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(Response.json(modelSummary, { headers: { ETag: etag } }))
      .mockResolvedValueOnce(new Response(new Uint8Array([1, 2, 3]), { headers: { ETag: etag } }))
      .mockResolvedValueOnce(Response.json(modelSummary, { headers: { ETag: etag } }));
    vi.stubGlobal('fetch', fetchMock);

    const model = await loadModel('session-id');

    expect(model.summary.model_hash).toBe(modelHash);
    expect([...new Uint8Array(model.bytes)]).toEqual([1, 2, 3]);
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining('/model/file'),
      expect.objectContaining({ headers: { 'If-Match': etag } }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      expect.stringContaining('/model/summary'),
      expect.objectContaining({ headers: { 'If-Match': etag } }),
    );
  });

  it('surfaces a version mismatch rather than loading mixed model data', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(Response.json(modelSummary, { headers: { ETag: etag } }))
      .mockResolvedValueOnce(
        Response.json(
          { title: 'Precondition failed', detail: 'The model version changed.' },
          { status: 412 },
        ),
      );
    vi.stubGlobal('fetch', fetchMock);

    await expect(loadModel('session-id')).rejects.toMatchObject({
      message: 'The model version changed.',
      status: 412,
    });
  });

  it('sends If-Match with an element lookup', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(Response.json({ ref: { global_id: 'id' } }));
    vi.stubGlobal('fetch', fetchMock);

    await fetchElement('session-id', '0QWMtUzsnUUONCUGc8Sqsa', etag);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/elements/0QWMtUzsnUUONCUGc8Sqsa'),
      expect.objectContaining({ headers: { 'If-Match': etag } }),
    );
  });

  it('rejects a response whose body and ETag name different model versions', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(Response.json(modelSummary, { headers: { ETag: etag } }))
        .mockResolvedValueOnce(
          new Response(new Uint8Array([1]), { headers: { ETag: '"different"' } }),
        ),
    );

    await expect(loadModel('session-id')).rejects.toBeInstanceOf(ApiError);
  });

  it('loads findings only when the run manifest matches the pinned model version', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/model/summary')) {
        return Promise.resolve(Response.json(modelSummary, { headers: { ETag: etag } }));
      }
      if (url.endsWith('/reviews/run-id')) {
        return Promise.resolve(Response.json(reviewRun));
      }
      if (url.endsWith('/model/file')) {
        return Promise.resolve(
          new Response(new Uint8Array([4, 5, 6]), { headers: { ETag: etag } }),
        );
      }
      if (url.includes('/findings?')) {
        return Promise.resolve(Response.json([finding]));
      }
      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });
    vi.stubGlobal('fetch', fetchMock);

    const workspace = await loadReviewWorkspace('session-id', 'run-id');

    expect(workspace.findings).toHaveLength(1);
    expect(workspace.findings[0]?.elements[0]?.global_id).toBe('0QWMtUzsnUUONCUGc8Sqsa');
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/model/file'),
      expect.objectContaining({ headers: { 'If-Match': etag } }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/findings?run_id=run-id'),
      expect.any(Object),
    );
  });

  it('rejects findings from a run pinned to a different model version', async () => {
    const staleRun = {
      ...reviewRun,
      input_manifest: { ...reviewRun.input_manifest, model_hash: 'b'.repeat(64) },
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(Response.json(modelSummary, { headers: { ETag: etag } }))
      .mockResolvedValueOnce(Response.json(staleRun));
    vi.stubGlobal('fetch', fetchMock);

    await expect(loadReviewWorkspace('session-id', 'run-id')).rejects.toMatchObject({
      message: 'This review run belongs to a different model version.',
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
