import { useId, useState } from 'react';

import type { ElementRef, ModelSummary } from '../api/generated/types';

interface ModelBrowserProps {
  readonly summary: ModelSummary;
}

const VISIBLE_CLASS_COUNT = 8;

export function ModelBrowser({ summary }: ModelBrowserProps) {
  const classCounts = Object.entries(summary.counts)
    .flatMap(([name, count]) => (typeof count === 'number' ? [{ name, count }] : []))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
  const totalInstances = classCounts.reduce((total, entry) => total + entry.count, 0);
  const leading = classCounts.slice(0, VISIBLE_CLASS_COUNT);
  const remaining = classCounts.slice(VISIBLE_CLASS_COUNT);

  return (
    <aside className="browser" aria-labelledby="browser-heading">
      <div className="panel-heading">
        <h2 id="browser-heading">Model information</h2>
        <span className="panel-heading__hint">From the indexed model</span>
      </div>

      <dl className="fact-list" aria-label="Model summary">
        <div>
          <dt>Project</dt>
          <dd>{summary.project_name ?? 'Unnamed in file'}</dd>
        </div>
        <div>
          <dt>Schema</dt>
          <dd>{summary.ifc_schema}</dd>
        </div>
        <div>
          <dt>Model version</dt>
          <dd>
            <code title={summary.model_hash}>{summary.model_hash.slice(0, 12)}</code>
          </dd>
        </div>
        <div>
          <dt>Indexed instances</dt>
          <dd>
            {totalInstances} across {classCounts.length} IFC classes
          </dd>
        </div>
      </dl>

      <section className="browser__section" aria-labelledby="storeys-heading">
        <h3 id="storeys-heading">Storeys</h3>
        {summary.storeys.length === 0 ? (
          <p className="notice">No IfcBuildingStorey was found in the model.</p>
        ) : (
          <ol className="storey-list" aria-label="Building storeys in file order">
            {summary.storeys.map((storey) => (
              <StoreyRow key={`${summary.model_hash}:${storey.express_id}`} storey={storey} />
            ))}
          </ol>
        )}
      </section>

      <section className="browser__section" aria-labelledby="classes-heading">
        <h3 id="classes-heading">Instances by IFC class</h3>
        {classCounts.length === 0 ? (
          <p className="notice">The summary reported no instance counts.</p>
        ) : (
          <>
            <ul className="class-list" aria-label="Instance counts by IFC class">
              {leading.map((entry) => (
                <ClassRow key={entry.name} name={entry.name} count={entry.count} />
              ))}
            </ul>
            {remaining.length > 0 && (
              <details className="class-list__more">
                <summary>Show {remaining.length} more classes</summary>
                <ul className="class-list" aria-label="Further instance counts by IFC class">
                  {remaining.map((entry) => (
                    <ClassRow key={entry.name} name={entry.name} count={entry.count} />
                  ))}
                </ul>
              </details>
            )}
          </>
        )}
      </section>

      <p className="browser__limits">
        A per-element tree, category visibility and hide/isolate controls are not part of this
        iteration; the summary above is the only hierarchy the API exposes.
      </p>
    </aside>
  );
}

function StoreyRow({ storey }: { readonly storey: ElementRef }) {
  const [expanded, setExpanded] = useState(false);
  const detailsId = useId();
  const hasName = storey.name !== null && storey.name.trim().length > 0;
  const name = hasName ? storey.name : 'Unnamed storey';
  const hasGlobalId = storey.global_id !== null && storey.global_id.trim().length > 0;

  return (
    <li>
      <div className="storey-list__row">
        <span className="storey-list__name" title={hasName ? storey.name : undefined}>
          {name}
        </span>
        <button
          type="button"
          className="storey-list__toggle"
          aria-label={`Details for ${name}, STEP #${storey.express_id}`}
          aria-expanded={expanded}
          aria-controls={detailsId}
          onClick={() => setExpanded((current) => !current)}
        >
          Details
        </button>
      </div>
      <dl id={detailsId} className="storey-list__details" hidden={!expanded}>
        <div>
          <dt>Original name</dt>
          <dd>{hasName ? storey.name : 'Not provided or blank'}</dd>
        </div>
        <div>
          <dt>IFC class</dt>
          <dd>{storey.ifc_type}</dd>
        </div>
        <div>
          <dt>GlobalId</dt>
          <dd>{hasGlobalId ? <code>{storey.global_id}</code> : 'Not available'}</dd>
        </div>
        <div>
          <dt>STEP Express ID</dt>
          <dd>
            <code>#{storey.express_id}</code>
          </dd>
        </div>
      </dl>
    </li>
  );
}

function ClassRow({ name, count }: { readonly name: string; readonly count: number }) {
  return (
    <li className="class-list__row">
      <span>{name}</span>
      <span className="class-list__count">{count}</span>
    </li>
  );
}
