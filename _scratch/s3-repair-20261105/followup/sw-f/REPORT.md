# 8.1 Changed artefacts

- `677d3abf`: two Forge effect files; bench-only design variants plus setup/transport-setup/colour scopes. Four-pixel cells and local spring coupling. Build guards require B489 and MabuTrace; product flags remain off.
- `0277aca5`: both Forge variants use sixteen-pixel cells (five texture samples), preserving eight moving streaks and every spectrum bin's contribution.
- `5b7feb02`: Mode24 only uses forty-pixel cells (two texture samples). Mode21 F2 preserved exactly. Root integrated as `8accab34`.
- `expected-result.json`, `expected-result-v2.json`, `expected-result-v3.json`: rules written before each design change. `gates.json`: successes, failures and pending capture. `measured-through-v2.json`: copied measured provenance and cadence values.
- No platformio.ini, audio-producer, calibration, device or main-branch edits by F. Root owns captures/restoration; no push.

# 8.2 Gates

- `bash scripts/agent/pio-build.sh k1_fe_emu`: exit0; `build-emu.log`. Sequential repeat exit0; `build-emu-repeat.log`.
- `PLATFORMIO_BUILD_FLAGS=<lite treatment flags> bash scripts/agent/pio-build.sh k1_fe_bench_b489_trace_dev`: F1/F2/F3 exit0; `build-lite.log`, `build-lite-v2.log`, `build-lite-v3.log`. F2/F3 supplied all seven treatment flags; no config edit.
- `python3 -m pytest tests/test_new_effects_batch_static.py tests/test_chord_hue_consumer_static.py tests/test_sprite_upper_transport.py tests/test_esp_emulator_seams_static.py -q`: exit0; 28 passed; `focused-tests.log`.
- Initial replay exit1 (`replay.log`): subsequent PlatformIO environment removed earlier emulator build output. Preserved lite image, rebuilt sequentially, reran existing `run.py run_case`; exit0, `replay-second.log`, `stock-replay-receipt.json`.
- `cmp` against pre-followup separately built native outputs: both modes exit0; `stock-parity-21.exit`, `stock-parity-24.exit`. Original frozen-stock RGB8 gate also exit0; `stock-replay-receipt.json`.
- F2/F3 stock source preservation comparisons exit0; `v2-stock-source-parity.json`, `v3-source-parity.json`. F3 Mode21 whole-file comparison also exact.
- Silicon F1 combined target: exit1 (both modes). F2 combined target: exit1 (Mode24 only; Mode21 meets target). F2 cadence: exit0 both. Exact commands/exits: main `followup/sw-c/gates-fragment.json`; numerical detail in `effect-cost-table.json`. F3 Mode24 captured: selected target command exit1 (Mode24 rawmax1807); selected hard2,000 ceiling and cadence commands exit0. Exact subprocess commands copied into `gates.json`.
- Root H owns the full suite. Local commit hook full-suite bypass preserved the brief's single shared suite.

# 8.3 Measured numbers

- Recipe SHA-256: `5e65de9f0bf342bbb3dbfd7c3033ee4a1901df57378ff77dc0645986185fd1d3`.
- Silicon: `k1_fe_bench_b489_trace_dev`, 240 MHz; common `build-flags.ini`, treatment `lite-build-flags.ini`. Raw full retained trace values below; no outside-window overruns discarded.

| Variant | Integrated commit | Mode21 max / p99 µs | Mode24 max / p99 µs |
|---|---|---:|---:|
| F1 | 85da2224 | 2666 / 2575 | 2882 / 2799 |
| F2 | f87fe1f2 | 1742 / 1740 | 1990 / 1983 |
| F3 | 8accab34 | F2 preserved | 1807 / 1796 |

- Full before-stock/final-stock/selected-lite body and cadence values with identities are preserved in `final-measured.json`; root/C owns final consolidated seven-effect table. Common-window numbers differ from raw-tail maxima and remain explicitly labelled there.
- Personally inspected final `followup/visual/24-stock-vs-lite.png`, identity8accab34: 79/79 lit and unique frames; informational byte difference71.92%. Neither sheet proves physical appearance or sample-exact stimulus alignment.
- Selected Mode24 F3 full-tail cadence: p99 7,013 µs; mean6,301.10 µs; maximum consecutive misses0; recovery0. Maximum gap7,036 µs. Common-window body max/p99=1,807/1,799 µs; raw p99=1,796 µs.
- Host, flag-off: 1,867 frames each. Native bytes exactly match the separately built pre-followup bounded outputs. Against older frozen stock7a7507b2, Mode21 differs34/1,792,320 RGB8 bytes and Mode24 differs52; max1 and identical lit masks. Differences predate followup.
- Personally inspected `followup/visual/21-stock-vs-lite.png`: F2 remains lit with changing streaks, retains the purple/magenta palette structure, and visibly coarsens the texture. Informational sampled byte change69.69%; timing labels are aggregates, not per-row measurements. This is submitted-buffer evidence, not optical evidence.

# 8.4 Not verified

- Mode24 target remains OPEN after all three designs: raw maxima2882 →1990 →1807 microseconds. F3 is fastest and retained; no fourth attempt. It passes the existing2,000 ceiling. Mode21 retains F2 rawmax1742. Mode24 final PNG inspected: all79 captured frames lit and unique; changing streaks and purple/magenta structure remain. Two broad texture cells and changed bright-region timing are visibly different from stock. This meets the limited music sanity rule for the decision pack, not visual equivalence.
- Lite quiet/return behaviour is source-preserved but not independently captured here; same-clip music contact sheets do not establish all-input behaviour or physical appearance.
- Selected lite measured section coverage21=89.46%,24F3=89.00% over full tail; no claim it reaches90%. C reports the required stock section coverage gate passes. Shorter variant bodies increase the measured fraction occupied by trace/dispatch overhead.
- Full suite, final normal flash, 28-mode validation and settings restoration belong to root; no worker claim of their completion.

# 8.5 Decisions for Captain

- Per effect: stock, lite or later redesign — `followup/visual/index.png`.
- Named effect ceiling changes — `followup/ceiling-option.json`.

Remaining execution: root completes normal-build/restoration and final shared gates. Forge implementation and decision-pack inspection finished; Mode24 target1800 remains OPEN after three designs. No further Forge code changes.
