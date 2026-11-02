import { useId, useRef, useState, type KeyboardEvent, type TouchEvent } from 'react';

interface Scene {
  readonly title: string;
  readonly filename: string;
  readonly alt: string;
  readonly width: number;
  readonly height: number;
  readonly contain?: boolean;
}

const SCENES: readonly Scene[] = [
  {
    title: 'Architectural Vision',
    filename: 'architectural-vision.webp',
    alt: 'Conceptual view of a contemporary terraced office complex.',
    width: 1688,
    height: 932,
  },
  {
    title: 'Architectural Design',
    filename: 'architectural-design.webp',
    alt: 'Conceptual view of colleagues working in an architecture studio.',
    width: 1688,
    height: 932,
  },
  {
    title: 'Design Collaboration',
    filename: 'design-collaboration.webp',
    alt: 'Conceptual view of architects and engineers reviewing a design together.',
    width: 1688,
    height: 932,
  },
  {
    title: 'Construction Delivery',
    filename: 'construction-delivery.webp',
    alt: 'Conceptual view of professionals in a construction environment.',
    width: 1683,
    height: 935,
  },
  {
    title: 'Digital Twin',
    filename: 'digital-twin.webp',
    alt: 'Conceptual view of Tower Bridge represented with digital and physical geometry.',
    width: 1672,
    height: 941,
  },
  {
    title: 'BIM Intelligence',
    filename: 'bim-intelligence-concept.webp',
    alt: 'Conceptual BIM Intelligence interface shown on desktop and laptop screens.',
    width: 1086,
    height: 1448,
    contain: true,
  },
];

export function ArchitecturalReel() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [imageUnavailable, setImageUnavailable] = useState(false);
  const touchStart = useRef<{ readonly x: number; readonly y: number } | null>(null);
  const slideId = useId();
  const scene = SCENES[activeIndex];

  if (!scene) {
    throw new Error(`Unknown architectural scene index: ${activeIndex}`);
  }

  function move(amount: number) {
    setActiveIndex((current) => (current + amount + SCENES.length) % SCENES.length);
    setImageUnavailable(false);
  }

  function select(index: number) {
    setActiveIndex(index);
    setImageUnavailable(false);
  }

  function onKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      move(event.key === 'ArrowLeft' ? -1 : 1);
    }
  }

  function onTouchStart(event: TouchEvent<HTMLDivElement>) {
    const touch = event.touches.length === 1 ? event.touches[0] : undefined;
    touchStart.current = touch ? { x: touch.clientX, y: touch.clientY } : null;
  }

  function onTouchEnd(event: TouchEvent<HTMLDivElement>) {
    const start = touchStart.current;
    touchStart.current = null;
    const touch = event.changedTouches.length === 1 ? event.changedTouches[0] : undefined;
    if (!start || !touch) {
      return;
    }
    const horizontal = touch.clientX - start.x;
    const vertical = touch.clientY - start.y;
    if (Math.abs(horizontal) >= 48 && Math.abs(horizontal) > Math.abs(vertical)) {
      move(horizontal < 0 ? 1 : -1);
    }
  }

  return (
    <section
      className="architectural-reel"
      aria-label="Architectural image reel"
      aria-roledescription="carousel"
      onKeyDown={onKeyDown}
    >
      <div className="architectural-reel__frame">
        <div
          id={slideId}
          className="architectural-reel__media"
          role="group"
          aria-roledescription="slide"
          aria-label={`${activeIndex + 1} of ${SCENES.length}`}
          onTouchStart={onTouchStart}
          onTouchEnd={onTouchEnd}
          onTouchCancel={() => {
            touchStart.current = null;
          }}
        >
          {imageUnavailable ? (
            <p className="architectural-reel__error" role="alert">
              Image unavailable. Choose another scene.
            </p>
          ) : (
            <img
              key={scene.filename}
              className={
                scene.contain
                  ? 'architectural-reel__image architectural-reel__image--contain'
                  : 'architectural-reel__image'
              }
              src={`/images/home/reel/${scene.filename}`}
              alt={scene.alt}
              width={scene.width}
              height={scene.height}
              loading={activeIndex === 0 ? 'eager' : 'lazy'}
              decoding="async"
              draggable={false}
              onError={() => setImageUnavailable(true)}
            />
          )}
        </div>
        <button
          type="button"
          className="architectural-reel__arrow architectural-reel__previous"
          aria-label="Previous image"
          aria-controls={slideId}
          onClick={() => move(-1)}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M15 5 8 12l7 7" fill="none" stroke="currentColor" strokeWidth="2" />
          </svg>
        </button>
        <button
          type="button"
          className="architectural-reel__arrow architectural-reel__next"
          aria-label="Next image"
          aria-controls={slideId}
          onClick={() => move(1)}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M15 5 8 12l7 7" fill="none" stroke="currentColor" strokeWidth="2" />
          </svg>
        </button>
      </div>
      <div className="architectural-reel__details">
        <div className="architectural-reel__caption" aria-live="polite" aria-atomic="true">
          <p className="architectural-reel__label">
            <span className="architectural-reel__count">
              {String(activeIndex + 1).padStart(2, '0')} / {String(SCENES.length).padStart(2, '0')}
            </span>
            <span>{scene.title}</span>
          </p>
          <p className="architectural-reel__note">
            {scene.contain
              ? 'Concept visualisation, not a screenshot of the implemented application.'
              : 'AI-generated architectural imagery.'}
          </p>
        </div>
        <div
          className="architectural-reel__pagination"
          role="group"
          aria-label="Choose an architectural scene"
        >
          {SCENES.map((item, index) => (
            <button
              key={item.filename}
              type="button"
              className="architectural-reel__dot"
              aria-label={`Show image ${index + 1}: ${item.title}`}
              aria-controls={slideId}
              aria-pressed={index === activeIndex}
              onClick={() => select(index)}
            >
              <span aria-hidden="true" />
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
