"""Exceptions raised by the ``bim`` package. Messages never contain file-system paths."""

from __future__ import annotations


class IfcLoadError(Exception):
    """IfcOpenShell could not open or parse the uploaded bytes (ARCHITECTURE §14: 422)."""


class UnsupportedSchemaError(IfcLoadError):
    """The file declares an IFC schema this build does not index."""

    def __init__(self, schema: str, supported: frozenset[str]) -> None:
        super().__init__(
            f"Unsupported IFC schema {schema!r}; supported schemas are {sorted(supported)}."
        )
        self.schema = schema


class UnsupportedUploadError(Exception):
    """The upload's declared filename does not carry an allowed extension (415)."""

    def __init__(self, filename: str | None, allowed: frozenset[str]) -> None:
        shown = filename if filename is not None else "<no filename>"
        super().__init__(
            f"{shown!r} is not an accepted model file; allowed extensions: {sorted(allowed)}."
        )
        self.filename = filename


class InvalidGlobalIdError(ValueError):
    """The supplied identifier is not a 22-character IFC GlobalId."""

    def __init__(self, global_id: str) -> None:
        super().__init__(f"Invalid GlobalId {global_id!r}: expected 22 base-64 IFC characters.")
        self.global_id = global_id


class UnknownElementError(LookupError):
    """No indexed element has this identity."""

    def __init__(self, identity: str) -> None:
        super().__init__(f"No element {identity} in the indexed model.")
        self.identity = identity


class AmbiguousGlobalIdError(LookupError):
    """More than one indexed element carries this GlobalId (FR-VAL-06)."""

    def __init__(self, global_id: str, express_ids: list[int]) -> None:
        super().__init__(
            f"GlobalId {global_id} is shared by {len(express_ids)} elements "
            f"(express ids {express_ids}); look them up by express id instead."
        )
        self.global_id = global_id
        self.express_ids = express_ids
