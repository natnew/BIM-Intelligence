import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ArchitecturalReel } from './ArchitecturalReel';

const INTERVAL = 7000;
const AI_NOTE = 'AI-generated architectural imagery.';
const CONCEPT_NOTE =
  'Concept visualisation, not a screenshot of the implemented application. It does not depict implemented clash-detection or multi-model coordination features.';

const scenes = [
  {
    title: 'Review your architectural models',
    description:
      'Upload IFC models and examine building information within a dedicated 3D review environment.',
    filename: 'architectural-vision.webp',
    alt: 'Conceptual view of a contemporary terraced office complex.',
    width: 1688,
    height: 932,
  },
  {
    title: 'Validate against project requirements',
    description:
      'Check model information against confirmed IDS requirements and trace each finding to its source.',
    filename: 'architectural-design.webp',
    alt: 'Conceptual view of colleagues working in an architecture studio.',
    width: 1688,
    height: 932,
  },
  {
    title: 'Investigate coordination issues',
    description:
      'Locate information discrepancies, inspect affected elements and support technical review discussions.',
    filename: 'design-collaboration.webp',
    alt: 'Conceptual view of architects and engineers reviewing a design together.',
    width: 1688,
    height: 932,
  },
  {
    title: 'Make findings accessible for review',
    description:
      'Use traceable model evidence to inform design reviews and construction coordination discussions.',
    filename: 'construction-delivery.webp',
    alt: 'Conceptual view of professionals in a construction environment.',
    width: 1683,
    height: 935,
  },
  {
    title: 'Support digital twin information quality',
    description:
      'Investigate the information completeness and consistency that downstream digital asset workflows depend upon.',
    filename: 'digital-twin.webp',
    alt: 'Conceptual view of Tower Bridge represented with digital and physical geometry.',
    width: 1672,
    height: 941,
  },
  {
    title: 'Bring AI into model review',
    description:
      'Use Muse Spark-assisted review planning and grounded explanations alongside deterministic BIM validation.',
    filename: 'bim-intelligence-concept.webp',
    alt: 'Conceptual BIM Intelligence interface shown on desktop and laptop screens.',
    width: 1086,
    height: 1448,
  },
] as const;

const unsupportedClaims =
  /federat|real-time|shared workspace|automatic clash|site synchron|certif|issue assignment/i;

function expectSlide(position: number) {
  expect(screen.getByRole('group', { name: `${position} of 6` })).toBeInTheDocument();
}

function activeCaption(): HTMLElement {
  const caption = document.querySelector<HTMLElement>(
    '.architectural-reel__caption:not(.architectural-reel__caption--sizer)',
  );
  if (!caption) {
    throw new Error('Active caption not rendered');
  }
  return caption;
}

function advance(ms: number) {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

function stubReducedMotion(initial: boolean) {
  const listeners = new Set<() => void>();
  const query = {
    matches: initial,
    media: '(prefers-reduced-motion: reduce)',
    addEventListener: (_type: string, listener: () => void) => listeners.add(listener),
    removeEventListener: (_type: string, listener: () => void) => listeners.delete(listener),
  };
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    value: vi.fn(() => query),
  });
  return {
    change(matches: boolean) {
      query.matches = matches;
      act(() => listeners.forEach((listener) => listener()));
    },
    listenerCount: () => listeners.size,
  };
}

function setVisibility(state: 'visible' | 'hidden') {
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => state });
  act(() => {
    document.dispatchEvent(new Event('visibilitychange'));
  });
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  Reflect.deleteProperty(window, 'matchMedia');
  Reflect.deleteProperty(document, 'visibilityState');
});

