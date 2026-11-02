import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ArchitecturalReel } from './ArchitecturalReel';

const scenes = [
  ['Architectural Vision', 'architectural-vision.webp', 1688, 932],
  ['Architectural Design', 'architectural-design.webp', 1688, 932],
  ['Design Collaboration', 'design-collaboration.webp', 1688, 932],
  ['Construction Delivery', 'construction-delivery.webp', 1683, 935],
  ['Digital Twin', 'digital-twin.webp', 1672, 941],
  ['BIM Intelligence', 'bim-intelligence-concept.webp', 1086, 1448],
] as const;

afterEach(() => {
  vi.useRealTimers();
});

describe('ArchitecturalReel', () => {
  it('shows one image at a time in the approved order and wraps after the last', () => {
    render(<ArchitecturalReel />);
    const next = screen.getByRole('button', { name: 'Next image' });

    scenes.forEach(([title, filename, width, height], index) => {
      const slide = screen.getByRole('group', { name: `${index + 1} of 6` });
      const image = within(slide).getByRole('img');
      expect(screen.getAllByRole('img')).toHaveLength(1);
      expect(image).toHaveAttribute('src', `/images/home/reel/${filename}`);
      expect(image).toHaveAttribute('width', String(width));
      expect(image).toHaveAttribute('height', String(height));
      if (index === 0) {
        expect(image).not.toHaveAttribute('loading', 'lazy');
      } else {
        expect(image).toHaveAttribute('loading', 'lazy');
      }
      expect(
        screen.getByRole('button', { name: `Show image ${index + 1}: ${title}` }),
      ).toHaveAttribute('aria-pressed', 'true');
      if (index === 5) {
        expect(image).toHaveClass('architectural-reel__image--contain');
        expect(
          screen.getByText(
            'Concept visualisation, not a screenshot of the implemented application.',
          ),
        ).toBeInTheDocument();
      }
      fireEvent.click(next);
    });

    expect(screen.getByRole('group', { name: '1 of 6' })).toBeInTheDocument();
    expect(screen.queryByText(/Concept visualisation, not a screenshot/)).not.toBeInTheDocument();
  });

  it('supports previous, pagination and arrow keys without moving focus', () => {
    render(<ArchitecturalReel />);
    const previous = screen.getByRole('button', { name: 'Previous image' });
    fireEvent.click(previous);
    expect(screen.getByRole('group', { name: '6 of 6' })).toBeInTheDocument();

    const third = screen.getByRole('button', { name: 'Show image 3: Design Collaboration' });
    fireEvent.click(third);
    expect(screen.getByRole('group', { name: '3 of 6' })).toBeInTheDocument();
    third.focus();
    expect(fireEvent.keyDown(third, { key: 'ArrowRight' })).toBe(false);
    expect(screen.getByRole('group', { name: '4 of 6' })).toBeInTheDocument();
    expect(third).toHaveFocus();
    expect(fireEvent.keyDown(third, { key: 'ArrowLeft' })).toBe(false);
    expect(screen.getByRole('group', { name: '3 of 6' })).toBeInTheDocument();
    expect(third).toHaveFocus();
  });

  it('supports horizontal touch swipes without treating vertical or short gestures as navigation', () => {
    render(<ArchitecturalReel />);
    const slide = screen.getByRole('group', { name: '1 of 6' });
    fireEvent.touchStart(slide, { touches: [{ clientX: 250, clientY: 100 }] });
    fireEvent.touchEnd(slide, { changedTouches: [{ clientX: 100, clientY: 110 }] });
    expect(screen.getByRole('group', { name: '2 of 6' })).toBeInTheDocument();

    fireEvent.touchStart(slide, { touches: [{ clientX: 100, clientY: 100 }] });
    fireEvent.touchEnd(slide, { changedTouches: [{ clientX: 120, clientY: 220 }] });
    fireEvent.touchStart(slide, { touches: [{ clientX: 100, clientY: 100 }] });
    fireEvent.touchEnd(slide, { changedTouches: [{ clientX: 130, clientY: 100 }] });
    expect(screen.getByRole('group', { name: '2 of 6' })).toBeInTheDocument();

    fireEvent.touchStart(slide, { touches: [{ clientX: 100, clientY: 100 }] });
    fireEvent.touchEnd(slide, { changedTouches: [{ clientX: 240, clientY: 105 }] });
    expect(screen.getByRole('group', { name: '1 of 6' })).toBeInTheDocument();
  });

  it('reports an image load failure and recovers when another image is selected', () => {
    render(<ArchitecturalReel />);
    fireEvent.error(screen.getByRole('img'));
    expect(screen.getByRole('alert')).toHaveTextContent('Image unavailable. Choose another scene.');

    fireEvent.click(screen.getByRole('button', { name: 'Next image' }));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('img')).toHaveAttribute(
      'src',
      '/images/home/reel/architectural-design.webp',
    );
    fireEvent.click(screen.getByRole('button', { name: 'Previous image' }));
    expect(screen.getByRole('img')).toHaveAttribute(
      'src',
      '/images/home/reel/architectural-vision.webp',
    );
  });

  it('never advances automatically', () => {
    vi.useFakeTimers();
    render(<ArchitecturalReel />);
    act(() => vi.advanceTimersByTime(30000));
    expect(screen.getByRole('group', { name: '1 of 6' })).toBeInTheDocument();
  });
});
