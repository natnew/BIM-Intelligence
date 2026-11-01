import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from './client';
import {
  classifyUploadFile,
  createSession,
  explainFinding,
  fetchElement,
  fetchRequirements,
  fetchSession,
  isExecutableRequirement,
  loadModel,
  loadReviewWorkspace,
  MAX_REVIEW_OBJECTIVE_LENGTH,
  ModelVersionMismatchError,
  startObjectiveReview,
  startStandardReview,
  uploadDocument,
  uploadModel,
} from './bim';

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

    const error: unknown = await loadReviewWorkspace('session-id', 'run-id').catch(
      (caught: unknown) => caught,
    );
    expect(error).toBeInstanceOf(ModelVersionMismatchError);
    expect(error).toMatchObject({
      message: 'This review run belongs to a different model version.',
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('starts the deterministic review without an objective body (no Meta API involvement)', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(Response.json(modelSummary, { headers: { ETag: etag } }))
      .mockResolvedValueOnce(Response.json(reviewRun));
    vi.stubGlobal('fetch', fetchMock);

    await startStandardReview('session-id');

    const [, init] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(init.method).toBe('POST');
    expect(init.body).toBeUndefined();
  });
});

describe('session and upload requests', () => {
  const session = {
    id: 'session-id',
    status: 'created' as const,
    model_hash: null,
    document_hashes: [],
    created_at: '2026-10-30T00:00:00Z',
  };

  it('creates a session with POST /sessions', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(Response.json(session, { status: 201 }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(createSession()).resolves.toEqual(session);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/sessions$/),
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('rejects a session response for another id', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(Response.json(session)));

    await expect(fetchSession('other-id')).rejects.toBeInstanceOf(ApiError);
  });

  it('uploads an IFC as multipart form data to the model endpoint and returns its version', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(Response.json(modelSummary, { status: 201, headers: { ETag: etag } }));
    vi.stubGlobal('fetch', fetchMock);
    const file = new File(['ISO-10303-21;'], 'minimal.ifc');

    const result = await uploadModel('session-id', file);

    expect(result.etag).toBe(etag);
    expect(result.summary.model_hash).toBe(modelHash);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/sessions\/session-id\/model$/);
    expect(init.method).toBe('POST');
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get('file')).toBeInstanceOf(File);
  });

  it('rejects a non-IFC model upload before any request is made', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    await expect(uploadModel('session-id', new File(['x'], 'model.rvt'))).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects an uploaded model whose ETag does not name its hash', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(Response.json(modelSummary, { headers: { ETag: '"different"' } })),
    );

    await expect(uploadModel('session-id', new File(['x'], 'minimal.ifc'))).rejects.toMatchObject({
      message: 'The uploaded model returned an invalid version ETag.',
    });
  });

  it('uploads each accepted requirements document type to the documents endpoint', async () => {
    for (const name of ['minimal.ids', 'brief.md', 'notes.TXT']) {
      const fetchMock = vi
        .fn()
        .mockResolvedValueOnce(
          Response.json(
            { sha256: 'b'.repeat(64), kind: 'ids', title: 'Doc', requirements: [] },
            { status: 201 },
          ),
        );
      vi.stubGlobal('fetch', fetchMock);

      await uploadDocument('session-id', new File(['x'], name));

      const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toMatch(/\/sessions\/session-id\/documents$/);
      expect(init.method).toBe('POST');
      expect(init.body).toBeInstanceOf(FormData);
    }
  });

  it('rejects unsupported requirement documents such as PDF before any request', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    await expect(uploadDocument('session-id', new File(['x'], 'brief.pdf'))).rejects.toMatchObject({
      message: 'Only .ids, .md, .txt files can be uploaded as requirements.',
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('surfaces backend problem details for a rejected upload', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(
          Response.json(
            { title: 'Unsupported Media Type', detail: 'Only .ifc files are accepted.' },
            { status: 415 },
          ),
        ),
    );

    await expect(uploadModel('session-id', new File(['x'], 'minimal.ifc'))).rejects.toMatchObject({
      message: 'Only .ifc files are accepted.',
      status: 415,
    });
  });

  it('lists session requirements', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(Response.json([]));
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchRequirements('session-id')).resolves.toEqual([]);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/sessions\/session-id\/requirements$/),
      expect.any(Object),
    );
  });

  it('maps a 412 response to a model-version mismatch error', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(
          Response.json({ title: 'Precondition failed', detail: 'Stale.' }, { status: 412 }),
        ),
    );

    await expect(fetchElement('session-id', 'gid', etag)).rejects.toBeInstanceOf(
      ModelVersionMismatchError,
    );
  });
});

describe('upload classification and requirement execution rules', () => {
  it('classifies filenames by the backend-accepted extensions only', () => {
    expect(classifyUploadFile('model.ifc')).toBe('model');
    expect(classifyUploadFile('C:\\models\\MODEL.IFC')).toBe('model');
    expect(classifyUploadFile('spec.ids')).toBe('ids');
    expect(classifyUploadFile('brief.md')).toBe('narrative');
    expect(classifyUploadFile('brief.txt')).toBe('narrative');
    expect(classifyUploadFile('model.rvt')).toBeNull();
    expect(classifyUploadFile('model.nwd')).toBeNull();
    expect(classifyUploadFile('brief.pdf')).toBeNull();
    expect(classifyUploadFile('.ifc')).toBeNull();
    expect(classifyUploadFile('noextension')).toBeNull();
  });

  it('treats a requirement as executable only when its confirmed revision is current', () => {
    const base = {
      id: 'REQ-1',
      title: 'T',
      statement: 'S',
      origin: 'ids' as const,
      status: 'confirmed' as const,
      confidence: null,
      confirmed_at: null,
      confirmed_by: null,
      source: null,
      check: {
        id: 'c',
        kind: 'ids' as const,
        rule_id: 'ids:x',
        rule_version: 'v',
        params: {},
        ids_specification: null,
      },
    };
    expect(isExecutableRequirement({ ...base, revision: 1, confirmed_revision: 1 })).toBe(true);
    expect(isExecutableRequirement({ ...base, revision: 2, confirmed_revision: 1 })).toBe(false);
    expect(isExecutableRequirement({ ...base, revision: 1, confirmed_revision: null })).toBe(false);
  });
});

