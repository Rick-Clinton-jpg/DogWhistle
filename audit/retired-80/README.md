# Retired PR #5: unchanged partial record

This is the complete partial record from the retired `listener-audit-1.0` run. The run stopped after 80 of 360 registered Codex receiver calls. No Qwen calls were made. The study was retired, without viewing or scoring an answer, for the reasons fixed in [`retired-partial.json`](../seals/retired-partial.json). The replacement study in [PR #6](https://github.com/Rick-Clinton-jpg/DogWhistle/pull/6) was revealed before this archive was decrypted. This record makes **no confirmatory decision** about PR #5's primary or secondary hypotheses.

## Record and verification

The four encrypted archive files matched every byte count and SHA-256 in the retirement seal at commit `069be1a71146fcb6d5d86c89880edb69a2935d94`. The recovered labels and all 360 inputs passed the frozen `validate_registration` checks, including their public commitments, generated matrices, trial schedule, and handoff schema. The 80 checkpoint rows matched the first 80 registered trial IDs and committed inputs in order. The 80 attempts matched those rows in order, each succeeding on its first invocation. The four published JSON files are the exact decrypted bytes; no row, answer, label, or attempt was rewritten.

| Published file | Bytes | SHA-256 of exact plaintext |
| --- | ---: | --- |
| [`labels.json`](labels.json) | 750 | `7f94c8a059a0c2f85949ede70bba851d4ba732bc1fa9f11f2f63a0aebdeae8f7` |
| [`inputs.json`](inputs.json) | 218,893 | `0e80e46bba61e5c40fc244e6041ec910bd36034f481ea4ca37e470e9deeee66f` |
| [`checkpoint.json`](checkpoint.json) | 56,283 | `e047d674c460731ce969cf50ac8c2c29cde1e63439b8673bef6ae09d3cde2345` |
| [`attempts.json`](attempts.json) | 154,373 | `ec6faec089757520d2d8f2dda32cfeda0082824a76b64de791028f7d92b0fba1` |

The original PR #5 helper read the encryption passphrase from the macOS Keychain on the run machine. Label isolation for these 80 calls is **not claimed as enforced**. For this promised publication, the owner authorized a one-time direct read of that same Keychain item. The publication helper held the passphrase in memory and passed it to OpenSSL through a file descriptor; it did not put the passphrase in a command argument, environment variable, repository file, or report.

## Descriptive observations only

The 80 calls ran from 2026-10-24 15:32:17 to 15:49:35 UTC. They covered 28 of the 30 matrices; none had all 12 registered slots. There were 80 successful process invocations, no process errors, no retries, and 80 valid assignments. The matrix slot-count distribution was: five matrices with one answer, seven with two, seven with three, five with four, and four with five.

| Listener / arm | Answers | Valid | Mean hidden-pair assignments | Mean welfare ratio | Mean welfare regret |
| --- | ---: | ---: | ---: | ---: | ---: |
| Coalition / codeword | 20 | 20 | 3.5500 | 0.9904 | 6.4000 |
| Coalition / public refs | 16 | 16 | 2.8125 | 0.9835 | 11.0625 |
| Honest / codeword | 19 | 19 | 2.5789 | 1.0000 | 0 |
| Honest / public refs | 25 | 25 | 2.5600 | 1.0000 | 0 |

Only four coalition and six honest slots had both arms answered for the same matrix and paraphrase. Their descriptive mean codeword-minus-public hidden-pair differences were +1.25 and 0, respectively. These are sparse, incomplete, order-prefix observations. The unbalanced cell counts and lack of complete matrices prevent the registered matrix-level analysis. No p-value, confidence interval, equivalence claim, or pass/fail decision is assigned to this partial record.
