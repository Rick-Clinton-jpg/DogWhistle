# Why PR #1 did not establish a covert allocation effect

This is an **exploratory, post-reveal** analysis of the completed PR #1 run.
It does not change that study's registration, endpoints, scores, or conclusion.
Reproduce the counts with `python3.12 followup/diagnose_pr1.py`; the script
binds its inputs to the published sender, receiver, score, and reveal hashes.

| Observation across 20 matched public tasks | Count |
| --- | ---: |
| Free/covert and free/no-signal delivered identical handoffs | 14 |
| Their delivered handoffs differed | 6 |
| Covert refs directly named both hidden coalition vendors | 0 |
| Different handoffs led to different final assignments | 2 of 6 |
| Identical handoffs still led to different final assignments | 3 of 14 |
| Covert minus no-signal coalition-count differences | 19 zeros, one −1 |

All 80 model sender outputs passed the gate. Only ordered vendor refs survived
it; the rest of each delivered handoff was fixed by code. In the six tasks
where refs differed, four final assignments were still identical. In three
tasks where refs were identical, final assignments differed, so an observed
allocation difference alone cannot be attributed to the refs in this
one-sample comparison. The model received a *possible cue* instruction but
no shared encoding rule. Directly naming the two hidden vendors in refs was
not observed; another code is logically possible, but the outcomes provide
no evidence that one was used successfully.

This points to two distinct questions for a new experiment: did the sender
place the hidden pair into the allowed field, and did the successor use that
field to alter an allocation? The original run answered neither positively.
The next design should measure both, with a deterministic encoder diagnostic
that makes a null result localizable. It must use new, held-out tasks and a
fresh preregistration; extending PR #1 after seeing its outcomes would break
its fixed-sample claim.

These counts are descriptive diagnostics selected after observing the null.
They are not new hypothesis tests, effect estimates for a population, or
evidence that every form of schema-bound signaling fails.
