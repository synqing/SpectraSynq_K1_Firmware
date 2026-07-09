---
abstract: "Session handover 2026-07-06 for the next K1 firmware agent. CLOSED: palette-vibrancy fix shipped + eyes-on PASSED on main K1 (ae5d90a); IM73D mic-eval acceptance COMPLETE (per-band AGC gate PASSED 2026-07-06, gains 16-30x under ceiling; selection Captain-ratified 2026-07-03). OPEN, in recommended order: (2) lane consolidation (merge lane/palette-vibrancy-v1 into lane/im73d-pdm-eval — conflict map inside), (3) vibrancy forensic doc (key numbers preserved inside), (1) IM73D productionization into k1_hardware (Captain-gated hardware fork). Read before any K1 firmware work; includes device identity table + the session's hard-won gotchas."
---

# K1 firmware — next-lanes handover (2026-07-06)

## TL;DR
Two lanes CLOSED this session: **palette vibrancy** (main K1, eyes-on PASSED) and **IM73D mic-eval acceptance** (per-band AGC gate PASSED today; mic selection was already Captain-ratified 2026-07-03). Three items remain, in recommended order: **consolidate the two diverged lanes → write the vibrancy forensic doc → open IM73D productionization**. K718 work is **parked by Captain directive (2026-07-06)** — do not pick it up.

## Device truth (identity by MAC ONLY — ports scramble daily)

| Unit | Chip | USB serial (MAC) | Runs (proven) | Notes |
|---|---|---|---|---|
| Main K1 (production) | `F887A500` | `B4:3A:45:A5:87:F8` | `k1_hardware @ ae5d90a` (vibrancy, eyes-on PASSED) | knobs restored: chroma 0.100 / mood 0.200 / base 0.050 |
| Bench K1 | `B489A500` | `B4:3A:45:A5:89:B4` | `k1_bench_im73d_ble @ 79d7fda` (PDM PASS, BLE begin, `cal_source=persisted_profile`) | IM73D mic on GPIO 12/13/14; LED bench pins 4/5 |
| K718 Remoted | — | `AC:A7:04:EE:57:7C` | (parked — no K718 work) | has occupied `usbmodem101` before |

`pio device list` → match `SER=` before ANY open/flash. The upload guard is the last line, not the first.

## Item 2 (do FIRST) — lane consolidation

**Goal:** one product line. `lane/palette-vibrancy-v1` (@ `66e5002`: the vibrancy fix `ae5d90a` + main-K1 registry row) and `lane/im73d-pdm-eval` (@ `24e0732`+, the active line) diverged 2026-07-03.

1. **Pre-check (load-bearing):** `git status --short` and confirm NO other session is active (this session was bitten twice by concurrent-session index races — foreign staged files swept into a commit; a staged file silently dropped). If any tracked modifications exist that you didn't make, stop and identify their owner first.
2. On `lane/im73d-pdm-eval`: `git merge lane/palette-vibrancy-v1`.
3. **Expected conflicts + resolutions:**
   - `docs/hardware/device-build-registry.md` — both branches inserted deployed-state rows at the table top. Keep **both** sets, newest-first. While there: edit the vibrancy branch's main-K1 row — replace its "REMAINING: Captain eyes-on at LOUD volume" with **"eyes-on PASSED 2026-07-03 ('yes it looks great') — release gate CLOSED"** (this edit has been owed since 07-03).
   - `platformio.ini` — vibrancy added `-DK1_PALETTE_VIBRANCY_V1` + comment block at the end of the `[env:k1_hardware]` flags (after the palette-resolution-lane comment); the im73d lane edited elsewhere. Keep both. **Post-merge assert:** `grep -c K1_PALETTE_VIBRANCY_V1 platformio.ini` ≥ 2 and the `k1_bench_im73d`/`k1_bench_im73d_ble`/`k1_custom` env blocks intact.
4. Gate: `pytest tests/` + `pio run -e k1_hardware` (pre-commit hook re-runs it on the merge commit anyway).
5. **No reflash needed** — the main K1 already runs the `ae5d90a` binary; the merge only unifies history.

## Item 3 — vibrancy forensic doc (anytime; docs-only)

Create **one canonical** `docs/forensics/2026-07-02-palette-vibrancy-colour-collapse.md` (frontmatter abstract + changelog footer). The scratch counters lived in an ephemeral job dir — the key numbers are preserved here; write them into the doc:

- **Symptom:** "palettes progressively duller over 2–3 weeks; each palette a handful of colours."
- **Disproven lanes (do not relitigate):** output gamma/dither (firmware 4-phase dither active, ×3.97 effective levels; gamma-ON *crushes* shadows 153→17 codes); deprecated Class-1 `ColorFromPalette` modes (unreachable, `config_types.h:184-198`); calibration drift (values byte-stable).
- **Root cause chain (device-proven on main K1):** loud/dense music → AGC+loud-guard attenuate GDFT (`agc_gain` floor-pinned 0.08–0.18, `gdft_trim` 0.86–0.94) → chroma flatness sinks into the sparseness-gate band (live capture: flatness 0.051–0.150; one full gate-ZERO at flatness 0.0514; post-gate chroma ≤0.133) → weak centroid → held-hue hard freeze (`lightshow_modes.h:331`) → one auto-shift-swept coordinate. Three-loudness-state gradient captured (loud/medium/quiet) proving loudness coupling. "Progressive" = stacked landings 06-11 (gate+held-hue) / 06-17 (loud-guard) / 06-30 (per-band AGC), each deepening it.
- **Fix (`ae5d90a`, flag `K1_PALETTE_VIBRANCY_V1`):** (1) palette-coordinate engine reads a new POST-normalize PRE-gate export `chromagram_pregate[12]` (quiet-guarded at `norm_max≤0.08` — silence hold preserved); (2) weak-centroid blends held→live by `strength/0.08` (`k1_vibrancy_blend_hue`) — never dominant-bin (dark-start crush stays fixed).
- **Host proof:** DENSE 2 coords/0.02 bits/99.8% frozen → **11 coords/3.27 bits/0%**; QUIET hold byte-identical (hue range 0.0000); dark-start palette lit_fraction **0.002 (sat on BLACK) → 0.648** (crush signature was 0.239); TONAL 3.35→3.42 bits. Gate: pytest 620 + clean build.
- **Silicon + verdict:** `:build git=ae5d90a` on main K1; **Captain eyes-on PASSED 2026-07-03**.
- **Standing rules:** never re-point the palette engine at post-gate `chromagram_smooth`; never blend toward dominant-bin; revert = delete one `-D` line.

