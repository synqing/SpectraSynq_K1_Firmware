---
abstract: "RANGE=1 writer IDENTIFIED (2026-08-13): the Aug-9 Deck16 full71 control-map harness wrote stimulus vmin+0.37 into every float control over BLE-MIDI with NO restore step — global.chromagram_range got 1.37, the control facade truncates uint8_t(1.37)=1 and persists via save_config_delayed(). Timeline sealed: full71 matrix 06:18 → RANGE=1 in dark-fade resync log 07:10 → prism-off dump 07:33. No load-time clamp exists (load_config memcpy's the blob verbatim), so a live :chromagram_range=60 survives reboot; re-poisoning requires a stimulus-writing harness to run again. Guard rule: any harness that writes controls MUST snapshot (:dump) before and restore after."
---

# CHROMAGRAM_RANGE 60→1 — the writer, identified (2026-08-13)

Closes the open sub-question from
[`colour-nuance-regression-verdict-2026-08-13.md`](./colour-nuance-regression-verdict-2026-08-13.md)
§Defect 1 ("WHAT wrote 1") and canon insight #4
(`docs/canon/SESSION_CANON_2026-08-13_colour_forensics_config_poison.md`).

## Verdict

**The writer is the Deck16 full71 control-map harness run of 2026-08-09
(`_scratch/deck16_full71_map_20260809/`).** Not a Tab5 product-path write, not a defaults
reset, not a load-time clamp.

## The mechanism (all steps evidenced)

1. **Stimulus table** — `_scratch/deck16_full71_map_20260809/CONTROL_MATRIX.json` assigns each
   float control a test stimulus of `vmin + 0.37`:
   `global.chromagram_range → 1.37` · `global.sensitivity → 0.37` · `primary.chroma → 0.37` ·
   `primary.mood → 0.37` · `primary.photons → 0.4015` · `global.master_brightness → 0.37`.
2. **No restore** — `full71_harness.py` contains no restore/revert logic of any kind (verified:
   neither token appears in the source). The harness proves apply-delta and walks on.
3. **Truncation** — the K1 control facade
   (`SPECTRASYNQ_K1_FIRMWARE/control/k1_control_facade.cpp` `global.chromagram_range` branch)
   accepts 1.37 (range check is [1.0, NUM_FREQS]), assigns
   `CONFIG.CHROMAGRAM_RANGE = uint8_t(record.number_value)` → **1**, then
   `save_config_delayed()` → **persisted to flash**.
4. **Applied receipt** — `evidence/full71_matrix_final.json` entry for
   `global.chromagram_range`: `stimulus "1.37"`, `result PASS`, K1-side confirm observed.
5. **Timeline** (file mtimes, 2026-08-09): full71 matrix final **06:18** →
   `_scratch/k1_bench_dark_fade_20260809/link_proof_resync.log:183` `CHROMAGRAM_RANGE: 1`
   **07:10** → `_scratch/bench_k1_prism_off_20260809/prism_off_before_dump.txt` `RANGE: 1`
   **07:33**. Last known-good: Aug-8 B1/B2 proofs (`proof_S1/S4/S9/G2.3.log`) all read **60**.
6. **Why only RANGE stuck** — commonly-touched knobs (sensitivity was back at 1.994891 by
   07:33) were rewritten by later lanes; `chromagram_range` is touched by nothing else, so the
   harness value persisted four days until the 2026-08-13 excavation found it.

## Wholesale-poisoning corollary

The harness did not poison one field — it replaced **every writable control** with a test
stimulus and persisted the lot. The Aug-9→13 config drift the era replay had to undo
(CHROMA/MOOD/etc.) is the same event, partially masked by later lanes rewriting the popular
knobs.

## Re-poison analysis (the pre-registered clamp test, answered from source)

`load_config()` (`SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h`) memcpy's the validated
blob into `CONFIG` **with no per-field clamping or migration of `CHROMAGRAM_RANGE`**; the
CFG_FALLBACK path loads compiled defaults (60). There is **no load-time clamp**: a live
`:chromagram_range=60` persists across reboot. Re-poisoning requires a stimulus-writing
harness (full71 or a successor reusing `CONTROL_MATRIX.json` semantics) to run again.
Mechanical on-device confirmation (set 60 → reboot → re-read) is pending the next scheduled
device window; it is not a blocker for the fix lane.

## Guard (the rule that prevents a repeat)

**Any harness that writes controls (BLE-MIDI, facade, serial setters) MUST take a full
`:dump` snapshot before its first write and restore every touched field after its last —
and the restore must be verified by a second `:dump` diff.** Proving "apply works" by
mutating persisted product config and walking away is exactly how a diagnostic became a
four-day product defect. (Same family as HF-41: config is half the firmware identity —
harnesses that mutate it are flashing half a firmware.)

## Relation to the two BLE-side theoretical vectors (for completeness)

The BLE map (`network/k1_ble_midi_map.h`) gives `global.chromagram_range` CC14 ch2/cc2+34
with vmin=1.0 — any n14=0 frame decodes to exactly 1.0, and `primary.chroma` shares cc-pair
2/34 on ch0, so a channel-crossed chroma≈0 write also lands on RANGE. Both remain REAL
product-path hazards worth a future clamp-guard discussion, but neither is the Aug-9 writer:
the full71 receipt is explicit and the timeline closes around it.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-13 | agent:claude-code | Created — writer identified (full71 stimulus 1.37, no restore), timeline sealed, no-clamp proof, harness snapshot/restore guard rule. |
