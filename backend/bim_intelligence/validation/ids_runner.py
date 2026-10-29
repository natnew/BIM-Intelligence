"""Execute one confirmed IDS check against an open model (FR-VAL-01, ADR-015 §4, ADR-018).

``run_ids_check`` is the whole contract between the orchestrator and IfcTester:

* the check is re-hydrated from its own payload (never from the uploaded document), so what runs
  is exactly what was confirmed;
* it runs inside a single-specification ``Ids`` through ``Ids.validate``, IfcTester's public
  entry point, which also resets its per-run property caches;
* every outcome is a typed ``CheckResult`` — ``passed``, ``failed`` (with findings), ``error``
  (engine exception or corrupted check, with diagnostics), ``skipped`` (the specification does
  not declare the model's schema) or ``not_applicable`` (nothing matched the applicability);
* the model is opened read-only by the caller and is never written (C-04).

A Finding is only ever produced by the normaliser from state IfcTester set (ADR-001).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import ifcopenshell
import ifctester.ids

from bim_intelligence.bim import ModelIndex, element_ref_resolver, open_ifc
from bim_intelligence.schemas import CheckResult, CheckSpec, CheckStatus, Finding
from bim_intelligence.validation.errors import CheckSpecIntegrityError
from bim_intelligence.validation.ids_compiler import hydrate_specification
from bim_intelligence.validation.normaliser import normalise_specification

logger = logging.getLogger(__name__)

_RUN_TITLE = "BIM Intelligence check run"


@dataclass(frozen=True)
class CheckOutcome:
    """What one check produced: its execution record and the findings it verified."""

    result: CheckResult
    findings: tuple[Finding, ...] = ()


class ValidationTarget:
    """One model version opened read-only, with its index, ready to run checks against.

    The orchestrator works with this object only, so no IfcOpenShell type crosses the
    ``validation/`` boundary (AGENTS.md §3). ``close()`` drops the file handle; on Windows that
    must happen before the version directory could be renamed or removed.
    """

    def __init__(self, model: ifcopenshell.file, index: ModelIndex | None) -> None:
        self._model: ifcopenshell.file | None = model
        self._index = index

    @classmethod
    def open(cls, path: Path, index: ModelIndex | None) -> ValidationTarget:
        """Open ``path`` through the loader (schema check, no writes) and bind ``index``."""
        return cls(open_ifc(path), index)

    @property
    def schema(self) -> str:
        return str(self._require_model().schema_identifier)

    def run(self, check: CheckSpec, *, requirement_id: str) -> CheckOutcome:
        if check.kind == "native":
            from bim_intelligence.validation.native_rules import run_native_check

            return run_native_check(self._index, check, requirement_id=requirement_id)
        return run_ids_check(
            self._require_model(), self._index, check, requirement_id=requirement_id
        )

    def close(self) -> None:
        self._model = None

    def __enter__(self) -> ValidationTarget:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _require_model(self) -> ifcopenshell.file:
        if self._model is None:
            raise RuntimeError("The validation target has been closed.")
        return self._model


def run_ids_check(
    model: ifcopenshell.file, index: ModelIndex | None, check: CheckSpec, *, requirement_id: str
) -> CheckOutcome:
    """Validate ``model`` against ``check``; never raises for a per-check failure."""
    try:
        spec = hydrate_specification(check)
    except CheckSpecIntegrityError as exc:
        return _error(check, requirement_id, [str(exc)])

    schema = str(model.schema_identifier)
    declared: Sequence[str] = list(spec.ifcVersion or [])
    if declared and schema not in declared:
        return _outcome(
            check,
            requirement_id,
            "skipped",
            diagnostics=[
                f"Specification applies to {', '.join(declared)}; the model is {schema}. "
                "The check was not executed."
            ],
        )

    try:
        single = ifctester.ids.Ids(title=_RUN_TITLE)
        single.specifications.append(spec)
        single.validate(model)
        findings = normalise_specification(spec, check, requirement_id, element_ref_resolver(index))
    except Exception as exc:
        logger.warning("check %s raised in ifctester: %s", check.id, exc, exc_info=exc)
        return _error(check, requirement_id, [f"{type(exc).__name__}: {exc}"])

    applicable = len(spec.applicable_entities)
    if findings:
        return _outcome(
            check, requirement_id, "failed", applicable=applicable, findings=tuple(findings)
        )
    if applicable == 0:
        if spec.maxOccurs == 0:
            # A prohibition that nothing violates is satisfied.
            return _outcome(check, requirement_id, "passed")
        return _outcome(
            check,
            requirement_id,
            "not_applicable",
            diagnostics=["No entities matched the specification's applicability."],
        )
    return _outcome(check, requirement_id, "passed", applicable=applicable)


def _outcome(
    check: CheckSpec,
    requirement_id: str,
    status: CheckStatus,
    *,
    applicable: int = 0,
    findings: tuple[Finding, ...] = (),
    diagnostics: Sequence[str] = (),
) -> CheckOutcome:
    result = CheckResult(
        check_id=check.id,
        requirement_id=requirement_id,
        status=status,
        applicable_count=applicable,
        finding_ids=[finding.id for finding in findings],
        diagnostics=list(diagnostics),
    )
    return CheckOutcome(result=result, findings=findings)


def _error(check: CheckSpec, requirement_id: str, diagnostics: list[str]) -> CheckOutcome:
    return _outcome(check, requirement_id, "error", diagnostics=diagnostics)
