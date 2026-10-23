"""Check the exact bytes of the imported Neural Node Swarm files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / "nns_snapshot"
MANIFEST = HERE / "manifest.json"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = manifest["files"]
    actual_paths = {
        str(path.relative_to(SNAPSHOT))
        for path in SNAPSHOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    if actual_paths != set(expected):
        raise SystemExit(f"file set differs: missing={set(expected)-actual_paths}, extra={actual_paths-set(expected)}")
    for relative, digest in expected.items():
        actual = hashlib.sha256((SNAPSHOT / relative).read_bytes()).hexdigest()
        if actual != digest:
            raise SystemExit(f"SHA-256 mismatch: {relative}")
    print(f"Verified {len(expected)} imported files against manifest.json")


if __name__ == "__main__":
    main()
