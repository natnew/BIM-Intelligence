import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { createSession, fetchSession, uploadDocument, uploadModel } from '../api/bim';
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
    expect(
      screen.getByRole('heading', { name: 'Recent sessions and sample projects' }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Native RVT, NWD and PDF files are not ingested/)).toBeInTheDocument();
    expect(screen.queryByText(/Sample Pavilion/)).not.toBeInTheDocument();
  });

  it('creates a session through the API and shows the setup sequence', async () => {
    render(<ProjectHome onOpenWorkspace={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Create review session' }));

    expect(
      await screen.findByRole('heading', { name: 'Prepare the review inputs' }),
    ).toBeInTheDocument();
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
});
