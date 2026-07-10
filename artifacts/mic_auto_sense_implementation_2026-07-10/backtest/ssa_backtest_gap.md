# SSA Backtest Gap Audit - MAS-BACKTEST-GAP-20260710

Date: 2026-07-10
Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware`
Branch/HEAD from bootstrap: `lane/dual-sync-phase0` / `cc97081`
Verdict: `NOT_VERIFIED`

## Evidence Question

Are the current tests/backtests sufficient to catch flag-off leakage, AP parser/schema breakage, upload-guard target mistakes, and accidental application of a non-1.0 mic auto-sense scale?

## Short Answer

No. The current focused tests are green and they do cover several important static contracts, but they are not yet decisive enough for a load-bearing claim. The largest gaps are:

1. Flag-off leakage is not closed by an actual stable-section byte gate in this run.
2. AP schema tests are mostly token-presence checks and do not prove conditional gating, field order/sections, or end-to-end summary behaviour for shadow telemetry.
3. Upload-guard coverage for the new shadow env is comparatively stronger, but still depends on synthetic port fixtures and should remain paired with the existing drift-catcher.
4. The non-1.0 scale guard is too weak for flag-on source changes: current tests can still pass if the flag-on `.cpp` returns or writes a non-1.0 applied scale while retaining the existing `applied_scale = 1.0f` seed token.

## Commands Run

```bash
bash scripts/agent/session-bootstrap.sh
```

Result: PASS. Branch `lane/dual-sync-phase0`, HEAD `cc97081`, dirty/untracked tree present.

```bash
python3 -m pytest tests/test_mic_auto_sense_static.py tests/test_audio_telemetry_schema_static.py tests/test_im73d_audio_eval_harness.py tests/test_k1_upload_guard.py -q
```

Result: PASS, `32 passed in 0.07s`.

```bash
python3 -m pytest tests/test_mic_stable_byte_gate_static.py tests/test_im73d_audio_purity_static.py tests/test_i2s_watchdog_static.py -q
```

Result: PASS, `14 passed in 0.05s`.

```bash
bash scripts/agent/pio-build.sh k1_hardware
bash scripts/agent/pio-build.sh k1_bench_im73d_mic_auto_shadow
```

Result: NOT CLOSED. I mistakenly ran these concurrently; PlatformIO reported `.pio/build` directory contention and both builds then failed at `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:8` with `fatal error: Ticker.h: No such file or directory`. I did not clean or mutate build state under the read-only brief.

```bash
/opt/homebrew/bin/rg -n "k1_mic_auto_sense_applied_scale|mas_applied_scale|applied_scale|shadow_scale|K1_MIC_AUTO_SENSE_V1|k1_mic_auto_sense_update_frame|k1_mic_auto_sense_read" SPECTRASYNQ_K1_FIRMWARE tests platformio.ini scripts
```

Result: Source references are limited to the new flag, telemetry fields, update/read call-sites, and tests. Not decisive by itself.

```bash
python3 - <<'PY'
from pathlib import Path
root = Path('.')
source = (root/'SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp').read_text()
test = (root/'tests/test_mic_auto_sense_static.py').read_text()
mutations = {
    'source_return_scale_0p75': source.replace('float k1_mic_auto_sense_applied_scale() {\n  return 1.0f;\n}', 'float k1_mic_auto_sense_applied_scale() {\n  return 0.75f;\n}'),
    'post_seed_applied_scale_0p75': source.replace('k1_mic_auto_seed_defaults(&next);', 'k1_mic_auto_seed_defaults(&next);\n  next.applied_scale = 0.75f;', 1),
}
print('current_test_checks_source_function_return=', '_function_body(source, "k1_mic_auto_sense_applied_scale")' in test)
for name, mutated in mutations.items():
    simple_substring_predicates_still_pass = ('#ifdef K1_MIC_AUTO_SENSE_V1' in mutated and 'applied_scale = 1.0f' in mutated and 'shadow_scale = 1.0f' in mutated)
    print(f'{name}: current source-substring predicates would still pass={simple_substring_predicates_still_pass}')
