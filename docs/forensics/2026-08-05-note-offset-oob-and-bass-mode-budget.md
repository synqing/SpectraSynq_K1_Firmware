---
abstract: "Two verified defects found 2026-08-05 while costing the AP Goertzel bank, both independent of that lane. (1) SHIPPING OOB READ: serial `:note_offset` clamps to 0..32 but notes[] has 96 entries and system.h indexes notes[n+NOTE_OFFSET] for n<=79, so offsets 17..32 read past the end and corrupt every Goertzel coefficient. One-line fix: constrain to 0..16. (2) PROJECTED BUDGET OVERRUN: CHROMA_PROFILE_BASS and _FULL both set NOTE_OFFSET=0, doubling every block_size (17,222 -> 34,484 iters), putting process_GDFT alone at ~6,380us of a 7,500us frame (~85%). Not device-verified."
status: open
severity: "(1) memory-safety, shipping, serial-reachable · (2) performance, shipping, projected"
---

# `note_offset` out-of-bounds read + bass-mode frame budget

Found 2026-08-05 while building the per-bin Goertzel cost model for the AP
architecture lane. **Neither defect has anything to do with that lane** — both
are pre-existing and independently actionable.

## Defect 1 — out-of-bounds read reachable from the serial surface

**Severity: memory safety. Ships today. Reachable by one serial command.**

| | |
|---|---|
| Writer | `serial/serial_cmd_handlers.cpp:600` — `CONFIG.NOTE_OFFSET = constrain(atol(command_data), 0, 32);` |
| Reader | `system/system.h:245` — `frequencies[i].target_freq = notes[n + CONFIG.NOTE_OFFSET];` with `int16_t n = i;` over `i < NUM_FREQS` (80), plus the neighbour reads at `notes[n + NOTE_OFFSET ± 1]` |
| Array | `system/constants.h` — `notes[]` has **96** entries |

Highest index touched is `79 + NOTE_OFFSET`, so the access is in-bounds only for
`NOTE_OFFSET <= 16`. The setter permits up to **32**, so
`:note_offset=17` … `:note_offset=32` read up to **16 elements past the end** of
`notes[]`.

This is not a benign over-read. The garbage values become `target_freq`, which
feeds `max_distance_hz` and therefore `block_size = SAMPLE_RATE /
(max_distance_hz * 2.0)` (`system.h:271`) for **every** bin — so a single
out-of-range command corrupts the whole Goertzel coefficient table. A near-zero
or negative `max_distance_hz` also drives `block_size` into the 2000 clamp
(`system.h:273-275`) or produces a non-finite value.

The value is **persisted** (`save_config()` on the same path), so a bad offset
survives reboot.

### Fix

```c
// serial/serial_cmd_handlers.cpp:600
CONFIG.NOTE_OFFSET = constrain(atol(command_data), 0, 16);
```

`16` is not arbitrary: it is `sizeof(notes)/sizeof(notes[0]) - NUM_FREQS`, i.e.
`96 - 80`. Prefer deriving it so the bound cannot drift if either constant
changes, and add a `static_assert` at the read site.

**This is NOT a free one-liner — checked and confirmed.** `note_offset` is one of
the seven reboot setters locked by `oracle_serial_replay.py`, and its corpus
contains **`note_offset=99`**, which clamps to 32 today. So the regression
harness currently **freezes the defective bound as expected behaviour**: the
golden asserts that an out-of-range request lands on 32, which is precisely the
value that reads past the end of `notes[]`.

Landing the fix therefore requires the repo's lock-then-change discipline:
regenerate `serial_replay.golden.jsonl` under the corrected clamp, and add a
Gate-Fα mutation proving the new bound has teeth (e.g. shift 16 → 17 and confirm
it is caught). Regenerating the golden *is* the correct move here — the old
number encodes a bug, not a contract — but it must be a deliberate, recorded
change rather than a silent one.

## Defect 2 — bass mode likely overruns the AP frame budget

**Severity: performance. Ships today. PROJECTED, not device-verified.**

`visual/led_utilities.h:1852-1858` — both `CHROMA_PROFILE_BASS` and
`CHROMA_PROFILE_FULL` set `new_note_offset = 0`. The profile is user-facing
("BASS MODE ENABLED", `serial/serial_menu.h:3270`).

At `NOTE_OFFSET = 0` every bin targets one octave lower, and since
`block_size ∝ 1/f`, **every block size doubles**:

| | default (`NOTE_OFFSET=12`) | bass/full (`NOTE_OFFSET=0`) |
|---|---:|---:|
| bin 0 target | 110 Hz | 55 Hz |
| bin 0 `block_size` | 978 (76.4 ms) | 1,956 (152.8 ms) |
| Σ `block_size` | **17,222** | **34,484** |
| `process_GDFT` (projected) | ~3,190 µs | **~6,380 µs** |
| share of the 7,500 µs frame | ~43% | **~85%** |

The 85% is the Goertzel *alone*, before onset, tempo, chord or semantic state.
Measured non-GDFT per-frame work is roughly 3,978 µs, which would put the total
far past the frame period. Since the default profile already sits at only
~+22 µs of headroom under real music, **bass mode is expected to overrun.**

### Caveats

- The `process_GDFT` figure is scaled from a 2026-06-21 measurement, and the
  non-GDFT figure is inferred by subtraction across two captures of different
  vintage. Treat the absolute numbers as ±.
- **Not device-verified.** The cheap confirmation is to enable the profile on the
  bench and read the AP cadence telemetry.
- The doubled table also lands at 1,956 against the 2000 clamp — so the clamp is
  live, not dead code, and any sample-rate rise would push bass mode into it.

### Why this matters beyond itself

It strengthens the case for the AP hop change (96 → 128, giving a 10,000 µs
frame): at that frame length the same profile has room it does not have today.

## Provenance

Both defects surfaced from a *wrong* premise. A subagent built its cost table
using `NOTE_OFFSET = 0` — taken from a claude-mem observation title rather than
the config initialiser, i.e. a Tier-2 clue used as Tier-0 truth, the exact
failure mode the memory-authority discipline exists to prevent. The resulting
table was one octave low and was retracted. Checking *why* it was wrong revealed
that `NOTE_OFFSET = 0` is in fact reachable in shipping firmware, which is
Defect 2, and that nothing bounds the index, which is Defect 1.

All file:line references above were verified first-hand against the working tree
at `lane/dual-sync-phase0`, not taken from the subagent's report.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-05 | agent:claude-code | Created — `note_offset` OOB read (verified) and bass-mode frame-budget overrun (projected, needs bench confirmation). |
