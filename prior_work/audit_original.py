"""Verify copied bytes, then run both audits at the original Git commit."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from verify_snapshot import main as verify_snapshot


HERE = Path(__file__).resolve().parent


def run(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, cwd=cwd, env=env, check=True)


def main() -> None:
    verify_snapshot()
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    with TemporaryDirectory(prefix="dogwhistle-nns-audit-") as temporary:
        source = Path(temporary) / "nns"
        run("git", "clone", "--quiet", manifest["source_repository"], str(source))
        run("git", "checkout", "--quiet", "--detach", manifest["source_commit"], cwd=source)
        env = {**os.environ, "PYTHONPATH": f"{source}:{source / 'src'}"}
        for module, trial, reveal in (
            ("covert_channel.experiment", "pilot-1", "reveal-pilot-1.json"),
            ("covert_channel.v2", "pr6-1", "reveal-pr6-1.json"),
        ):
            print(f"Auditing {trial} at {manifest['source_commit']}", flush=True)
            run(sys.executable, "-m", module, "audit", "--run-dir",
                f"covert_channel/{trial}", "--reveal", f"covert_channel/{reveal}",
                cwd=source, env=env)


if __name__ == "__main__":
    main()
