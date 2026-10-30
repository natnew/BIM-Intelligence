import { createElement } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { App } from './App';

vi.mock('./components/ProjectHome', () => ({
  ProjectHome: (props: { readonly onOpenWorkspace: (s: string, r: string | null) => void }) =>
    createElement(
      'button',
      { onClick: () => props.onOpenWorkspace('session-id', null) },
      'Mock open workspace',
    ),
}));

vi.mock('./components/ModelWorkspace', () => ({
  ModelWorkspace: (props: {
    readonly sessionId: string;
    readonly initialRunId: string | null;
    readonly onReturnHome: () => void;
  }) =>
    createElement(
      'div',
      { 'data-testid': 'mock-workspace' },
      `${props.sessionId}/${props.initialRunId ?? 'none'}`,
      createElement('button', { onClick: props.onReturnHome }, 'Mock return home'),
    ),
}));

describe('App view routing', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/');
  });

  afterEach(() => {
    window.history.replaceState(null, '', '/');
  });

  it('opens Project Home by default and enters the workspace with the created session', () => {
    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: 'Mock open workspace' }));

    expect(screen.getByTestId('mock-workspace')).toHaveTextContent('session-id/none');
    expect(window.location.search).toBe('?session_id=session-id');
  });

  it('deep-links into a session and run from the query string and returns home cleanly', () => {
    window.history.replaceState(null, '', '/?session_id=abc&run_id=run-1');
    render(<App />);

    expect(screen.getByTestId('mock-workspace')).toHaveTextContent('abc/run-1');

    fireEvent.click(screen.getByRole('button', { name: 'Mock return home' }));

    expect(screen.getByRole('button', { name: 'Mock open workspace' })).toBeInTheDocument();
    expect(window.location.search).toBe('');
  });
});
