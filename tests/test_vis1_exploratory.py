"""Pinned checks for the post-reveal visibility decoy reanalysis."""

from __future__ import annotations

import shutil

import pytest

from analysis.vis1_exploratory import INPUT_SHA256, ROOT, analyze


def test_published_decoy_and_welfare_values():
    result = analyze()
    assert result["status"] == "exploratory, post-reveal"
    for arm, excess, regret in (
        ("public", 0.1093, 5.72),
        ("codeword", 0.0000, 4.13),
        ("explicit", 0.0037, 3.11),
    ):
        observed = result["arms"][arm]
        assert observed["n"] == 90
        assert observed["mean_decoy_excess"] == pytest.approx(excess, abs=0.00005)
        assert observed["mean_welfare_regret"] == pytest.approx(regret, abs=0.005)


def test_input_digest_is_checked_before_parsing(tmp_path):
    for name in INPUT_SHA256:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    (tmp_path / "visibility/vis-1/ledger.json").write_text("not JSON", encoding="utf-8")
    with pytest.raises(ValueError, match="published input SHA-256 mismatch"):
        analyze(tmp_path)
