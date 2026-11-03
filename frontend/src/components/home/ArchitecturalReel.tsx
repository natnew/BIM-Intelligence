import {
  useEffect,
  useId,
  useRef,
  useState,
  type FocusEvent,
  type KeyboardEvent,
  type PointerEvent,
  type TouchEvent,
} from 'react';

interface Scene {
  readonly title: string;
  readonly description: string;
  readonly filename: string;
  readonly alt: string;
  readonly width: number;
  readonly height: number;
  readonly contain?: boolean;
}

const AUTOPLAY_INTERVAL_MS = 7000;

const AI_IMAGERY_NOTE = 'AI-generated architectural imagery.';
const CONCEPT_NOTE =
  'Concept visualisation, not a screenshot of the implemented application. It does not depict implemented clash-detection or multi-model coordination features.';
const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

const SCENES: readonly Scene[] = [
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
    contain: true,
  },
];

function imageSource(scene: Scene): string {
  return `/images/home/reel/${scene.filename}`;
}

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia(REDUCED_MOTION_QUERY).matches;
}

function isKeyboardFocus(target: EventTarget): boolean {
  if (!(target instanceof Element)) {
    return false;
  }
  try {
    return target.matches(':focus-visible');
  } catch {
    return true;
  }
}

function SceneCaption({ scene, index }: { readonly scene: Scene; readonly index: number }) {
  return (
    <>
      <p className="architectural-reel__label">
        <span className="architectural-reel__count">
          {String(index + 1).padStart(2, '0')} / {String(SCENES.length).padStart(2, '0')}
        </span>
        <span className="architectural-reel__title">{scene.title}</span>
      </p>
      <p className="architectural-reel__description">{scene.description}</p>
      <p className="architectural-reel__note">{scene.contain ? CONCEPT_NOTE : AI_IMAGERY_NOTE}</p>
    </>
  );
}

export function ArchitecturalReel() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [imageUnavailable, setImageUnavailable] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(prefersReducedMotion);
  // Null until the visitor presses Play or Pause; an explicit choice overrides the motion default.
  const [playChoice, setPlayChoice] = useState<boolean | null>(null);
  const [hoverPaused, setHoverPaused] = useState(false);
  const [focusPaused, setFocusPaused] = useState(false);
  const [documentHidden, setDocumentHidden] = useState(() => document.visibilityState === 'hidden');
  const [timerEpoch, setTimerEpoch] = useState(0);
  const touchStart = useRef<{ readonly x: number; readonly y: number } | null>(null);
  const slideId = useId();
  const scene = SCENES[activeIndex];

  const playing = playChoice ?? !reducedMotion;
  const rotating = playing && !hoverPaused && !focusPaused && !documentHidden;

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') {
      return undefined;
    }
    const query = window.matchMedia(REDUCED_MOTION_QUERY);
    const onChange = () => setReducedMotion(query.matches);
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);

  useEffect(() => {
    const onVisibilityChange = () => setDocumentHidden(document.visibilityState === 'hidden');
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
  }, []);

  useEffect(() => {
    if (!rotating) {
      return undefined;
    }
    const upcoming = SCENES[(activeIndex + 1) % SCENES.length];
    if (upcoming && typeof Image === 'function') {
      new Image().src = imageSource(upcoming);
    }
    // Every index change, manual interaction or resume starts a fresh full interval.
    const timer = window.setTimeout(() => {
      setActiveIndex((current) => (current + 1) % SCENES.length);
      setImageUnavailable(false);
    }, AUTOPLAY_INTERVAL_MS);
    return () => window.clearTimeout(timer);
  }, [rotating, activeIndex, timerEpoch]);

  if (!scene) {
    throw new Error(`Unknown architectural scene index: ${activeIndex}`);
  }

  function restartTimer() {
    setTimerEpoch((epoch) => epoch + 1);
  }

  function move(amount: number) {
    setActiveIndex((current) => (current + amount + SCENES.length) % SCENES.length);
    setImageUnavailable(false);
    restartTimer();
  }

  function select(index: number) {
    setActiveIndex(index);
    setImageUnavailable(false);
    restartTimer();
  }

  function togglePlayback() {
    if (playing) {
      setPlayChoice(false);
      return;
    }
    setPlayChoice(true);
    // Explicit Play resumes now, even while the pointer or focus remains inside the reel.
    setHoverPaused(false);
    setFocusPaused(false);
    restartTimer();
  }

  function onKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      move(event.key === 'ArrowLeft' ? -1 : 1);
    }
  }

  function onFocus(event: FocusEvent<HTMLElement>) {
    const related = event.relatedTarget instanceof Node ? event.relatedTarget : null;
    if (!event.currentTarget.contains(related) && isKeyboardFocus(event.target)) {
      setFocusPaused(true);
    }
  }

  function onBlur(event: FocusEvent<HTMLElement>) {
    const related = event.relatedTarget instanceof Node ? event.relatedTarget : null;
    if (!event.currentTarget.contains(related)) {
      setFocusPaused(false);
    }
  }

  function onPointerEnter(event: PointerEvent<HTMLElement>) {
    if (event.pointerType === 'mouse') {
      setHoverPaused(true);
    }
  }

  function onPointerLeave(event: PointerEvent<HTMLElement>) {
    if (event.pointerType === 'mouse') {
      setHoverPaused(false);
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
      onFocus={onFocus}
      onBlur={onBlur}
      onPointerEnter={onPointerEnter}
      onPointerLeave={onPointerLeave}
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
              src={imageSource(scene)}
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
        <div className="architectural-reel__captions">
          {/* Announce user-driven changes only; automatic rotation stays silent. */}
          <div
            className="architectural-reel__caption"
            aria-live={rotating ? 'off' : 'polite'}
            aria-atomic="true"
          >
            <SceneCaption scene={scene} index={activeIndex} />
          </div>
          {/* Invisible copies reserve the tallest caption, so rotation never shifts the page. */}
          {SCENES.map((item, index) => (
            <div
              key={item.filename}
              className="architectural-reel__caption architectural-reel__caption--sizer"
              aria-hidden="true"
            >
              <SceneCaption scene={item} index={index} />
            </div>
          ))}
        </div>
        <div className="architectural-reel__controls">
          <button
            type="button"
            className="architectural-reel__playback"
            aria-label={
              playing ? 'Pause automatic image rotation' : 'Play automatic image rotation'
            }
            aria-controls={slideId}
            onClick={togglePlayback}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              {playing ? (
                <path d="M8 5v14M16 5v14" fill="none" stroke="currentColor" strokeWidth="2.5" />
              ) : (
                <path d="M8 5v14l11-7z" fill="currentColor" />
              )}
            </svg>
          </button>
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
      </div>
    </section>
  );
}
