import { WorkflowIllustration, type WorkflowIllustrationKind } from './WorkflowIllustration';

interface WorkflowStep {
  readonly number: string;
  readonly kind: WorkflowIllustrationKind;
  readonly title: string;
  readonly description: string;
  readonly note?: string;
}

const STEPS: readonly WorkflowStep[] = [
  {
    number: '01',
    kind: 'import',
    title: 'Import your model',
    description:
      'Upload an IFC model and its associated IDS requirements to establish a traceable review session.',
  },
  {
    number: '02',
    kind: 'validate',
    title: 'Validate information',
    description:
      'Execute deterministic checks against confirmed requirements and examine the resulting review coverage.',
  },
  {
    number: '03',
    kind: 'investigate',
    title: 'Investigate in 3D',
    description:
      'Locate affected elements in the model, inspect their properties and trace findings to their source requirements.',
  },
  {
    number: '04',
    kind: 'interpret',
    title: 'Interpret with AI',
    description:
      'Use optional AI-assisted review objectives and grounded explanations to support professional assessment.',
    note: 'Availability depends on the server’s model configuration. AI output never creates findings.',
  },
];

/** UI-005B: informational overview of the review workflow; nothing here is interactive. */
export function HowItWorks() {
  return (
    <section className="workflow" aria-labelledby="workflow-heading">
      <div className="workflow__heading">
        <h2 id="workflow-heading">How BIM Intelligence works</h2>
        <p className="workflow__lede">
          From IFC model ingestion to verified findings and intelligent interpretation.
        </p>
      </div>
      <ol className="workflow-grid">
        {STEPS.map((step) => (
          <li key={step.number} className="workflow-card">
            <div className="workflow-card__art">
              <WorkflowIllustration kind={step.kind} />
            </div>
            <div className="workflow-card__body">
              <h3
                className="workflow-card__title"
                aria-label={`Step ${step.number}: ${step.title}`}
              >
                <span className="workflow-card__number">{step.number}</span>
                {step.title}
              </h3>
              <p>{step.description}</p>
              {step.note && <p className="workflow-card__note">{step.note}</p>}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
