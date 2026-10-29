"""Registered deterministic rules that IDS 1.0 cannot express (FR-VAL-04, ADR-015)."""

from __future__ import annotations

from collections.abc import Sequence

from bim_intelligence.bim import ModelIndex
from bim_intelligence.schemas import CheckResult, CheckSpec, ClassificationRef, Finding
from bim_intelligence.validation.ids_runner import CheckOutcome

CLASSIFICATION_CONSISTENCY_RULE_ID = "classification.consistent_by_type"
CLASSIFICATION_CONSISTENCY_RULE_VERSION = "1.0.0"
CLASSIFICATION_CONSISTENCY_TITLE = "Classification is consistent by type"
CLASSIFICATION_CONSISTENCY_STATEMENT = (
    "Each occurrence of a classified type uses the same effective classification references "
    "as that type."
)


def classification_consistency_check() -> CheckSpec:
    """Return the immutable, parameter-free CheckSpec for the registered P0 rule."""
    return CheckSpec(
        kind="native",
        rule_id=CLASSIFICATION_CONSISTENCY_RULE_ID,
        rule_version=CLASSIFICATION_CONSISTENCY_RULE_VERSION,
        params={},
    )


def run_native_check(
    index: ModelIndex | None, check: CheckSpec, *, requirement_id: str
) -> CheckOutcome:
    """Run a registered native check; invalid or unsupported specs are execution errors."""
    diagnostic: str | None = None
    if check.kind != "native":
        diagnostic = f"Expected a native CheckSpec; received kind {check.kind!r}."
    elif check.rule_id != CLASSIFICATION_CONSISTENCY_RULE_ID:
        diagnostic = f"Unregistered native rule {check.rule_id!r}."
    elif check.rule_version != CLASSIFICATION_CONSISTENCY_RULE_VERSION:
        diagnostic = (
            f"Unsupported version {check.rule_version!r} for {check.rule_id!r}; "
            f"expected {CLASSIFICATION_CONSISTENCY_RULE_VERSION!r}."
        )
    elif check.params:
        diagnostic = (
            f"{CLASSIFICATION_CONSISTENCY_RULE_ID!r} accepts no parameters; "
            "the confirmed CheckSpec must contain an empty params object."
        )
    elif index is None:
        diagnostic = "The Model Index for the pinned model version is unavailable."

    if diagnostic is not None:
        return CheckOutcome(
            result=CheckResult(
                check_id=check.id,
                requirement_id=requirement_id,
                status="error",
                applicable_count=0,
                diagnostics=[diagnostic],
            )
        )

    assert index is not None
    findings: list[Finding] = []
    applicable_count = 0
    for element in index.elements:
        if element.type_ref is None:
            continue
        type_record = index.by_express_id(element.type_ref.express_id)
        expected = _classification_values(type_record.classifications)
        if not expected:
            continue

        applicable_count += 1
        observed = _classification_values(element.classifications)
        if observed == expected:
            continue

        findings.append(
            Finding(
                check_id=check.id,
                requirement_id=requirement_id,
                rule_id=check.rule_id,
                rule_version=check.rule_version,
                facet_index=0,
                severity="error",
                category="classification_inconsistent",
                elements=[element.ref],
                observed=(
                    f"{_element_name(element.ref.name, element.ref.ifc_type)} uses "
                    f"{_format_classifications(observed)}."
                ),
                expected=(
                    f"Type {_element_name(type_record.ref.name, type_record.ref.ifc_type)} "
                    f"uses {_format_classifications(expected)}."
                ),
                method="native",
            )
        )

    if findings:
        status = "failed"
        diagnostics: Sequence[str] = ()
    elif applicable_count == 0:
        status = "not_applicable"
        diagnostics = ("No occurrence has a type with a classification reference.",)
    else:
        status = "passed"
        diagnostics = ()

    return CheckOutcome(
        result=CheckResult(
            check_id=check.id,
            requirement_id=requirement_id,
            status=status,
            applicable_count=applicable_count,
            finding_ids=[finding.id for finding in findings],
            diagnostics=list(diagnostics),
        ),
        findings=tuple(findings),
    )


def _classification_values(
    classifications: Sequence[ClassificationRef],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            {
                (
                    classification.system or "",
                    classification.identification or classification.name or "",
                )
                for classification in classifications
            }
        )
    )


def _format_classifications(values: Sequence[tuple[str, str]]) -> str:
    if not values:
        return "no classification references"
    return "; ".join(
        f"{system or 'Unknown system'}: {identification or 'unidentified'}"
        for system, identification in values
    )


def _element_name(name: str | None, ifc_type: str) -> str:
    return repr(name) if name else ifc_type
