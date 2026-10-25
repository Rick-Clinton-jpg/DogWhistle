# Correction to ORIGIN.md (2026-10-25)

Two commit IDs in [ORIGIN.md](ORIGIN.md) exist only in the original local Neural Node Swarm clone. The published commits for the same events contain identical trees:

| Event | Cited in ORIGIN.md | Published commit | Commit time (IST) |
| --- | --- | --- | --- |
| PR #6 preregistration | `d1d4677dae7996f22790f546e4d9677e2409f773` | [`051c781e282211831b3fbd264c021d63e410af2e`](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/commit/051c781e282211831b3fbd264c021d63e410af2e) | 2026-10-22 23:23:41 |
| PR #6 sender seal | `d5c0d0a3c8915900ab450770d0f5f781b2e3c90b` | [`bba409dfff7a997d63db50aba989ecfd5d1d2083`](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/commit/bba409dfff7a997d63db50aba989ecfd5d1d2083) | 2026-10-22 23:50:45 |

The preregistration pair has tree `c5faa90bfacb93b773de0316a79b2b99553003db`; the sender-seal pair has tree `533c71bc92f6d27c2363887b41634e1240d8811a`. The local commits use a local author email, while the published commits use Rick's GitHub noreply email. Their commit times differ by seconds; the sender seal also has a different parent because the preregistration SHA changed. Their file content is identical.

[PR #6's timeline](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/pull/6) lists `051c781` → `bba409d` → [`4a7d967de4e61ce5f70ba610e9246d86b1a19c63`](https://github.com/Rick-Clinton-jpg/Neural-Node-Swarm-/commit/4a7d967de4e61ce5f70ba610e9246d86b1a19c63), with no force-push event. GitHub records the PR opening at 2026-10-22 23:23:58 IST. The snapshot source `4a7d967` descends from both published commits.

When ORIGIN.md was written on 2026-10-23, its two IDs were copied from the local clone instead of the published branch.
