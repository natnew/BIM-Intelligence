import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { createSession, fetchSession, uploadDocument, uploadModel } from '../api/bim';
import { ApiError } from '../api/client';
import type { Session } from '../api/generated/types';
import { ProjectHome } from './ProjectHome';

const session: Session = {
  id: '11111111-2222-4333-8444-555555555555',
  status: 'created',
  model_hash: null,
  document_hashes: [],
  created_at: '2026-10-30T00:00:00Z',
};
const modelHash = 'a'.repeat(64);
const summary = {
  ifc_schema: 'IFC4',
  model_hash: modelHash,
  project_name: 'Minimal fixture',
  counts: { IfcWall: 3 },
  storeys: [
    {
      global_id: 'storey',
      express_id: 1,
      ifc_type: 'IfcBuildingStorey',
      name: 'L00',
      storey: null,
    },
  ],
};

vi.mock('../api/bim', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/bim')>()),
  createSession: vi.fn(),
  fetchSession: vi.fn(),
  uploadDocument: vi.fn(),
  uploadModel: vi.fn(),
}));

vi.mock('../state/useHealth', () => ({
  useHealth: () => ({ kind: 'loading' }),
}));

describe('ProjectHome', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    vi.mocked(createSession).mockResolvedValue(session);
    vi.mocked(fetchSession).mockResolvedValue({
      ...session,
      status: 'model_ready',
      model_hash: modelHash,
    });
    vi.mocked(uploadModel).mockResolvedValue({ summary, etag: `"${modelHash}"` });
    vi.mocked(uploadDocument).mockResolvedValue({
      sha256: 'b'.repeat(64),
      kind: 'ids',
      title: 'Minimal IDS',
      requirements: [],
    });
  });

  it('renders the product identity, start routes and honest unavailable areas', () => {
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Start with the model/);
    expect(screen.getByRole('button', { name: 'Create review session' })).toBeEnabled();
    expect(screen.getByRole('heading', { name: 'Open an existing session' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Recent sessions' })).toBeInTheDocument();
    expect(screen.getByText(/Sessions you open in this browser appear here/)).toBeInTheDocument();
    expect(
      screen.getByText(/A synthetic sample project is not yet available from this page/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Native RVT, NWD and PDF files are not ingested/)).toBeInTheDocument();
    expect(screen.queryByText(/Sample Pavilion/)).not.toBeInTheDocument();
    expect(fetchSession).not.toHaveBeenCalled();
  });

  it('shows the architectural banner above the project workspace without a duplicate heading', () => {
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);

    const banner = screen.getByRole('img', {
      name: /BIM Intelligence: AI-native Architectural and Engineering BIM Model Review/,
    });
    expect(banner).toHaveAttribute('src', '/images/home/bim-intelligence-hero.webp');
    expect(banner).toHaveAttribute('width', '2172');
    expect(banner).toHaveAttribute('height', '724');
    expect(banner).toHaveAttribute('decoding', 'async');
    expect(banner).not.toHaveAttribute('loading', 'lazy');

    const workspace = screen.getByRole('region', { name: /Start with the model/ });
    expect(
      banner.compareDocumentPosition(workspace) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.queryByRole('heading', { name: /AI-native/ })).not.toBeInTheDocument();
  });

  it('places the introduction and architectural reel between the start routes and review workflow', () => {
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);

    const routes = screen.getByRole('region', { name: 'Choose how to begin' });
    const introduction = screen.getByRole('region', { name: 'From BIM review to delivery' });
    const heading = within(introduction).getByRole('heading', {
      level: 2,
      name: 'From BIM review to delivery',
    });
    const reel = within(introduction).getByRole('region', { name: 'Architectural image reel' });
    const workflow = screen.getByRole('region', { name: 'How BIM Intelligence works' });
    expect(routes.nextElementSibling).toBe(introduction);
    expect(introduction.nextElementSibling).toBe(workflow);
    expect(heading.compareDocumentPosition(reel) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(introduction).toHaveTextContent(
      'Evaluate, validate and act on your building models with BIM Intelligence — an AI-native assistant for architectural and engineering BIM review, grounded in your models, standards and project documentation.',
    );
    expect(
      within(introduction).getByText('BIM Intelligence', { selector: 'strong' }),
    ).toBeVisible();

    fireEvent.click(within(reel).getByRole('button', { name: 'Next image' }));
    expect(within(reel).getByRole('group', { name: '2 of 6' })).toBeInTheDocument();
    expect(createSession).not.toHaveBeenCalled();
    expect(fetchSession).not.toHaveBeenCalled();
  });

  it('explains the review workflow in four informational cards', () => {
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);

    const workflow = screen.getByRole('region', { name: 'How BIM Intelligence works' });
    expect(
      within(workflow).getByText(
        'From IFC model ingestion to verified findings and intelligent interpretation.',
      ),
    ).toBeInTheDocument();

    const steps = within(within(workflow).getByRole('list')).getAllByRole('listitem');
    expect(steps).toHaveLength(4);
    const expected = [
      ['Step 01: Import your model', /Upload an IFC model and its associated IDS requirements/],
      ['Step 02: Validate information', /deterministic checks against confirmed requirements/],
      ['Step 03: Investigate in 3D', /trace findings to their source requirements/],
      ['Step 04: Interpret with AI', /optional AI-assisted review objectives and grounded/],
    ] as const;
    steps.forEach((step, index) => {
      const [heading, description] = expected[index] ?? ['', /^$/];
      expect(within(step).getByRole('heading', { level: 3 })).toHaveAccessibleName(heading);
      expect(within(step).getByText(description)).toBeInTheDocument();
      const art = step.querySelector('svg');
      expect(art).toHaveAttribute('aria-hidden', 'true');
      expect(art).toHaveAttribute('focusable', 'false');
    });
    const aiNote = within(workflow).getByText(/depends on the server’s model configuration/);
    expect(aiNote).toHaveTextContent('AI output never creates findings.');
    expect(steps[3]).toContainElement(aiNote);

    expect(within(workflow).queryAllByRole('button')).toHaveLength(0);
    expect(within(workflow).queryAllByRole('link')).toHaveLength(0);
    expect(workflow.querySelector('img, [tabindex]')).toBeNull();
  });

  it('presents four non-interactive product features between the workflow and footer', () => {
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);

    const workflow = screen.getByRole('region', { name: 'How BIM Intelligence works' });
    const features = screen.getByRole('region', {
      name: 'Features for intelligent AEC model review',
    });
    expect(workflow.nextElementSibling).toBe(features);
    expect(features.nextElementSibling?.tagName).toBe('FOOTER');
    expect(features.nextElementSibling?.textContent?.replace(/\s+/g, ' ').trim()).toBe(
      'IFC files remain read-only. The viewer uses local WASM and worker assets; findings are produced deterministically by IfcTester and registered native rules. AI explanations, when requested, are interpretations labelled separately from findings.',
    );
    expect(
      within(features).getByText(
        'Technical precision, visual investigation and evidence-grounded intelligence in one review environment.',
      ),
    ).toBeInTheDocument();

    const cards = within(within(features).getByRole('list')).getAllByRole('listitem');
    const expected = [
      [
        'Interactive 3D BIM Viewer',
        'Explore IFC geometry, navigate the building model and inspect individual elements using intuitive spatial controls.',
      ],
      [
        'Requirements-Based Validation',
        'Check BIM information against confirmed IDS specifications and deterministic rules, with transparent execution coverage.',
      ],
      [
        'Traceable Review Evidence',
        'Connect model findings to affected IFC elements, requirement references and the observed information behind each result.',
      ],
      [
        'AI-Assisted Interpretation',
        'Use bounded review objectives and grounded explanations to investigate findings while keeping verified evidence distinct from AI interpretation.',
      ],
    ] as const;
    expect(cards).toHaveLength(expected.length);
    const illustrations = cards.map((card, index) => {
      const [heading, description] = expected[index] ?? ['', ''];
      expect(within(card).getByRole('heading', { level: 3, name: heading })).toBeInTheDocument();
      expect(within(card).getByText(description)).toBeInTheDocument();
      const illustration = card.querySelector('svg');
      expect(illustration).toHaveAttribute('aria-hidden', 'true');
      expect(illustration).toHaveAttribute('focusable', 'false');
      expect(illustration).toHaveAttribute('viewBox', '0 0 96 76');
      expect(illustration).toHaveAttribute('stroke', 'currentColor');
      expect(illustration).toHaveAttribute('stroke-width', '1.5');
      return illustration?.innerHTML;
    });
    expect(new Set(illustrations).size).toBe(4);
    expect(cards[3]).toHaveTextContent('AI availability depends on the server');
    expect(features.querySelector('a, button, input, [tabindex]')).toBeNull();
    expect(createSession).not.toHaveBeenCalled();
    expect(fetchSession).not.toHaveBeenCalled();
  });

  it('creates a session through the API and shows the setup sequence', async () => {
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Create review session' }));

    expect(
      await screen.findByRole('heading', { name: 'Prepare the review inputs' }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('region', { name: 'Features for intelligent AEC model review' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('region', { name: 'Architectural image reel' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('region', { name: 'From BIM review to delivery' }),
    ).not.toBeInTheDocument();
    expect(createSession).toHaveBeenCalledWith(expect.any(AbortSignal));
    expect(screen.getByText(session.id)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Open review workspace' })).toBeDisabled();
  });

  it('shows the API error when session creation fails', async () => {
    vi.mocked(createSession).mockRejectedValue(new Error('Backend unreachable.'));
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Create review session' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Backend unreachable.');
    expect(screen.getByRole('button', { name: 'Create review session' })).toBeEnabled();
  });

  it('uploads the IFC and requirements, then opens the workspace for the created session', async () => {
    const onOpenWorkspace = vi.fn();
    render(<ProjectHome onOpenWorkspace={onOpenWorkspace} />);
    fireEvent.click(screen.getByRole('button', { name: 'Create review session' }));
    await screen.findByRole('heading', { name: 'Prepare the review inputs' });

    const ifc = new File(['ISO-10303-21;'], 'minimal.ifc');
    fireEvent.change(screen.getByLabelText('Choose IFC model'), { target: { files: [ifc] } });

    expect(await screen.findByLabelText('Uploaded model summary')).toHaveTextContent(
      'Minimal fixture',
    );
    expect(uploadModel).toHaveBeenCalledWith(session.id, ifc, expect.any(AbortSignal));
    expect(screen.getByText('Indexed')).toBeInTheDocument();

    const ids = new File(['<ids/>'], 'minimal.ids');
    fireEvent.change(screen.getByLabelText('Add requirements document'), {
      target: { files: [ids] },
    });

    const list = await screen.findByRole('list', { name: 'Imported requirements documents' });
    expect(list).toHaveTextContent('minimal.ids');
    expect(uploadDocument).toHaveBeenCalledWith(session.id, ids, expect.any(AbortSignal));
    expect(screen.getByText(/without an IDS, no review can be run/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Open review workspace' }));
    expect(onOpenWorkspace).toHaveBeenCalledWith(session.id, null);
  });

  it('labels narrative documents as source text that creates no requirements', async () => {
    vi.mocked(uploadDocument).mockResolvedValue({
      sha256: 'c'.repeat(64),
      kind: 'markdown',
      title: 'Narrative requirements document',
      requirements: [],
    });
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Create review session' }));
    await screen.findByRole('heading', { name: 'Prepare the review inputs' });

    fireEvent.change(screen.getByLabelText('Add requirements document'), {
      target: { files: [new File(['# Brief'], 'brief.md')] },
    });

    expect(
      await screen.findByText(/Source text stored · no requirements created/),
    ).toBeInTheDocument();
  });

  it('rejects unsupported model and document file types without calling the API', async () => {
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Create review session' }));
    await screen.findByRole('heading', { name: 'Prepare the review inputs' });

    fireEvent.change(screen.getByLabelText('Choose IFC model'), {
      target: { files: [new File(['x'], 'model.rvt')] },
    });
    expect(await screen.findByText(/"model\.rvt" is not an IFC file/)).toBeInTheDocument();
    expect(uploadModel).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText('Add requirements document'), {
      target: { files: [new File(['x'], 'brief.pdf')] },
    });
    expect(
      await screen.findByText(/"brief\.pdf" is not a supported requirements document/),
    ).toBeInTheDocument();
    expect(uploadDocument).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Open review workspace' })).toBeDisabled();
  });

  it('surfaces a backend rejection of the model upload and allows a retry', async () => {
    vi.mocked(uploadModel).mockRejectedValueOnce(new Error('The IFC could not be parsed.'));
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Create review session' }));
    await screen.findByRole('heading', { name: 'Prepare the review inputs' });

    fireEvent.change(screen.getByLabelText('Choose IFC model'), {
      target: { files: [new File(['x'], 'broken.ifc')] },
    });

    expect(await screen.findByRole('alert')).toHaveTextContent('The IFC could not be parsed.');
    expect(screen.getByText('Rejected')).toBeInTheDocument();
    expect(screen.getByLabelText('Choose IFC model')).toBeEnabled();
  });

  it('opens an existing model-ready session directly in the workspace', async () => {
    const onOpenWorkspace = vi.fn();
    render(<ProjectHome onOpenWorkspace={onOpenWorkspace} />);

    fireEvent.change(screen.getByLabelText('Session ID'), { target: { value: ' session-id ' } });
    fireEvent.change(screen.getByLabelText('Review run ID (optional)'), {
      target: { value: 'run-id' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Open session' }));

    await waitFor(() => {
      expect(onOpenWorkspace).toHaveBeenCalledWith(session.id, 'run-id');
    });
    expect(fetchSession).toHaveBeenCalledWith('session-id', expect.any(AbortSignal));
  });

  it('routes an existing session without a model into the setup sequence', async () => {
    vi.mocked(fetchSession).mockResolvedValue(session);
    const onOpenWorkspace = vi.fn();
    render(<ProjectHome onOpenWorkspace={onOpenWorkspace} />);

    fireEvent.change(screen.getByLabelText('Session ID'), { target: { value: session.id } });
    fireEvent.click(screen.getByRole('button', { name: 'Open session' }));

    expect(
      await screen.findByRole('heading', { name: 'Prepare the review inputs' }),
    ).toBeInTheDocument();
    expect(onOpenWorkspace).not.toHaveBeenCalled();
  });

  it('confirms the indexed model version and lists imported requirements in setup', async () => {
    vi.mocked(uploadDocument).mockResolvedValue({
      sha256: 'b'.repeat(64),
      kind: 'ids',
      title: 'Minimal IDS',
      requirements: [
        {
          id: 'REQ-001',
          title: 'Fire rating present',
          statement: 'Every wall shall declare a FireRating.',
          origin: 'ids',
          status: 'confirmed',
          revision: 1,
          confirmed_revision: 1,
          confirmed_at: '2026-10-29T00:00:00Z',
          confirmed_by: 'ids-import',
          confidence: null,
          source: null,
          check: {
            id: 'check-id',
            kind: 'ids',
            rule_id: 'ids:FireRating',
            rule_version: 'rule-v1',
            params: {},
            ids_specification: null,
          },
        },
      ],
    });
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Create review session' }));
    await screen.findByRole('heading', { name: 'Prepare the review inputs' });

    fireEvent.change(screen.getByLabelText('Choose IFC model'), {
      target: { files: [new File(['ISO-10303-21;'], 'minimal.ifc')] },
    });
    const confirmation = await screen.findByText(/was stored byte-for-byte and indexed/);
    expect(confirmation).toHaveTextContent('minimal.ifc');
    expect(confirmation).toHaveTextContent(modelHash.slice(0, 12));
    expect(screen.getByLabelText('Uploaded model summary')).toHaveTextContent('Indexed instances3');

    fireEvent.change(screen.getByLabelText('Add requirements document'), {
      target: { files: [new File(['<ids/>'], 'minimal.ids')] },
    });
    expect(await screen.findByText('Requirements in this document (1)')).toBeInTheDocument();
    expect(
      screen.getByRole('list', { name: 'Requirements imported from minimal.ids' }),
    ).toHaveTextContent('REQ-001 Fire rating present · executable');
    expect(screen.getByText(/1 executable requirement are ready/)).toBeInTheDocument();
  });
});

describe('ProjectHome recent sessions', () => {
  const readySessionId = '11111111-2222-4333-8444-555555555555';
  const emptySessionId = '22222222-2222-4333-8444-555555555555';
  const missingSessionId = '33333333-2222-4333-8444-555555555555';

  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.localStorage.setItem(
      'bimi.recent-sessions.v1',
      JSON.stringify([
        { sessionId: readySessionId, runId: 'run-ready', openedAt: '2026-11-01T10:00:00Z' },
        { sessionId: emptySessionId, runId: null, openedAt: '2026-11-01T09:00:00Z' },
        { sessionId: missingSessionId, runId: null, openedAt: '2026-11-01T08:00:00Z' },
        { sessionId: '', runId: null, openedAt: 'bad' },
        'not-an-entry',
      ]),
    );
    vi.mocked(fetchSession).mockImplementation(async (sessionId) => {
      if (sessionId === readySessionId) {
        return { ...session, id: readySessionId, status: 'model_ready', model_hash: modelHash };
      }
      if (sessionId === emptySessionId) {
        return { ...session, id: emptySessionId };
      }
      throw new ApiError('Session not found.', 404);
    });
  });

  it('revalidates remembered sessions against the server and ignores malformed entries', async () => {
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);

    const list = screen.getByRole('list', { name: 'Recently opened sessions' });
    expect(list.querySelectorAll('li')).toHaveLength(3);
    expect(list).toHaveTextContent(readySessionId.slice(0, 8));
    expect(list).toHaveTextContent('run run-read');

    await waitFor(() => expect(screen.getByText('Not on server')).toBeInTheDocument());
    expect(screen.getByText('Model ready')).toBeInTheDocument();
    expect(screen.getByText('No model yet')).toBeInTheDocument();
    expect(fetchSession).toHaveBeenCalledTimes(3);
    expect(
      screen.getByRole('button', { name: `Reopen session ${missingSessionId.slice(0, 8)}` }),
    ).toBeDisabled();
  });

  it('reopens a model-ready session with its remembered run and routes an empty one into setup', async () => {
    const onOpenWorkspace = vi.fn();
    render(<ProjectHome onOpenWorkspace={onOpenWorkspace} />);

    const reopenReady = screen.getByRole('button', {
      name: `Reopen session ${readySessionId.slice(0, 8)}`,
    });
    await waitFor(() => expect(reopenReady).toBeEnabled());
    fireEvent.click(reopenReady);
    expect(onOpenWorkspace).toHaveBeenCalledWith(readySessionId, 'run-ready');

    fireEvent.click(
      screen.getByRole('button', { name: `Reopen session ${emptySessionId.slice(0, 8)}` }),
    );
    expect(
      await screen.findByRole('heading', { name: 'Prepare the review inputs' }),
    ).toBeInTheDocument();
    expect(screen.getByText(emptySessionId)).toBeInTheDocument();
    expect(onOpenWorkspace).toHaveBeenCalledTimes(1);
  });

  it('forgets a single session and clears the list from browser storage', async () => {
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);
    await waitFor(() => expect(screen.getByText('Not on server')).toBeInTheDocument());

    fireEvent.click(
      screen.getByRole('button', { name: `Forget session ${missingSessionId.slice(0, 8)}` }),
    );
    expect(screen.queryByText('Not on server')).not.toBeInTheDocument();
    expect(window.localStorage.getItem('bimi.recent-sessions.v1')).not.toContain(missingSessionId);

    fireEvent.click(screen.getByRole('button', { name: 'Clear recent sessions' }));
    expect(
      screen.queryByRole('list', { name: 'Recently opened sessions' }),
    ).not.toBeInTheDocument();
    expect(window.localStorage.getItem('bimi.recent-sessions.v1')).toBe('[]');
  });
});
