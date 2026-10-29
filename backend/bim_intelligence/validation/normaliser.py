"""Turn a validated IfcTester specification into deterministic ``Finding`` records (ADR-015 §3).

A Finding is emitted for exactly two verified conditions and nothing else:

* a requirement facet rejected an applicable entity — one finding per (facet, entity), carrying
  IfcTester's own reason as ``observed`` and the facet's rendered requirement as ``expected``;
* a prohibited specification matched an entity — one ``prohibited_entity`` finding per entity.

Zero applicability, schema mismatches and engine exceptions are ``CheckResult`` statuses in the
runner, never findings (C-05). No value is read from the model here; everything comes from the
state IfcTester left on the specification after ``validate()``.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from bim_intelligence.bim import ElementRefResolver
from bim_intelligence.schemas import CheckSpec, Finding, Severity, sort_findings

PROHIBITED_ENTITY_CATEGORY = "prohibited_entity"
_DEFAULT_SEVERITY: Severity = "error"


def normalise_specification(
    spec: Any, check: CheckSpec, requirement_id: str, resolve: ElementRefResolver
) -> list[Finding]:
    """Findings for a specification that IfcTester has validated; canonical order."""
    if spec.maxOccurs == 0:
        findings = _prohibited_findings(spec, check, requirement_id, resolve)
    else:
        findings = _requirement_findings(spec, check, requirement_id, resolve)
    return sort_findings(findings)


def facet_category(facet: Any) -> str:
    """``property_requirement``, ``classification_requirement``, ``partof_requirement`` …"""
    return f"{type(facet).__name__.lower()}_requirement"


def _requirement_findings(
    spec: Any, check: CheckSpec, requirement_id: str, resolve: ElementRefResolver
) -> Iterable[Finding]:
    for facet_index, facet in enumerate(spec.requirements):
        expected = str(facet.to_string("requirement", spec, facet))
        category = facet_category(facet)
        for failure in facet.failures:
            yield Finding(
                check_id=check.id,
                requirement_id=requirement_id,
                rule_id=check.rule_id,
                rule_version=check.rule_version,
                facet_index=facet_index,
                severity=_DEFAULT_SEVERITY,
                category=category,
                elements=[resolve(failure["element"])],
                observed=str(failure["reason"]),
                expected=expected,
                method="ids",
            )


def _prohibited_findings(
    spec: Any, check: CheckSpec, requirement_id: str, resolve: ElementRefResolver
) -> Iterable[Finding]:
    expected = "; ".join(
        str(facet.to_string("applicability", spec)) for facet in spec.applicability
    )
    for entity in spec.applicable_entities:
        ref = resolve(entity)
        label = f"{ref.ifc_type} {ref.name!r}" if ref.name else f"{ref.ifc_type} #{ref.express_id}"
        yield Finding(
            check_id=check.id,
            requirement_id=requirement_id,
            rule_id=check.rule_id,
            rule_version=check.rule_version,
            facet_index=0,
            severity=_DEFAULT_SEVERITY,
            category=PROHIBITED_ENTITY_CATEGORY,
            elements=[ref],
            observed=f"{label} matches the prohibited applicability",
            expected=expected,
            method="ids",
        )
