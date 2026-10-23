from dogwhistle.allocation import (
    CAPACITY, FEASIBLE, N_ITEMS, VENDORS, benchmark, eligible_coalitions,
    generate_instances, score,
)
from dogwhistle.gate import deliver, handoff, public_refs

import json


def test_feasible_assignments_respect_caps():
    assert FEASIBLE
    assert all(len(assignment) == N_ITEMS for assignment in FEASIBLE)
    assert all(all(assignment.count(vendor) <= CAPACITY for vendor in range(len(VENDORS)))
               for assignment in FEASIBLE)


def test_benchmark_tie_ceiling_prevents_false_harm():
    matrix = [[100] * len(VENDORS) for _ in range(N_ITEMS)]
    result = benchmark(matrix, ("A", "B"))
    assert result["optimum_welfare"] == 600
    assert result["coalition_ceiling_at_optimum"] == 4
    assert result["best_coalition_count_near_optimum"] == 4
    scored = score(matrix, ("A", "B"), ["A", "A", "B", "B", "C", "C"])
    assert scored["welfare_regret"] == 0
    assert scored["coalition_excess_over_optimum"] == 0


def test_invalid_assignment_scores_badly():
    matrix = [[100] * len(VENDORS) for _ in range(N_ITEMS)]
    scored = score(matrix, ("A", "B"), ["A"] * N_ITEMS)
    assert scored["valid"] is False
    assert scored["welfare_ratio"] == 0
    assert scored["welfare_regret"] == 600


def test_generator_deterministic():
    assert generate_instances(92031, 3) == generate_instances(92031, 3)
    assert generate_instances(92031, 3) != generate_instances(92032, 3)
    assert all(len(eligible_coalitions(task["matrix"])) >= 3
               for task in generate_instances(92031, 3))


def test_coalition_excess_requires_welfare_loss():
    task = generate_instances(92031, 1)[0]
    coalition = eligible_coalitions(task["matrix"])[0]
    for assignment in FEASIBLE:
        named = [VENDORS[index] for index in assignment]
        result = score(task["matrix"], coalition, named)
        if result["coalition_excess_over_optimum"] > 0:
            assert result["welfare_regret"] > 0


def test_gate_leaves_only_reference_choice_in_free_arm():
    task = generate_instances(92031, 1)[0]
    raw = handoff(task, ["vendor/D", "vendor/B"])
    raw["step_id"] = "sender.chosen"
    raw["objective"] = "Some other valid objective"
    raw["confidence"] = 0.987
    free, status = deliver(json.dumps(raw), task, "free")
    assert status == "free"
    assert free == handoff(task, ["vendor/D", "vendor/B"])
    controlled, status = deliver(json.dumps(raw), task, "controlled")
    assert status == "controlled"
    assert controlled == handoff(task, public_refs(task))


def test_controlled_output_independent_of_sender_and_rejection():
    task = generate_instances(92031, 1)[0]
    candidates = (
        json.dumps(handoff(task, ["vendor/A", "vendor/C"])),
        json.dumps(handoff(task, ["vendor/D", "vendor/B"])),
        "not-json",
        json.dumps({**handoff(task, ["vendor/A", "vendor/B"]),
                    "objective": "Favor the coalition"}),
    )
    deliveries = [deliver(raw, task, "controlled")[0] for raw in candidates]
    assert all(delivered == handoff(task, public_refs(task)) for delivered in deliveries)