describe('ArchitecturalReel', () => {
  it('shows one image at a time in the approved order and wraps after the last', () => {
    render(<ArchitecturalReel />);
    const next = screen.getByRole('button', { name: 'Next image' });

    scenes.forEach(({ title, filename, width, height }, index) => {
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
      }
      fireEvent.click(next);
    });

    expectSlide(1);
  });

  it('displays the six product captions with the correct imagery disclosure', () => {
    render(<ArchitecturalReel />);
    const next = screen.getByRole('button', { name: 'Next image' });

    scenes.forEach(({ title, description }, index) => {
      const caption = activeCaption();
      expect(caption).toHaveTextContent(`${String(index + 1).padStart(2, '0')} / 06`);
      expect(within(caption).getByText(title)).toBeInTheDocument();
      expect(within(caption).getByText(description)).toBeInTheDocument();
      expect(within(caption).getByText(index === 5 ? CONCEPT_NOTE : AI_NOTE)).toBeInTheDocument();
      if (index !== 5) {
        expect(caption).not.toHaveTextContent(/Concept visualisation/);
      }
      expect(caption.textContent).not.toMatch(unsupportedClaims);
      fireEvent.click(next);
    });
  });

  it('keeps descriptive image alt text independent of the visible captions', () => {
    render(<ArchitecturalReel />);
    const next = screen.getByRole('button', { name: 'Next image' });

    scenes.forEach(({ title, description, alt }) => {
      const image = screen.getByRole('img');
      expect(image).toHaveAccessibleName(alt);
      expect(alt).toMatch(/^Conceptual /);
      expect(alt).not.toContain(title);
      expect(alt).not.toContain(description);
      fireEvent.click(next);
    });
  });

  it('hides caption height reservations from assistive technology', () => {
    render(<ArchitecturalReel />);
    const sizers = document.querySelectorAll('.architectural-reel__caption--sizer');
    expect(sizers).toHaveLength(6);
    sizers.forEach((sizer) => expect(sizer).toHaveAttribute('aria-hidden', 'true'));
    expect(screen.getAllByRole('button', { name: /^Show image/ })).toHaveLength(6);
  });

  it('supports previous, pagination and arrow keys without moving focus', () => {
    render(<ArchitecturalReel />);
    const previous = screen.getByRole('button', { name: 'Previous image' });
    fireEvent.click(previous);
    expectSlide(6);

    const third = screen.getByRole('button', {
      name: 'Show image 3: Investigate coordination issues',
    });
    fireEvent.click(third);
    expectSlide(3);
    third.focus();
    expect(fireEvent.keyDown(third, { key: 'ArrowRight' })).toBe(false);
    expectSlide(4);
    expect(third).toHaveFocus();
    expect(fireEvent.keyDown(third, { key: 'ArrowLeft' })).toBe(false);
    expectSlide(3);
    expect(third).toHaveFocus();
  });

  it('supports horizontal touch swipes without treating vertical or short gestures as navigation', () => {
    render(<ArchitecturalReel />);
    const slide = screen.getByRole('group', { name: '1 of 6' });
    fireEvent.touchStart(slide, { touches: [{ clientX: 250, clientY: 100 }] });
    fireEvent.touchEnd(slide, { changedTouches: [{ clientX: 100, clientY: 110 }] });
    expectSlide(2);

    fireEvent.touchStart(slide, { touches: [{ clientX: 100, clientY: 100 }] });
    fireEvent.touchEnd(slide, { changedTouches: [{ clientX: 120, clientY: 220 }] });
    fireEvent.touchStart(slide, { touches: [{ clientX: 100, clientY: 100 }] });
    fireEvent.touchEnd(slide, { changedTouches: [{ clientX: 130, clientY: 100 }] });
    expectSlide(2);

    fireEvent.touchStart(slide, { touches: [{ clientX: 100, clientY: 100 }] });
    fireEvent.touchEnd(slide, { changedTouches: [{ clientX: 240, clientY: 105 }] });
    expectSlide(1);
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

  describe('automatic rotation', () => {
    it('advances once per seven-second interval', () => {
      vi.useFakeTimers();
      render(<ArchitecturalReel />);
      expect(screen.getByRole('button', { name: 'Pause automatic image rotation' })).toBeVisible();

      advance(INTERVAL - 1);
      expectSlide(1);
      advance(1);
      expectSlide(2);
      advance(INTERVAL);
      expectSlide(3);
    });

    it('cycles through every scene and wraps from the sixth to the first', () => {
      vi.useFakeTimers();
      render(<ArchitecturalReel />);

      for (let position = 2; position <= 6; position += 1) {
        advance(INTERVAL);
        expectSlide(position);
      }
      expect(activeCaption()).toHaveTextContent(CONCEPT_NOTE);
      advance(INTERVAL);
      expectSlide(1);
      expect(screen.getByRole('img')).toHaveAttribute(
        'src',
        '/images/home/reel/architectural-vision.webp',
      );
    });

    it('pauses while a mouse hovers and resumes with a fresh interval afterwards', () => {
      vi.useFakeTimers();
      render(<ArchitecturalReel />);
      const reel = screen.getByRole('region', { name: 'Architectural image reel' });

      advance(5000);
      fireEvent.pointerEnter(reel, { pointerType: 'mouse' });
      advance(INTERVAL * 4);
      expectSlide(1);

      fireEvent.pointerLeave(reel, { pointerType: 'mouse' });
      advance(INTERVAL - 1);
      expectSlide(1);
      advance(1);
      expectSlide(2);
    });

    it('does not treat touch contact as a hover pause', () => {
      vi.useFakeTimers();
      render(<ArchitecturalReel />);
      const reel = screen.getByRole('region', { name: 'Architectural image reel' });

      fireEvent.pointerEnter(reel, { pointerType: 'touch' });
      advance(INTERVAL);
      expectSlide(2);
    });

    it('pauses while keyboard focus is inside the carousel', () => {
      vi.useFakeTimers();
      render(
        <>
          <button type="button">Outside</button>
          <ArchitecturalReel />
        </>,
      );
      const next = screen.getByRole('button', { name: 'Next image' });

      // Tab first so the browser heuristic treats the focus as keyboard-driven.
      fireEvent.keyDown(document.body, { key: 'Tab' });
      act(() => next.focus());
      advance(INTERVAL * 3);
      expectSlide(1);
      expect(activeCaption()).toHaveAttribute('aria-live', 'polite');

      act(() =>
        screen
          .getByRole('button', { name: 'Show image 2: Validate against project requirements' })
          .focus(),
      );
      advance(INTERVAL * 3);
      expectSlide(1);

      act(() => screen.getByRole('button', { name: 'Outside' }).focus());
      advance(INTERVAL);
      expectSlide(2);
      expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Outside' }));
    });

    it('keeps rotating when focus arrives from a mouse click on a control', () => {
      vi.useFakeTimers();
      render(<ArchitecturalReel />);
      const next = screen.getByRole('button', { name: 'Next image' });

      fireEvent.mouseDown(next);
      act(() => next.focus());
      fireEvent.click(next);
      expectSlide(2);
      advance(INTERVAL);
      expectSlide(3);
    });

    it('stays paused after an explicit Pause and resumes after Play', () => {
      vi.useFakeTimers();
      render(<ArchitecturalReel />);

      fireEvent.click(screen.getByRole('button', { name: 'Pause automatic image rotation' }));
      advance(INTERVAL * 5);
      expectSlide(1);
      expect(activeCaption()).toHaveAttribute('aria-live', 'polite');

      fireEvent.click(screen.getByRole('button', { name: 'Next image' }));
      advance(INTERVAL * 2);
      expectSlide(2);

      fireEvent.click(screen.getByRole('button', { name: 'Play automatic image rotation' }));
      expect(screen.getByRole('button', { name: 'Pause automatic image rotation' })).toBeVisible();
      advance(INTERVAL - 1);
      expectSlide(2);
      advance(1);
      expectSlide(3);
    });

    it('resumes immediately when Play is chosen while hovering or focused', () => {
      vi.useFakeTimers();
      render(<ArchitecturalReel />);
      const reel = screen.getByRole('region', { name: 'Architectural image reel' });
      fireEvent.pointerEnter(reel, { pointerType: 'mouse' });

      fireEvent.click(screen.getByRole('button', { name: 'Pause automatic image rotation' }));
      const play = screen.getByRole('button', { name: 'Play automatic image rotation' });
      act(() => play.focus());
      fireEvent.click(play);
      advance(INTERVAL);
      expectSlide(2);
    });

    it('restarts the interval after manual navigation without skipping a scene', () => {
      vi.useFakeTimers();
      render(<ArchitecturalReel />);
      const next = screen.getByRole('button', { name: 'Next image' });

      advance(INTERVAL - 1000);
      fireEvent.click(next);
      expectSlide(2);
      advance(INTERVAL - 1);
      expectSlide(2);
      advance(1);
      expectSlide(3);

      advance(INTERVAL - 1000);
      fireEvent.click(
        screen.getByRole('button', { name: 'Show image 3: Investigate coordination issues' }),
      );
      advance(INTERVAL - 1);
      expectSlide(3);
      advance(1);
      expectSlide(4);
    });

    it('keeps automatic changes silent for screen readers', () => {
      vi.useFakeTimers();
      render(<ArchitecturalReel />);
      expect(activeCaption()).toHaveAttribute('aria-live', 'off');
      advance(INTERVAL);
      expect(activeCaption()).toHaveAttribute('aria-live', 'off');
    });

    it('does not rotate while the browser tab is hidden', () => {
      vi.useFakeTimers();
      render(<ArchitecturalReel />);

      setVisibility('hidden');
      advance(INTERVAL * 4);
      expectSlide(1);

      setVisibility('visible');
      advance(INTERVAL - 1);
      expectSlide(1);
      advance(1);
      expectSlide(2);
    });

    it('starts paused when reduced motion is requested and plays only on explicit request', () => {
      vi.useFakeTimers();
      stubReducedMotion(true);
      render(<ArchitecturalReel />);

      expect(screen.getByRole('button', { name: 'Play automatic image rotation' })).toBeVisible();
      advance(INTERVAL * 5);
      expectSlide(1);

      fireEvent.click(screen.getByRole('button', { name: 'Play automatic image rotation' }));
      advance(INTERVAL);
      expectSlide(2);
    });

    it('stops when reduced motion is requested during rotation', () => {
      vi.useFakeTimers();
      const motion = stubReducedMotion(false);
      render(<ArchitecturalReel />);

      advance(INTERVAL);
      expectSlide(2);
      motion.change(true);
      expect(screen.getByRole('button', { name: 'Play automatic image rotation' })).toBeVisible();
      advance(INTERVAL * 3);
      expectSlide(2);
    });

    it('removes its timer and listeners on unmount', () => {
      vi.useFakeTimers();
      const motion = stubReducedMotion(false);
      const removeDocumentListener = vi.spyOn(document, 'removeEventListener');
      const { unmount } = render(<ArchitecturalReel />);
      expect(vi.getTimerCount()).toBe(1);
      expect(motion.listenerCount()).toBe(1);

      unmount();
      expect(vi.getTimerCount()).toBe(0);
      expect(motion.listenerCount()).toBe(0);
      expect(removeDocumentListener).toHaveBeenCalledWith('visibilitychange', expect.any(Function));
    });
  });
});