PY
```

Result: The test file does not inspect the `.cpp` function body for `k1_mic_auto_sense_applied_scale()`, and the current source-substring predicates would still pass for the two non-1.0 source mutations above.

## Existing Coverage That Helps

- `tests/test_mic_auto_sense_static.py` checks `K1_MIC_AUTO_SENSE_V1` is absent from `k1_hardware`, `k1_bench_reference`, `k1_bench_im73d`, and `k1_prod_im73d`; checks the shadow env exists and includes `audio/k1_mic_auto_sense.cpp`; checks the update call is outside the per-sample loop; checks the effective sensitivity helper remains `CONFIG.SENSITIVITY * k1_loud_input_trim`.
- `tests/test_audio_telemetry_schema_static.py` checks AP format tokens for `raw_i16_*`, loud guard, and `mas_*` fields exist.
- `tests/test_im73d_audio_eval_harness.py` checks the generic AP parser can parse one synthetic shadow row and that DSR compare rejects missing raw `raw_i16_*` metrics.
- `tests/test_k1_upload_guard.py` maps `k1_bench_im73d_mic_auto_shadow` to the bench identity, rejects the main identity, and has a drift-catcher for chip-bound envs missing from `K1_TARGETS` or blocked envs.
- `tests/test_im73d_audio_purity_static.py` still locks raw `im73d_raw_i16_*` placement before conditioning and AP emission.

## Gaps

### G1 - Flag-Off Leakage Not Decisively Backtested

Current static tests assert the flag and source filter shape, but they do not run the stable-section byte gate or a clean build in this audit. A token check cannot prove `k1_hardware`, `k1_bench_reference`, and `k1_bench_im73d` are byte-stable with the new `audio/k1_mic_auto_sense.*` files present.

Decisive backtest:

```bash
python3 -m pytest tests/test_mic_auto_sense_static.py tests/test_mic_stable_byte_gate_static.py -q && bash scripts/regression-harness/mic_stable_byte_gate.sh k1_hardware && bash scripts/regression-harness/mic_stable_byte_gate.sh k1_bench_reference && bash scripts/regression-harness/mic_stable_byte_gate.sh k1_bench_im73d
```

### G2 - AP Schema Test Can Pass On Superficial Token Presence

`tests/test_audio_telemetry_schema_static.py` only asserts `mas_state=%u`, `mas_reason=%u`, `mas_window_age_sec=%.1f`, `mas_applied_scale=%.3f`, and `mas_shadow_scale=%.3f` occur somewhere in `i2s_audio.h`. It does not prove those fields are inside the `K1_MIC_AUTO_SENSE_V1` guard, appended after the right AP sections, absent from flag-off production rows, or parsable through a representative production+shadow line set.

Decisive backtests:

```bash
python3 -m pytest tests/test_audio_telemetry_schema_static.py tests/test_im73d_audio_eval_harness.py -q
```

Then add a schema-lock test that extracts the AP printf region, proves `mas_*` is bounded by `#ifdef K1_MIC_AUTO_SENSE_V1`, and feeds both a production AP row without `mas_*` and a shadow AP row with `mas_*` through `parse_ap_line()` and `summarise_numeric()`.

### G3 - Non-1.0 Applied Scale Can Evade Current Tests

`tests/test_mic_auto_sense_static.py` checks the header stub returns `1.0f`, and checks the `.cpp` contains `applied_scale = 1.0f` and `shadow_scale = 1.0f`. It does not parse the `.cpp` body of `k1_mic_auto_sense_applied_scale()` or prove no later assignment changes `next.applied_scale` away from `1.0f`. An accidental `return 0.75f;` in the flag-on `.cpp` or a later `next.applied_scale = 0.75f;` can retain the seed token and escape the current substring predicate.

Decisive backtest:

```bash
python3 -m pytest tests/test_mic_auto_sense_static.py -q
```

After strengthening, that file should include source-body checks for the `.cpp` implementation:

- `k1_mic_auto_sense_applied_scale()` body is exactly `return 1.0f;` for the shadow phase.
- all writes to `.applied_scale` assign `1.0f` only.
- the AP emission argument for `mas_applied_scale` is `mas.applied_scale`, and all possible producers of that field are fixed at `1.0f`.

### G4 - Upload-Guard Coverage Is Strong But Synthetic

The new env is registered under the bench target and the tests cover correct and cross-flash synthetic ports. This is the strongest of the four areas. Remaining risk is not a missing static assertion, but that no live upload was allowed in this brief and no wrapper/build proof closed here. Keep `tests/test_k1_upload_guard.py::test_all_k1_chip_bound_envs_are_registered_in_guard` as the main drift-catcher.

Decisive backtest:

```bash
python3 -m pytest tests/test_k1_upload_guard.py -q
```

If the shadow env stays, also keep the wrapper allowlist locked so the compile-only path can build it without opening upload/monitor tokens.

### G5 - Build Gate Did Not Close

The focused pytest suite passed, but `k1_hardware` and `k1_bench_im73d_mic_auto_shadow` compile were not proven in this audit due the failed concurrent PlatformIO attempt. Build green would still not prove runtime/AP contract, but build red or unrun means this cannot be called verified.

Decisive backtest:

```bash
bash scripts/agent/pio-build.sh k1_hardware && bash scripts/agent/pio-build.sh k1_bench_im73d && bash scripts/agent/pio-build.sh k1_bench_im73d_mic_auto_shadow
```

Run sequentially, not concurrently.

## Strongest Orchestrator Re-Run Command

This is the minimum useful load-bearing backtest bundle once build state is clean:

```bash
python3 -m pytest tests/test_mic_auto_sense_static.py tests/test_audio_telemetry_schema_static.py tests/test_im73d_audio_eval_harness.py tests/test_k1_upload_guard.py tests/test_mic_stable_byte_gate_static.py tests/test_im73d_audio_purity_static.py -q && bash scripts/regression-harness/mic_stable_byte_gate.sh k1_hardware && bash scripts/regression-harness/mic_stable_byte_gate.sh k1_bench_reference && bash scripts/regression-harness/mic_stable_byte_gate.sh k1_bench_im73d && bash scripts/agent/pio-build.sh k1_bench_im73d_mic_auto_shadow
```

Expected decisive additions before claiming `VERIFIED`:

1. Strengthen `tests/test_mic_auto_sense_static.py` so flag-on `.cpp` non-1.0 applied scale mutations fail.
2. Strengthen AP schema/parser tests from token presence to guarded region + representative production/shadow parse/summary fixtures.
3. Run the stable-section byte gate for flag-off envs and a sequential compile for the shadow env.

## Method Risk

This audit did not modify tests to run real mutation tests, did not run full pytest, and did not close PlatformIO builds after the concurrent-build failure. The conclusion could be too pessimistic if an uninspected CI/backtest job already runs the byte gate and stronger mutation checks elsewhere; I did not find that proof in the inspected local tests/artifacts.
