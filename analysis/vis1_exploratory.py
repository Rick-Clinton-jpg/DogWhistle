"""Post-reveal decoy analysis of the immutable, published visibility run.

Run from the repository root with ``python3.12 -m analysis.vis1_exploratory``.
No private run files or model clients are used.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from dogwhistle.allocation import VENDORS, score
from dogwhistle.gate import public_refs


ROOT = Path(__file__).resolve().parents[1]
INPUT_SHA256 = {
    "visibility/registration.json": "f97cb1ee39fa47c4460aa52f8634942a4f01649753f4a1cb48761d5863007fd2",
    "visibility/reveal-vis-1.json": "80f55bd7228637a5522205a0511c72e213105826921fd97358fcb9d054585ea9",
    "visibility/vis-1/ledger.json": "c92429e9e883aa7f066bf6692240196e963324d2b264fde221b1c2b2dc47b787",
    "visibility/vis-1/scores.json": "0cf501749d50b6332999cfef2fe21bdd152adbdd2772747c48f44b71b81b0c0c",
}
ARMS = ("public", "codeword", "explicit")


def analyze(root: Path = ROOT) -> dict[str, Any]:
    """Verify published bytes, then independently score the public-ref decoy."""
    raw = {}
    for name, expected in INPUT_SHA256.items():
        data = (root / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"published input SHA-256 mismatch: {name}")
        raw[name] = data

    registration = json.loads(raw["visibility/registration.json"])
    reveal = json.loads(raw["visibility/reveal-vis-1.json"])
    ledger = json.loads(raw["visibility/vis-1/ledger.json"])
    published_scores = json.loads(raw["visibility/vis-1/scores.json"])
    tasks = {task["instance_id"]: task for task in registration["instances"]}
    trials = registration["trials"]
    rows = ledger["receiver_rows"]
    scored = published_scores["trials"]
    if len(tasks) != 30 or len(trials) != 270 or len(rows) != 270 or len(scored) != 270:
        raise ValueError("published trial count differs from registration")

    values: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    decoys = {}
    for task_id, task in tasks.items():
        named = {ref.split("/", 1)[1] for ref in public_refs(task)}
        decoy = tuple(vendor for vendor in VENDORS if vendor not in named)
        if len(decoy) != 2 or decoy == tuple(reveal["labels"][task_id]):
            raise ValueError(f"public-ref decoy collides with target: {task_id}")
        decoys[task_id] = decoy

    for trial, row, published in zip(trials, rows, scored, strict=True):
        if trial["trial_id"] != row["trial_id"] or trial["trial_id"] != published["trial_id"]:
            raise ValueError("published trial order mismatch")
        arm = trial["arm"]
        task = tasks[trial["instance_id"]]
        if row["receiver_input"]["task"] != task:
            raise ValueError("published task differs from registration")
        try:
            assignment = json.loads(row["receiver_stdout"]).get("assignment")
        except (json.JSONDecodeError, AttributeError, TypeError):
            assignment = None
        result = score(task["matrix"], decoys[trial["instance_id"]], assignment)
        if result["welfare_regret"] != published["score"]["welfare_regret"]:
            raise ValueError("welfare regret differs from published score")
        values[arm].append(result)

    if any(len(values[arm]) != 90 for arm in ARMS):
        raise ValueError("published arm counts differ from registration")
    return {
        "status": "exploratory, post-reveal",
        "input_sha256": INPUT_SHA256,
        "arms": {
            arm: {
                "n": len(values[arm]),
                "mean_decoy_excess": sum(item["coalition_excess_over_optimum"]
                                         for item in values[arm]) / len(values[arm]),
                "mean_welfare_regret": sum(item["welfare_regret"]
                                           for item in values[arm]) / len(values[arm]),
            }
            for arm in ARMS
        },
    }


if __name__ == "__main__":
    print(json.dumps(analyze(), sort_keys=True, indent=2))
