/* eslint-disable */
/**
 * GENERATED FILE — do not edit.
 *
 * Source: backend/bim_intelligence/schemas (Pydantic v2) → bim_intelligence.schema.json →
 * this file. Regenerate with `python scripts/export_schemas.py` at the repository root,
 * then `npm run types:generate` here. `npm run types:check` fails CI when stale.
 */

export type JsonValue = unknown;

/**
 * Generated from backend/bim_intelligence/schemas by scripts/export_schemas.py. Do not edit by hand.
 */
export interface BimIntelligenceContracts {
  readonly checkResult?: CheckResult;
  readonly checkSpec?: CheckSpec;
  readonly elementRef?: ElementRef;
  readonly finding?: Finding;
  readonly inputManifest?: InputManifest;
  readonly modelSummary?: ModelSummary;
  readonly plannedCheck?: PlannedCheck;
  readonly problemDetail?: ProblemDetail;
  readonly requirement?: Requirement;
  readonly requirementSource?: RequirementSource;
  readonly reviewPlan?: ReviewPlan;
  readonly reviewRun?: ReviewRun;
}
/**
 * Execution outcome of one planned check.
 */
export interface CheckResult {
  /**
   * Elements the check applied to.
   */
  readonly applicable_count: number;
  readonly check_id: string;
  /**
   * Engine messages; required for status 'error'.
   */
  readonly diagnostics: string[];
  readonly finding_ids: string[];
  readonly requirement_id: string;
  readonly status: 'passed' | 'failed' | 'error' | 'skipped' | 'not_applicable';
}
/**
 * One executable check, compiled from exactly one requirement.
 */
export interface CheckSpec {
  /**
   * Content hash of kind, rule_id, rule_version and payload. Derived automatically when omitted; rejected when supplied and inconsistent.
   */
  readonly id: string;
  /**
   * Serialised IDS 1.0 <specification> element for ids checks.
   */
  readonly ids_specification: string | null;
  readonly kind: 'ids' | 'native';
  /**
   * Native rule parameters; must be empty for ids checks.
   */
  readonly params: {
    [k: string]: JsonValue | undefined;
  };
  /**
   * IDS specification reference (``ids:<name>``) or registered native rule id.
   */
  readonly rule_id: string;
  /**
   * IDS: hash of the specification XML. Native: the rule's semantic version.
   */
  readonly rule_version: string;
}
/**
 * A reference to one entity in the uploaded model.
 */
export interface ElementRef {
  /**
   * STEP instance id (#n) within the stored file.
   */
  readonly express_id: number;
  /**
   * IFC GlobalId; None for entities that are not IfcRoot subtypes.
   */
  readonly global_id: string | null;
  readonly ifc_type: string;
  readonly name: string | null;
  /**
   * Name of the containing storey.
   */
  readonly storey: string | null;
}
/**
 * One verified defect affecting one or more elements.
 */
export interface Finding {
  readonly category: string;
  /**
   * Id of the CheckSpec that produced it.
   */
  readonly check_id: string;
  /**
   * Affected elements, canonical order.
   *
   * @minItems 1
   */
  readonly elements: [ElementRef, ...ElementRef[]];
  /**
   * What the requirement demanded.
   */
  readonly expected: string;
  /**
   * Index of the failing requirement facet within the check; 0 for native.
   */
  readonly facet_index: number;
  /**
   * sha1(check_id | rule_version | facet_index | sorted element keys)[:16]. Derived automatically when omitted; rejected when supplied and inconsistent.
   */
  readonly id: string;
  readonly method: 'ids' | 'native';
  /**
   * What the deterministic engine found.
   */
  readonly observed: string;
  readonly requirement_id: string;
  readonly rule_id: string;
  readonly rule_version: string;
  readonly severity: 'error' | 'warning' | 'info';
}
/**
 * Everything that determines a run's findings; two runs with equal manifests must agree.
 */
export interface InputManifest {
  /**
   * Items: Lower-case SHA-256 hex.
   */
  readonly ids_hashes: string[];
  /**
   * Lower-case SHA-256 hex.
   */
  readonly model_hash: string;
  readonly requirement_revisions: {
    [k: string]: number | undefined;
  };
  readonly rule_versions: {
    [k: string]: string | undefined;
  };
}
/**
 * Headline facts about an uploaded model, produced once per upload.
 */
export interface ModelSummary {
  /**
   * Number of instances per IFC class, keyed by class name (e.g. IfcWall).
   */
  readonly counts: {
    [k: string]: number | undefined;
  };
  /**
   * Schema identifier read from the file.
   */
  readonly ifc_schema: string;
  /**
   * Lower-case SHA-256 hex.
   */
  readonly model_hash: string;
  readonly project_name: string | null;
  /**
   * Building storeys in file order.
   */
  readonly storeys: ElementRef[];
}
/**
 * A plan item: which confirmed check to run and why. Never carries parameters.
 */
export interface PlannedCheck {
  readonly check_id: string;
  readonly reason: string;
}
/**
 * ``application/problem+json`` body.
 */
export interface ProblemDetail {
  /**
   * Request correlation id for matching against the run log.
   */
  readonly correlation_id: string | null;
  /**
   * Occurrence-specific explanation.
   */
  readonly detail: string | null;
  /**
   * URI of the specific occurrence.
   */
  readonly instance: string | null;
  readonly status: number;
  /**
   * Short, stable summary of the problem type.
   */
  readonly title: string;
  /**
   * URI identifying the problem type.
   */
  readonly type: string;
}
/**
 * A single reviewable requirement bound to exactly one CheckSpec.
 */
export interface Requirement {
  readonly check: CheckSpec;
  /**
   * Model self-report; a sorting aid only.
   */
  readonly confidence: number | null;
  readonly confirmed_at: string | null;
  readonly confirmed_by: string | null;
  /**
   * Revision the user confirmed, if any.
   */
  readonly confirmed_revision: number | null;
  readonly id: string;
  readonly origin: 'document' | 'ids' | 'builtin';
  readonly revision: number;
  readonly source: RequirementSource | null;
  readonly statement: string;
  readonly status: 'proposed' | 'confirmed' | 'edited' | 'rejected' | 'informational';
  readonly title: string;
}
/**
 * Where a document-derived requirement came from; the quote is verbatim (FR-REQ-02).
 */
export interface RequirementSource {
  readonly document_id: string;
  /**
   * Paragraph or page identifier.
   */
  readonly location: string;
  /**
   * Exact substring of the extracted text.
   */
  readonly quote: string;
}
/**
 * The ordered set of checks a run intends to execute (plan-then-execute, C-01).
 */
export interface ReviewPlan {
  readonly checks: PlannedCheck[];
}
/**
 * One review run over a session; the only record that carries timestamps.
 */
export interface ReviewRun {
  readonly check_results: CheckResult[];
  readonly created_at: string;
  readonly finished_at: string | null;
  readonly id: string;
  readonly input_manifest: InputManifest;
  readonly plan: ReviewPlan;
  readonly plan_source: 'llm' | 'default';
  readonly session_id: string;
  readonly status: 'queued' | 'running' | 'completed' | 'partial' | 'failed' | 'interrupted';
}
