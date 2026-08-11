# Tab5 session canon validation — 2026-08-11

## Verdict

**PASS — durable lessons, routing, and executable recurrence guards.**

This validates the documentation/skill/harness layer and the later source
recovery recorded below. It does not claim a new perceptual pass, production
promotion, full G3 completion, or device flash.

## RED baseline

The baseline was the real session, not a synthetic story: three committed
palette iterations and two uncommitted field iterations satisfied progressively
stronger source/mechanical properties while Captain still observed the rejected
mechanical/banded result. G0 and G3 also contained documented evidence-boundary
overclaims later reopened by audit.

## Shipped prevention

- load-bearing 25-row failure/resolution/prevention inventory;
- nested `tab5_firmware/AGENTS.md` with identity, ownership, presenter, motion,
  busy-work, and claim-vocabulary hard stops;
- `tab5-embedded-ui-motion-gate` for Claude and Codex routing;
- existing Tab5 LVGL and live-harness skills amended for motion and identity;
- seven active motion mutants, including a technically nonzero but
  perceptually negligible 2D effect-size mutant;
- actual circular palette integration extracted into a host-testable function;
- uniform-colour, circular wrap, symmetry, and 11-tap support tests;
- G3 receipt corrected from full closure to bounded WDT/RSSI proof;
- both selected TRIAL font families named in source and canon;
- durable memory pointer written under Codex ad-hoc notes.

## Commands and results

```sh
python3 -m pytest tab5_firmware/tests -q
# 26 passed in 28.12s

pio run -d tab5_firmware -e native_sdl
# SUCCESS in 1.10s

PLATFORMIO_CORE_DIR=/tmp/tab5_pio_core_canon_20260811 \
  ~/.platformio/penv/bin/pio run -d tab5_firmware -e tab5_p4
# SUCCESS in 239.36s from an empty isolated core
# RAM 76,072 / 512,000 bytes (14.9%)
# flash 1,343,205 / 3,145,728 bytes (42.7%)

clang++ -std=c++17 -Wall -Wextra -Werror \
  -Itab5_firmware/include tab5_firmware/src/palette_flow.cpp \
  tab5_firmware/tests/palette_flow_harness.cpp \
  -o /tmp/tab5_palette_flow_harness
/tmp/tab5_palette_flow_harness
# palette_flow PASS jacobian=0.614 distinct=595 row_delta_q16=1025

git diff --check
# PASS
```

P4 artefacts after the successful build:

```text
firmware.bin 9a7e72541d4e370137298bd99919aaab70e564c90e92213d1fc0d62abc6708ac
firmware.elf 5d5ebc7745ae94b6a9528bc2300804191b77859bd9d9337846129b6d6100e959
```

The first final rerun caught the shared global PlatformIO cache carrying Arduino
3.2.0 metadata and the pinned-package guard refused the build. The isolated core
resolved the official 3.3.1 archive and passed every checksum. This is now part
of the source-closure lesson: mutable shared caches are not release authority.

The successful isolated build retained a non-fatal existing `esp_idf_size --ng` option
warning before PlatformIO's own size check. It did not affect compilation,
linking, binary generation, or the final SUCCESS result.

## Independent skill pressure test

A read-only independent agent applied the new motion skill to: “all host gates
are green, but Captain says it still looks mechanically identical.” It returned
the required decision: **not fixed; mechanical rail PASS, perceptual rail RED**.
It confirmed the skill would have blocked the false-positive claims after
`95d422b`, `b0c2cde`, `0a07e73`, the shared 1D field, and the first hard-banded
2D field.

The review found seven gaps. They were addressed before this receipt:

- “topology-level” narrowed too far -> changed to falsifiable mechanism-level;
- recipe could become a compliance shield -> baseline explicitly cannot overrule glass;
- physical proof underspecified -> continuous duration/state/transition requirements;
- chat-only proof -> mandatory `MOTION_GATE_RECEIPT.md`;
- authority to close ambiguous -> Captain closes Captain-rejected criteria;
- mutants ignored effect size -> quantitative `row_delta_q16` threshold + mutant;
- claim hook absent -> nested AGENTS contract and static reachability tests.

## Remaining blockers and claim boundary

- The source is committed and recoverable through the local recovery chain
  documented below.
- No final `MOTION_GATE_RECEIPT.md`, high-frame-rate physical capture, presenter
  timing counters, or long device soak exists for the recovered workload.
- Full original G3 fault + ordinary soak is `NOT_VERIFIED`.
- Countach and Berkeley Mono selected sources remain TRIAL.
- The M5GFX overlay and current palette source require renewed clean-clone G0
  proof before release promotion.
- No device was flashed or disturbed while creating this canonisation layer.

## Branch recovery closeout

The previously dirty state was preserved before repair, then corrected in two
reviewable commits:

```text
a5fc39a9 wip(tab5): preserve final palette field and session canon
4cf538fa fix(tab5): gate status redraws on state changes
3c1782a9 fix(tab5): restore product RF selector
```

`a5fc39a9` is the immutable recovery point for the exact 20-file palette/canon
state that existed before repair. `4cf538fa` prevents the 1 ms palette tick from
rewriting LVGL status labels and styles at roughly 1 kHz. `3c1782a9` restores
the known-good `WiFiAntenna` product source, initialises the internal RF path
after `M5.begin()`, and proves the selector symbol is linked into the P4 ELF.
The unrelated vendor-package symlink from the historical restore worktree was
deliberately excluded.

Recovery validation at `3c1782a9`:

```text
python3 -m pytest tab5_firmware/tests -q
28 passed in 29.12s

pio run -d tab5_firmware -e native_sdl
SUCCESS in 5.18s

PLATFORMIO_CORE_DIR=/tmp/tab5_recovery_pio_5QhRkC \
  ~/.platformio/penv/bin/pio run -d tab5_firmware -e tab5_p4
SUCCESS in 68.87s
RAM 76,112 / 512,000 bytes (14.9%)
flash 1,343,679 / 3,145,728 bytes (42.7%)

python3 tab5_firmware/scripts/tab5_palette_motion_mutation.py \
  --repo-root /Users/spectrasynq/SpectraSynq_K1_Tab5_Hardening \
  --json /tmp/tab5_palette_motion_recovery_20260811.json
TAB5_PALETTE_MOTION_MUTATION_GATE=PASS mutants=7
```

Committed-source P4 artefacts:

```text
firmware.bin 3ff10f093e100ab823b6316bf721698f323814adb3f1cbae6900c3b3a6f0ad40
firmware.elf 72744c23556654cda10344e7b8d6474f259d13ce3582cb6ffe25c292e51323d8
```

The source/host recovery rail is PASS. Physical palette quality, RF behaviour,
on-glass motion, WDT soak, and full G3 promotion remain `NOT_VERIFIED` until the
specified device sequence is run.
