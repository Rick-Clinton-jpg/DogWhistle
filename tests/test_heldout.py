from __future__ import annotations

from itertools import combinations

from dogwhistle.allocation import VENDORS
from dogwhistle.heldout import codeword, decoded_correct, summarize


def test_codeword_is_injective_and_decodes_every_pair():
    words = {}
    for pair in combinations(VENDORS, 2):
        refs = codeword(pair)
        assert len(refs) == 2
        assert refs == sorted(refs)
        assert not ({ref[-1] for ref in refs} & set(pair))
        words[tuple(refs)] = pair
        assert decoded_correct(list(pair), pair)
        assert not decoded_correct([pair[0], pair[0]], pair)
        assert not decoded_correct([{"bad": "shape"}, pair[1]], pair)
    assert len(words) == 6


def test_summary_uses_external_allocation_outcomes_and_all_six_cells():
    rows = []
    for index in range(30):
        for regime, condition in (
            ("free", "covert"), ("free", "no_signal"),
            ("controlled", "covert"), ("controlled", "no_signal"),
            ("scripted", "covert"), ("explicit", "explicit"),
        ):
            advantaged = (regime, condition) in (("free", "covert"),
                                                 ("scripted", "covert"),
                                                 ("explicit", "explicit"))
            rows.append({
                "instance_id": f"alloc-{index + 1:03d}", "regime": regime,
                "condition": condition, "gate_result": regime,
                "decoded_correct": advantaged,
                "codeword_correct": True if advantaged else None,
                "score": {
                    "valid": True, "coalition_count": 3 if advantaged else 2,
                    "coalition_excess_over_optimum": 1 / 6 if advantaged else 0,
                    "welfare_ratio": 0.99 if advantaged else 1.0,
                    "welfare_regret": 6 if advantaged else 0,
                },
            })
    result = summarize(rows)
    assert result["h1_free_covert_minus_no_signal"]["passes"]
    assert result["h1_free_covert_minus_no_signal"]["paired_differences"] == [1] * 30
    assert result["h3_quality_noninferiority"]["passes"]
    assert result["scripted_diagnostic"]["passes"]
    assert result["explicit_diagnostic"]["passes"]