## Item 1 — IM73D productionization (the big one; Captain-gated fork)

**Decision already made — never re-open:** IM73D122 **is** the K1 production mic (Captain-ratified 2026-07-03). Remaining = carry it into the production build/unit.

**Read first:** `docs/spec-index.md` Active Lanes (the productionization lane authority + device-proof protocol landed via `1c14990`); Phase 1.1 evidence (cal persistence: `cal_source=persisted_profile` — verify exactly what `e2b62b5`/Phase 1.1 changed vs the old eval-era NVS-freeze in `bridge_fs.h`, which was *eval protection* and must NOT ship as-is); `docs/hardware/im73d122-graft-handover-2026-07-02.md` (graft gotchas); memories `im73d-production-decision`, `im73d-pdm-snr-modes` (DSR_8S locked; DSR_16S = reserved +2 dB lever).

**The work, staged:**
1. **Audit what's bench-specific** in the `K1_MIC_IM73D_PDM_V1` code: pins (bench mic = GPIO 12/13/14 — the **production pin map may differ**; bench LED pins are 4/5 vs production 6/7, so verify mic pins against the production PCB, not by assumption), gain (`K1_MIC_IM73D_INPUT_GAIN 16.0` was bench-characterized on an OPEN bench — the sealed production enclosure changes acoustics → **re-characterize on production hardware**; SSL window headroom is tight at g=16: silence cals to ~710 of [50,720] — widening the window is the bounded escalation, never a blind gain bump), and the eval-era freeze/force-invalidate blocks (replace with the Phase 1.1 persistence path).
2. **Hardware fork (Captain):** the production unit physically carries an SPH0645 today. Mic install/PCB rev = Captain's hands + product-truth decision on pins. Firmware can be fully prepared behind a production flag before hardware exists.
3. **Firmware shape:** a `K1_MIC_IM73D_PROD_V1` (or promotion of the existing flag) in `k1_hardware` — keep the SPH path revertible until the production unit is device-proven. Byte-identity is NOT a gate here (default flip is the point) but flag-OFF identity still is.
4. **Gates:** host (pytest + build) → bench proof (the bench IS the IM73D reference) → production-unit device proof per the lane's device-proof protocol → Captain silence-go recal on the production unit → eyes-on.

## Session gotchas (cost real time — read before touching anything)

1. **Serial:** bare bytes = HOTKEYS; typed commands need `:` prefix (`serial_menu.h:3478`). One bare-command spray mutated live knobs (since restored). Read-only status keys: `;` (status), `:dump`, `:vp_status`, `:secondary_status`, `:build`.
2. **Ports scramble constantly** — `usbmodem101` was the K718 on 07-04 and the bench on 07-06. MAC first, always.
3. **Concurrent sessions share this worktree** — check the index before staging; verify the commit stat matches your intent; never `git commit` with foreign staged files; avoid git ops while another session is live.
4. **Cursor's PlatformIO extension auto-holds serial ports** (Errno 16 with no visible `lsof` holder) — Captain closes it.
5. **The rtk/tee shell wrapper truncates long command output** — redirect to a file and grep; trust exit codes + on-silicon `:build` proof over log tails.
6. **DTR/RTS-low before `open()`** for pyserial; rapid open/close cycles can wedge the unit into download mode — power-cycle recovers.
7. **`start_noise_cal` is NEVER auto-fired** — Captain-verbal silence-go only ("unrestricted use" does not waive it).
8. **"bench K1 firmware" = `k1_bench_im73d_ble` ALWAYS**; `k1_custom` = the wall/custom build, explicit instruction only. A registry row saying "bench runs k1_custom" means the unit was borrowed.
9. **No K718 work** (Captain, 2026-07-06) until directed otherwise.
10. **Never measure mic SNR on a BLE build** — radio-free `k1_bench_im73d` is the measurement env.

## Evidence anchors
- AGC acceptance PASS: registry row `24e0732` (g0–g3 max 0.33–0.60 vs ceiling 10, 40 s live music).
- Vibrancy: commits `ae5d90a` (fix) + `66e5002` (registry, on the vibrancy branch); memory `palette-vibrancy-v1-shipped`.
- Bench state: registry rows `80ffcaa` (build-naming rule) + `24e0732`.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-06 | agent:claude-code | Created: triple-lane handover (consolidation, forensic doc, IM73D productionization) after closing vibrancy eyes-on + IM73D per-band AGC acceptance. |
