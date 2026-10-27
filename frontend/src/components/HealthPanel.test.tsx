import { render, screen } from '@testing-library/react';
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

  it('renders health data on success, including degraded badge and missing library', async () => {
    mockFetch(() => Promise.resolve(Response.json(healthy)));
    render(<HealthPanel />);
    expect(await screen.findByText('0.1.0')).toBeInTheDocument();
    expect(screen.getByText('degraded')).toBeInTheDocument();
    expect(screen.getByText('0.9.0.post1')).toBeInTheDocument();
    expect(screen.getByText('not installed')).toBeInTheDocument();
    expect(screen.getByText(/\(no key\)/)).toBeInTheDocument();
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
