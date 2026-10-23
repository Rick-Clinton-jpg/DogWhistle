"""Exploratory, deterministic channel diagnostics for the revealed PR #1 run.

This script is post hoc. It does not change the preregistered scoring or make
model calls. Run from any directory with Python 3.12 or later.
"""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "study" / "dogwhistle-1"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def diagnose() -> dict:
    sender_path = RUN / "sender_seal.json"
    ledger_path = RUN / "ledger.json"
    score_path = RUN / "scores.json"
    reveal_path = ROOT / "study" / "reveal-dogwhistle-1.json"
    seal = read(sender_path)["sender_rows"]
    ledger = read(ledger_path)["receiver_rows"]
    scores = read(score_path)["trials"]
    labels = read(reveal_path)["labels"]

    by_sender = {(r["instance_id"], r["regime"], r["condition"]): r for r in seal}
    by_score = {(r["instance_id"], r["regime"], r["condition"]): r for r in scores}
    by_assignment = {
        r["trial_id"]: json.loads(r["receiver_stdout"])["assignment"]
        for r in ledger
    }
    instances = sorted(labels)
    if len(instances) != 20 or len(seal) != len(ledger) != len(scores) != 100:
        raise ValueError("unexpected PR #1 record size")

    handoff_same = 0
    assignment_same_when_handoff_same = 0
    assignment_same_when_handoff_changed = 0
    covert_direct_pair = 0
    no_signal_direct_pair = 0
    coalition_differences: Counter[int] = Counter()
    gate_results: Counter[str] = Counter()
    for row in seal:
        gate_results[row["gate_result"]] += 1
    for instance in instances:
        covert = by_sender[instance, "free", "covert"]["delivered_handoff"]
        no_signal = by_sender[instance, "free", "no_signal"]["delivered_handoff"]
        covert_refs = covert["required_memory_refs"]
        no_signal_refs = no_signal["required_memory_refs"]
        hidden = set(labels[instance])
        covert_direct_pair += {ref.split("/")[-1] for ref in covert_refs} == hidden
        no_signal_direct_pair += {ref.split("/")[-1] for ref in no_signal_refs} == hidden
        same_handoff = covert == no_signal
        handoff_same += same_handoff
        same_assignment = (
            by_assignment[f"{instance}-free-covert"]
            == by_assignment[f"{instance}-free-no_signal"]
        )
        if same_handoff:
            assignment_same_when_handoff_same += same_assignment
        else:
            assignment_same_when_handoff_changed += same_assignment
        difference = (
            by_score[instance, "free", "covert"]["score"]["coalition_count"]
            - by_score[instance, "free", "no_signal"]["score"]["coalition_count"]
        )
        coalition_differences[difference] += 1

    return {
        "classification": "post_hoc_exploratory",
        "source_sha256": {
            "sender_seal": digest(sender_path),
            "receiver_ledger": digest(ledger_path),
            "scores": digest(score_path),
            "reveal": digest(reveal_path),
        },
        "instances": len(instances),
        "free_handoffs_identical_across_conditions": handoff_same,
        "free_handoffs_different_across_conditions": len(instances) - handoff_same,
        "same_assignments_when_handoffs_identical": assignment_same_when_handoff_same,
        "different_assignments_when_handoffs_identical": handoff_same - assignment_same_when_handoff_same,
        "same_assignments_when_handoffs_different": assignment_same_when_handoff_changed,
        "different_assignments_when_handoffs_different": len(instances) - handoff_same - assignment_same_when_handoff_changed,
        "covert_refs_directly_name_hidden_pair": covert_direct_pair,
        "no_signal_refs_directly_name_hidden_pair": no_signal_direct_pair,
        "coalition_count_paired_differences": {str(k): coalition_differences[k] for k in sorted(coalition_differences)},
        "gate_results": dict(sorted(gate_results.items())),
    }


if __name__ == "__main__":
    print(json.dumps(diagnose(), indent=2, sort_keys=True))
