# HANDOVER B2 — close K1-DM-110 (continuation, five items)

**Project folder:** `/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-K1-DualMCU-Firmware`
**Branch:** continue on `lane/k1-dm-110-vectors-24k` (HEAD `1eda11d`).
**Read-only oracle:** `/Users/spectrasynq/SpectraSynq_K1_Firmware`. Never edit it.
**Agent:** Claude Code or Codex, one session.

---

The first K1-DM-110 session did the foundation correctly: legacy copy reproduces the frozen 12.8 kHz golden byte-for-byte, DUR-006 is filed, Emotiscope is pinned and not vendored, production stays 12 800 Hz / 96 behind delegating overloads. Five specific items remain. Do these and nothing else.

## 1. Unblock the Emotiscope oracle with a one-line, recorded scratch-copy fix

The `BLOCKED` diagnosis is right in substance and wrong in two details. Verified against the pinned source:

- `main/tempo.h:165` is `uint16_t index = ((NOVELTY_HISTORY_LENGTH - 1) - block_size) + i;`
- `init_num_tempi_float_lookup()` gives `progress = i/96`, so tempi are exactly 60–155 BPM in 1 BPM steps; neighbour distance is 1/60 Hz, so `block_size = 50 / (0.016667 × 0.5) = 6000`, clamped to 1024 by `tempo.h:94`. **Every** bin clamps to 1024, not just low bins.
- `index` is `uint16_t`, so at `i = 0` it is `(1023 − 1024) = −1` → **unsigned wraparound to 65535**, an out-of-bounds read ~256 kB past a 1024-float array, once per bin per call. It is not a negative index, and it is not confined to low bins.
- Consequence: the unmodified source can never run on a host. Waiting for it is waiting forever.

Apply, in the ignored `.cache/` copy only, exactly the allowance B1 already grants the legacy copy — the minimum change, listed with a one-line reason and recorded in the manifest:

```
uint16_t index = (NOVELTY_HISTORY_LENGTH - block_size) + i;   // was (NOVELTY_HISTORY_LENGTH - 1) - block_size
```

Record in the manifest and the README that this also fixes a second-order off-by-one: the original window excludes the newest novelty sample for every bin. Then emit the B3 goldens: 96 magnitudes, 96 phases, `tempo_confidence`, `silence_level` per novelty tick, with the manifest. Do not change anything else in the Emotiscope copy.

## 2. Use the legacy oracles that already exist for chroma, onset, tempo, chord

The report said the matrix is blocked because the legacy GDFT oracle does not supply those fields. That is true of `oracle_gdft.py` only. The legacy repo also has, with their own frozen goldens:

- `scripts/regression-harness/golden/oracle_tempo.py` (422 lines, references `SAMPLE_RATE`) → `tests/golden/tempo.golden.jsonl`
- `oracle_onset_beat.py` → `onset_beat.golden.jsonl`
- `oracle_chord.py` → `chord.golden.jsonl`

For each: prove the copy reproduces its frozen 12.8 kHz golden byte-for-byte first, then run it at 24 000 / 180 and emit `*_24k180.golden.jsonl` with a manifest. If one genuinely cannot take the rate substitution, say which token blocks it and stop on that one — do not stop on all three.

## 3. Make the 24 kHz check a differential, not a self-consistency test

`test/test_audio_rate_configuration/test_main.cpp` asserts that the port's own configuration derives sanely at 24 kHz (all 80 bins Nyquist-safe, no bin at the 2000 cap, novelty rate arithmetic). Nothing in it compares the port against `test/fixtures/gdft_24k180.golden.jsonl`. The K1-DM-110 acceptance item "the RT1062 host port matches the 24 000 Hz / 180 oracle within recorded numeric tolerances" is therefore untested.

Add that comparison: drive the port with the same input the oracle's driver uses, compare per bin per frame against the 24 kHz golden, and record a per-feature tolerance with a one-line numeric justification for each. Keep the existing configuration assertions — they are worth having, they are just not the differential.

Keep the two 80-bin facts in the evidence doc; they are the substantive result so far: at 24 kHz all 80 bins sit below Nyquist (at 12.8 kHz roughly nine are aliases) and no bin reaches the 2000-sample cap.

## 4. Gate the new work in the harness

`.claude/harness/init.sh` is unchanged, so none of the new evidence runs in the gate and its env list does not mention `native_audio_rate_24k`. Add, in the repo's existing style:

- `pio test -e native_audio_rate_24k` (the env uses `test_filter`, like `native_output_dither_truth`)
- `python3 scripts/check_k1_dm110_reproducibility.py`
- the Emotiscope generator, once item 1 makes it produce output

and add the env to the `HARNESS_INIT=PASS ENVS=…` list. A generator nothing calls is a regression nobody will see.

## 5. Fill the manifest provenance field

`test/fixtures/gdft_24k180.golden.manifest.json` has `"fixture_sha256": "analytic-440hz-silence-trace-in-driver"` — a label, not a hash. B4 requires the fixture SHA-256. Hash the actual driver input (or the driver source region that synthesises it) and record what was hashed. Do the same for every manifest added under item 2.

## Scope note

State plainly in the evidence doc what the 24 kHz vectors currently cover: 16 frames — four silent, twelve of a single 440 Hz tone at amplitude 16000 — from the legacy oracle's own built-in driver. That is one fixture, not the silence / impulse / sine / dual-tone / sweep matrix. If extending the driver's fixture set is more than a small change, say so and leave it; do not build a fixture framework.

## Constraints

- No hardware. Host only. Production stays 12 800 Hz / 96.
- Do not change existing golden files or contracts. Do not touch the legacy repo.
- No new guard macros, feature flags or timing scaffolding.
- British English.

## Stop report (repo format)

Files changed; commands run; validation output; the Emotiscope goldens' first-record summary; which of the three extra oracles took the 24 kHz substitution; the differential's tolerances and why; blockers; exact next step.
