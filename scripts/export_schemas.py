"""Export the Pydantic contract models as one JSON Schema document for the frontend (ADR-014).

    python scripts/export_schemas.py           # write frontend/src/api/generated/*.schema.json
    python scripts/export_schemas.py --check   # exit 1 if the committed file is stale

The TypeScript types are then produced from that file by ``npm run types:generate`` in
``frontend/``; ``npm run types:check`` detects drift on the Node side. The two stages are
independent so the frontend builds without Python and the backend tests without Node.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from bim_intelligence.schemas import contract_schema_json  # noqa: E402

OUTPUT_PATH = REPO_ROOT / "frontend" / "src" / "api" / "generated" / "bim_intelligence.schema.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="Compare with the committed file instead of writing."
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args(argv)

    rendered = contract_schema_json()
    relative = (
        args.output.relative_to(REPO_ROOT) if args.output.is_relative_to(REPO_ROOT) else args.output
    )

    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else None
        if current == rendered:
            print(f"{relative}: up to date")
            return 0
        print(f"{relative}: stale - run `python scripts/export_schemas.py`", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"wrote {relative} ({len(rendered)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
