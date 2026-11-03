import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { HealthResponse } from '../api/client';
import { HealthPanel } from './HealthPanel';

const healthy: HealthResponse = {
  status: 'ok',
  version: '0.1.0',
  llm_mode: 'off',
  llm_model: 'muse-spark-1.3',
  llm_configured: false,
  libraries: { ifcopenshell: '0.9.0.post1', ifctester: null },
};

function mockFetch(impl: () => Promise<Response>) {
  vi.stubGlobal('fetch', vi.fn(impl));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('HealthPanel', () => {
  it('shows a loading state first', () => {
    mockFetch(() => new Promise(() => {}));
    render(<HealthPanel />);
    expect(screen.getByRole('status')).toHaveTextContent(/checking backend/i);
  });

  it('shows plain-language system status and keeps diagnostics collapsed', async () => {
    mockFetch(() => Promise.resolve(Response.json(healthy)));
    render(<HealthPanel />);
    expect(await screen.findByText('Backend connected')).toBeInTheDocument();
    expect(screen.getByText(/AI review unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/deterministic reviews remain available/i)).toBeInTheDocument();
    expect(screen.queryByText('degraded')).not.toBeInTheDocument();
    expect(screen.queryByText('0.1.0')).not.toBeVisible();
    expect(screen.getByText('Technical details').closest('details')).not.toHaveAttribute('open');
    fireEvent.click(screen.getByText('Technical details'));
    expect(screen.getByText('0.1.0')).toBeVisible();
    expect(screen.getByText('0.9.0.post1')).toBeVisible();
    expect(screen.getByText('not installed')).toBeVisible();
    expect(screen.getByText('muse-spark-1.3')).toBeVisible();
  });

  it('shows an alert when the backend is unreachable', async () => {
    mockFetch(() => Promise.reject(new TypeError('Failed to fetch')));
    render(<HealthPanel />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/backend unreachable/i);
  });

  it('shows an alert with the status on a non-2xx response', async () => {
    mockFetch(() => Promise.resolve(new Response('boom', { status: 503 })));
    render(<HealthPanel />);
    expect(await screen.findByRole('alert')).toHaveTextContent('503');
  });
});