describe('objective review and finding explanation requests', () => {
  const llmRun = {
    ...reviewRun,
    plan: { checks: [{ check_id: 'check-id', reason: 'Fire safety objective.' }] },
    plan_source: 'llm' as const,
  };
  const aiExplanation = {
    finding_id: 'finding-id',
    summary: 'FireRating is missing.',
    probable_cause: 'The property was not authored.',
    corrective_action: 'Add the property.',
    citations: [],
    source: 'ai_generated' as const,
    grounding_status: 'passed' as const,
    model: 'muse-spark-1.3',
    fallback_reason: null,
  };
  const templateExplanation = {
    ...aiExplanation,
    source: 'deterministic_template' as const,
    grounding_status: 'fallback' as const,
    model: null,
    fallback_reason: 'grounding_failed' as const,
  };
  const explanationPath = '/sessions/session-id/reviews/run-id/findings/finding-id/explanation';

  it('sends the objective as JSON against the summary version and returns plan_source', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(Response.json(modelSummary, { headers: { ETag: etag } }))
      .mockResolvedValueOnce(Response.json(llmRun));
    vi.stubGlobal('fetch', fetchMock);

    const run = await startObjectiveReview('session-id', 'Check fire ratings only');

    expect(run.plan_source).toBe('llm');
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining('/sessions/session-id/reviews'),
      expect.objectContaining({
        method: 'POST',
        headers: { 'If-Match': etag, 'Content-Type': 'application/json' },
        body: JSON.stringify({ objective: 'Check fire ratings only' }),
      }),
    );
  });

  it('reports a deterministic default run unchanged rather than as AI planning', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(Response.json(modelSummary, { headers: { ETag: etag } }))
        .mockResolvedValueOnce(Response.json(reviewRun)),
    );

    const run = await startObjectiveReview('session-id', 'Check fire ratings only');

    expect(run.plan_source).toBe('default');
  });

  it.each(['', '   ', '\n\t'])('rejects a blank objective %j without a request', async (text) => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    await expect(startObjectiveReview('session-id', text)).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects an objective longer than the server limit without a request', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      startObjectiveReview('session-id', 'x'.repeat(MAX_REVIEW_OBJECTIVE_LENGTH + 1)),
    ).rejects.toMatchObject({ message: expect.stringContaining('limited') });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects an objective review that ran against another model version', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(Response.json(modelSummary, { headers: { ETag: etag } }))
        .mockResolvedValueOnce(
          Response.json({
            ...llmRun,
            input_manifest: { ...llmRun.input_manifest, model_hash: 'b'.repeat(64) },
          }),
        ),
    );

    await expect(startObjectiveReview('session-id', 'Check fire ratings')).rejects.toBeInstanceOf(
      ModelVersionMismatchError,
    );
  });

  it('requests an explanation pinned to the viewed version and keeps its labels', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(Response.json(aiExplanation));
    vi.stubGlobal('fetch', fetchMock);

    await expect(explainFinding('session-id', 'run-id', 'finding-id', etag)).resolves.toEqual(
      aiExplanation,
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(explanationPath),
      expect.objectContaining({ method: 'POST', headers: { 'If-Match': etag } }),
    );
  });

  it('returns a labelled deterministic template with its fallback reason', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(Response.json(templateExplanation)));

    const explanation = await explainFinding('session-id', 'run-id', 'finding-id', etag);

    expect(explanation.source).toBe('deterministic_template');
    expect(explanation.fallback_reason).toBe('grounding_failed');
  });

  it.each([
    { ...aiExplanation, finding_id: 'other-finding' },
    { ...aiExplanation, fallback_reason: 'grounding_failed' },
    { ...aiExplanation, model: null },
    { ...templateExplanation, fallback_reason: null },
    { ...templateExplanation, fallback_reason: undefined },
    { ...templateExplanation, fallback_reason: '' },
    { ...templateExplanation, fallback_reason: 'unrecognised_reason' },
    { ...templateExplanation, fallback_reason: 42 },
    { ...templateExplanation, model: 'muse-spark-1.3' },
    { ...templateExplanation, grounding_status: 'passed' },
  ])('rejects an explanation with inconsistent provenance %#', async (payload) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(Response.json(payload)));

    await expect(explainFinding('session-id', 'run-id', 'finding-id', etag)).rejects.toBeInstanceOf(
      ApiError,
    );
  });

  it('surfaces a run-version mismatch and a provenance conflict as errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(
          Response.json(
            { detail: 'Run run-id validated model version a but the request names b.' },
            { status: 412 },
          ),
        )
        .mockResolvedValueOnce(
          Response.json(
            { detail: 'Run run-id: The run belongs to a different session.' },
            { status: 409 },
          ),
        ),
    );

    await expect(explainFinding('session-id', 'run-id', 'finding-id', etag)).rejects.toBeInstanceOf(
      ModelVersionMismatchError,
    );
    await expect(explainFinding('session-id', 'run-id', 'finding-id', etag)).rejects.toMatchObject({
      status: 409,
    });
  });
});
