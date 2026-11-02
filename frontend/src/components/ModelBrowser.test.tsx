import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { ElementRef, ModelSummary } from '../api/generated/types';
import { ModelBrowser } from './ModelBrowser';

function storey(overrides: Partial<ElementRef>): ElementRef {
  const expressId = overrides.express_id ?? 1;
  return {
    name: 'Ground floor',
    global_id: `synthetic-global-${expressId}`,
    express_id: expressId,
    ifc_type: 'IfcBuildingStorey',
    storey: null,
    ...overrides,
  };
}

function modelSummary(storeys: ElementRef[]): ModelSummary {
  return {
    project_name: 'Synthetic model',
    ifc_schema: 'IFC4',
    model_hash: 'a'.repeat(64),
    counts: { IfcWall: 3, IfcBuildingStorey: storeys.length },
    storeys,
  };
}

function detailsFor(button: HTMLElement): HTMLElement {
  const id = button.getAttribute('aria-controls');
  if (!id) {
    throw new Error('The details control must identify its details panel.');
  }
  const details = document.getElementById(id);
  if (!details) {
    throw new Error('The details panel must exist for its control.');
  }
  return details;
}

describe('UI-006B Model Browser storeys', () => {
  it('preserves original names, duplicates and the supplied file order', () => {
    const names = ['Fundament', 'Kælder', 'Grundplan', '1. Sal', '1. Sal', '1. Sal'];
    const storeys = names.map((name, index) =>
      storey({ name, global_id: `synthetic-${index}`, express_id: index + 10 }),
    );

    render(<ModelBrowser summary={modelSummary(storeys)} />);

    expect(screen.getByRole('heading', { name: 'Storeys' })).toBeInTheDocument();
    const list = screen.getByRole('list', { name: 'Building storeys in file order' });
    const rows = within(list).getAllByRole('listitem');
    expect(rows.map((row) => row.querySelector('.storey-list__name')?.textContent)).toEqual(names);
    for (const [index, row] of rows.entries()) {
      expect(within(row).getByText(`synthetic-${index}`)).not.toBeVisible();
      expect(row).not.toHaveAttribute('role', 'button');
      expect(row).not.toHaveAttribute('tabindex');
    }
    const buttons = within(list).getAllByRole('button');
    expect(buttons.map((button) => button.getAttribute('aria-label'))).toEqual(
      names.map((name, index) => `Details for ${name}, STEP #${index + 10}`),
    );
    expect(new Set(buttons.map((button) => button.getAttribute('aria-controls'))).size).toBe(
      names.length,
    );
  });

  it('reveals the exact original name, IFC class, GlobalId and Express ID on request', async () => {
    const user = userEvent.setup();
    const globalId = '0AbCdEfGhIjKlMnOpQrStU';
    render(
      <ModelBrowser
        summary={modelSummary([storey({ name: 'Kælder', global_id: globalId, express_id: 51 })])}
      />,
    );

    const button = screen.getByRole('button', { name: 'Details for Kælder, STEP #51' });
    const details = detailsFor(button);
    expect(button).toHaveAttribute('aria-expanded', 'false');
    expect(within(details).getByText(globalId)).not.toBeVisible();

    await user.click(button);

    expect(button).toHaveAttribute('aria-expanded', 'true');
    expect(within(details).getByText('Original name').nextElementSibling).toHaveTextContent(
      'Kælder',
    );
    expect(within(details).getByText('IFC class').nextElementSibling).toHaveTextContent(
      'IfcBuildingStorey',
    );
    expect(within(details).getByText('GlobalId').nextElementSibling?.textContent).toBe(globalId);
    expect(within(details).getByText('STEP Express ID').nextElementSibling).toHaveTextContent(
      '#51',
    );
    expect(within(details).getByText(globalId)).toBeVisible();
  });

  it.each([null, '', ' \t '])(
    'identifies a storey by its Express ID when GlobalId is unavailable (%s)',
    async (globalId) => {
      const user = userEvent.setup();
      render(
        <ModelBrowser
          summary={modelSummary([
            storey({ name: 'Grundplan', global_id: globalId, express_id: 303 }),
          ])}
        />,
      );

      const button = screen.getByRole('button', { name: 'Details for Grundplan, STEP #303' });
      await user.click(button);
      const details = detailsFor(button);

      expect(within(details).getByText('GlobalId').nextElementSibling).toHaveTextContent(
        'Not available',
      );
      expect(within(details).getByText('STEP Express ID').nextElementSibling).toHaveTextContent(
        '#303',
      );
    },
  );

  it('labels absent and blank names without inventing level names', async () => {
    const user = userEvent.setup();
    render(
      <ModelBrowser
        summary={modelSummary([
          storey({ name: null, express_id: 71 }),
          storey({ name: '', express_id: 72 }),
          storey({ name: ' \t ', express_id: 73 }),
        ])}
      />,
    );

    expect(screen.getAllByText('Unnamed storey')).toHaveLength(3);
    for (const expressId of [71, 72, 73]) {
      const button = screen.getByRole('button', {
        name: `Details for Unnamed storey, STEP #${expressId}`,
      });
      await user.click(button);
      expect(
        within(detailsFor(button)).getByText('Original name').nextElementSibling,
      ).toHaveTextContent('Not provided or blank');
    }
  });

  it('retains a complete long name for the tooltip and expanded details', async () => {
    const user = userEvent.setup();
    const name = `  Kælder ${'TeknikOgInstallationer'.repeat(20)}  `;
    render(<ModelBrowser summary={modelSummary([storey({ name, express_id: 87 })])} />);

    const list = screen.getByRole('list', { name: 'Building storeys in file order' });
    const displayedName = list.querySelector('.storey-list__name');
    expect(displayedName?.textContent).toBe(name);
    expect(displayedName).toHaveAttribute('title', name);

    const button = within(list).getByRole('button');
    await user.click(button);
    expect(
      within(detailsFor(button)).getByText('Original name').nextElementSibling?.textContent,
    ).toBe(name);
  });

  it('operates details with the keyboard without making the row a navigation control', async () => {
    const user = userEvent.setup();
    render(<ModelBrowser summary={modelSummary([storey({ name: '1. Sal', express_id: 93 })])} />);

    const row = within(
      screen.getByRole('list', { name: 'Building storeys in file order' }),
    ).getByRole('listitem');
    const button = within(row).getByRole('button', { name: 'Details for 1. Sal, STEP #93' });

    await user.tab();
    expect(button).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(button).toHaveAttribute('aria-expanded', 'true');
    await user.keyboard(' ');
    expect(button).toHaveAttribute('aria-expanded', 'false');
    await user.click(row);
    expect(button).toHaveAttribute('aria-expanded', 'false');
  });

  it('does not carry open details across model versions with the same Express ID', async () => {
    const user = userEvent.setup();
    const summary = modelSummary([storey({ name: 'Ground floor', express_id: 42 })]);
    const { rerender } = render(<ModelBrowser summary={summary} />);
    const button = screen.getByRole('button', { name: 'Details for Ground floor, STEP #42' });
    await user.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');

    rerender(<ModelBrowser summary={{ ...summary, model_hash: 'b'.repeat(64) }} />);

    expect(
      screen.getByRole('button', { name: 'Details for Ground floor, STEP #42' }),
    ).toHaveAttribute('aria-expanded', 'false');
  });

  it('retains the empty state and existing class-count summary', () => {
    render(<ModelBrowser summary={modelSummary([])} />);

    expect(screen.getByText('No IfcBuildingStorey was found in the model.')).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Building storeys in file order' })).toBeNull();
    expect(screen.getByRole('list', { name: 'Instance counts by IFC class' })).toHaveTextContent(
      'IfcWall3',
    );
  });
});
