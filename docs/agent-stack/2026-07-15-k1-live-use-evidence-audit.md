# K1 Live-Use Product And Agent-Stack Evidence Audit

## Verdict

[FACT] The K1 product work is accepted under its recorded test contracts: the
five audio-semantic flags passed the scoped IM73D device gate, mode 32 was
retained, and modes 35 and 36 were rejected after mechanically valid device
legs.

[FACT] This live-use arc does not qualify Entire, Headroom, Ruflo,
`sqlite-utils`, OpenKnowledge retrieval, Claude-mem retrieval, or the Codex
plugin.

[FACT] The durable repository does not prove that the recorded manual Codex CLI
review actually ran. Commits `49ea369` and `17e8a58` assert the command, elapsed
time, findings, and remediation, but the only named raw output was
`/tmp/codexrev/7b3bb99_adversarial.log`, which is absent.

[INFERENCE] The remediation in `49ea369` remains valuable and independently
auditable. What is rejected is the stronger attribution claim that this arc
proves Codex execution or Codex-plugin value.

## Claim Matrix

| Claim | Durable evidence | Verdict |
|---|---|---|
| The five-flag device gate closed | Measurement closeout, raw device artefacts, exact reruns, commit-state validation | VERIFIED under the documented six-track corpus and limitations |
| The 32/35/36 comparison closed | Three device-leg JSON/log pairs, clean runtime identity, Captain verdict | VERIFIED |
| The manual Codex CLI review ran | Commit messages assert it; raw `/tmp` log absent | NOT_VERIFIED |
| The Codex plugin was used | No preserved plugin invocation or handoff artefact | NOT_VERIFIED |
| Codex improved delivery | Fixes exist, but tool attribution and counterfactual are not proven | NOT_VERIFIED |
| Herdr improved process control | Workspace `w1` is recorded as pre-existing/note-only | NOT_VERIFIED |
| OpenKnowledge or Claude-mem affected a decision | No retrieval-to-decision trace attached to this arc | NOT_VERIFIED |
| Entire captured useful provenance | Not exercised in Sessions 2 or 3; separate pilot unpromoted | NOT_VERIFIED for this arc |
| Headroom preserved quality | Not exercised | NOT_VERIFIED |
| Ruflo improved orchestration | Not exercised | NOT_VERIFIED |
| `sqlite-utils` contributed | Not exercised | NOT_VERIFIED |

[FACT] The matrix concerns only this live-use arc. The historical Phase 1-6
pilot decisions remain governed by [`STANDARD-STACK.md`](./STANDARD-STACK.md).

## Commit-To-Evidence Chain

| Commit/state | Relationship and purpose | What it supports | What it does not support |
|---|---|---|---|
| `7b3bb99` | Initial Shockwave/Iris product slice | Host implementation of modes 35/36 and tombstoning of 30/33/34; device eyes-on explicitly pending | No device captivation verdict; no Codex evidence |
| `b02fc16` | Child of `7b3bb99`; initial live-deployment ledger row | Records the host-gate session state | No device proof; no preserved review output |
| `49ea369` | Child of `b02fc16`; review-remediation code | Five recorded fixes, one deferred `k1_custom` issue, independent Waveform endpoint fix, green host gates | Commit message alone does not prove the asserted Codex run |
| `17e8a58` | Child of `49ea369`; ledger closeout | Records the asserted review command/findings and host artefact hash | No raw Codex output; no device A/B |
| `52a21db` plus dirty source fingerprint `caacb24bf26a47cd63095a63bf91b23a8d6a0d2b21e2330f0ec7c7cdb001b818` | Descendant of `17e8a58`; embedded runtime Git identity during audio-semantic measurement | Runtime provenance anchor for the dirty-tree device corpus; harness hardening exists at this commit | Git SHA alone is not exact binary identity and does not describe the later clean source boundary |
| `7b3d6c0` | Descendant of `52a21db`; audio-semantic evidence consolidation | Five-flag gate implementation/evidence, paired novelty result, IM73D production-reference decision | Does not retroactively make the dirty runtime a clean-tree binary |
| `f2257ef` | Child of `7b3d6c0`; documentation-only validation boundary | Clean exact-commit focused tests/builds; clean source used for the later mode A/B | Does not replace the earlier dirty-tree measurement identity |
| `7ae81df` | Child of `f2257ef`; intervening WS2816 bench profile | Explains why the final A/B closeout is not the direct child of `f2257ef` | Not part of the 32/35/36 evidence claim |
| `8000b3b` | Child of `7ae81df`; final captivation evidence closeout | Raw build/upload/serial artefacts and Captain's 32 retain, 35/36 reject verdict | No optional agent-tool qualification |

[FACT] The effect implementation and native math files used for the A/B are
byte-identical between `49ea369` and `f2257ef`; `f2257ef` changes only the
audio-semantic closeout document relative to `7b3d6c0`.

## Exact Audit Commands

[FACT] Reproduce the commit metadata and parent chain:

```bash
for c in 7b3bb99 b02fc16 49ea369 17e8a58 52a21db 7b3d6c0 f2257ef 7ae81df 8000b3b; do
  git show -s --format='%H%nparents %P%nsubject %s%nbody %b%n---' "$c"
done

git merge-base --is-ancestor 7b3bb99 b02fc16
git merge-base --is-ancestor b02fc16 49ea369
git merge-base --is-ancestor 49ea369 17e8a58
git merge-base --is-ancestor 17e8a58 52a21db
git merge-base --is-ancestor 52a21db 7b3d6c0
git merge-base --is-ancestor 7b3d6c0 f2257ef
git merge-base --is-ancestor f2257ef 8000b3b
```

[FACT] Audit the Codex claim and the missing ephemeral output:

```bash
git show -s --format=fuller 49ea369 17e8a58
test -f /tmp/codexrev/7b3bb99_adversarial.log
```

[FACT] The second command exits `1` on the audited machine because the log is
absent. A future rerun of `codex exec review --commit 7b3bb99` would be new
evidence; it would not prove the historical invocation.

[FACT] Inspect the remediation and prove the A/B effect sources did not drift:

```bash
git diff --stat 7b3bb99 49ea369
git show --stat --oneline 49ea369
git diff --exit-code 49ea369 f2257ef -- \
  SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_shockwave.cpp \
  SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_iris.cpp \
  tests/native/test_shockwave_math.cpp \
  tests/native/test_iris_math.cpp
git diff 7b3d6c0 f2257ef -- \
  docs/measurements/2026-07-15-device-audio-semantic-gate-closeout.md
```

[FACT] Re-run product validation using the exact commands in:

- [`../measurements/2026-07-15-device-audio-semantic-gate-closeout.md`](../measurements/2026-07-15-device-audio-semantic-gate-closeout.md)
- [`../measurements/2026-07-15-captivation-32-35-36-verdict.md`](../measurements/2026-07-15-captivation-32-35-36-verdict.md)

## Correct Ledger Interpretation

[FACT] Product result: five-flag device gate closed under scoped evidence;
mode 32 retained; modes 35 and 36 rejected.

[FACT] Stack result: bootstrap and repository safety workflow were recorded as
part of delivery. No optional tool is qualified by this arc. The historical
Codex execution is `NOT_VERIFIED` from durable artefacts, and Codex-plugin use
is `NOT_VERIFIED`.

[FACT] Entire, Headroom, Ruflo, and `sqlite-utils` were not exercised in the
device A/B. OpenKnowledge and Claude-mem have no preserved retrieval-to-decision
trace for this arc.
