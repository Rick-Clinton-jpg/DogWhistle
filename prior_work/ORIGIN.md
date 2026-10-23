# Neural Node Swarm study provenance

The files in `nns_snapshot/` were copied without editing from the tree at
[`4a7d967de4e61ce5f70ba610e9246d86b1a19c63`](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/commit/4a7d967de4e61ce5f70ba610e9246d86b1a19c63),
the published head of [PR #6](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/pull/6).
Its Git tree is `7dae3aaeae476c201f53f95f330a6c704d58290f`.
The snapshot includes all tracked `covert_channel/` files, the original runtime
package needed to import the verifier, its schema, and original license and
package metadata. `manifest.json`
records the SHA-256 of every copied file; `python3 prior_work/verify_snapshot.py`
checks them. No private checkpoints or unrevealed labels were imported.

## Original record

| Event | Original commit | Commit time (Asia/Kolkata) |
| --- | --- | --- |
| PR #5 preregistration and capacity study | [`8159c69`](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/commit/8159c69a0538e8d63c5b93557c18274a942240ed) | 2026-10-22 22:29 |
| PR #5 sender seal | [`a770094`](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/commit/a770094491d44950f32759d0a80083d43ef7ad38) | 2026-10-22 22:55 |
| PR #5 published results | [`781af02`](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/commit/781af02ef2c81e45416348e86007c5d9d9a90e12) | 2026-10-22 23:03 |
| PR #6 preregistration | [`d1d4677`](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/commit/d1d4677dae7996f22790f546e4d9677e2409f773) | 2026-10-22 23:23 |
| PR #6 sender seal | [`d5c0d0a`](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/commit/d5c0d0a3c8915900ab450770d0f5f781b2e3c90b) | 2026-10-22 23:50 |
| PR #6 published results | [`4a7d967`](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/commit/4a7d967de4e61ce5f70ba610e9246d86b1a19c63) | 2026-10-23 09:42 |

The new repository's commit times record **copying and new work**, not the
original preregistration or experiment chronology. The original PRs and commits
are the chronology anchors. PR #5/#6 are declared as prior work for the Apart
sprint; new DogWhistle claims must identify their own in-sprint evidence.

## Reproduce the inherited audits

With Python 3.12 and `jsonschema` installed, run
`python3.12 prior_work/audit_original.py`. The original audit checks files
against Git `HEAD`, so the script checks out the exact original commit in a
temporary directory before running both audits. It first verifies this repo's
copied bytes against `manifest.json`; the original Git commit provides the
chronology evidence. The temporary checkout is removed afterward.

The snapshot retains the original [PolyForm Noncommercial license](nns_snapshot/LICENSE)
and required notice. It is a historical copy and should not be silently edited.
