import { FeatureIcon, type FeatureIconKind } from './FeatureIcon';

interface ProductFeature {
  readonly kind: FeatureIconKind;
  readonly title: string;
  readonly description: string;
  readonly note?: string;
}

const FEATURES: readonly ProductFeature[] = [
  {
    kind: 'viewer',
    title: 'Interactive 3D BIM Viewer',
    description:
      'Explore IFC geometry, navigate the building model and inspect individual elements using intuitive spatial controls.',
  },
  {
    kind: 'validation',
    title: 'Requirements-Based Validation',
    description:
      'Check BIM information against confirmed IDS specifications and deterministic rules, with transparent execution coverage.',
  },
  {
    kind: 'evidence',
    title: 'Traceable Review Evidence',
    description:
      'Connect model findings to affected IFC elements, requirement references and the observed information behind each result.',
  },
  {
    kind: 'interpretation',
    title: 'AI-Assisted Interpretation',
    description:
      'Use bounded review objectives and grounded explanations to investigate findings while keeping verified evidence distinct from AI interpretation.',
    note: 'AI availability depends on the server configuration; live provider integration remains unverified.',
  },
];

export function ProductFeatures() {
  return (
    <section className="features" aria-labelledby="features-heading">
      <div className="features__heading">
        <h2 id="features-heading">Features for intelligent AEC model review</h2>
        <p className="features__lede">
          Technical precision, visual investigation and evidence-grounded intelligence in one review
          environment.
        </p>
      </div>
      <ul className="feature-grid">
        {FEATURES.map((feature) => (
          <li key={feature.kind} className="feature-card">
            <div className="feature-card__art">
              <FeatureIcon kind={feature.kind} />
            </div>
            <h3 className="feature-card__title">{feature.title}</h3>
            <p className="feature-card__description">{feature.description}</p>
            {feature.note && <p className="feature-card__note">{feature.note}</p>}
          </li>
        ))}
      </ul>
    </section>
  );
}
