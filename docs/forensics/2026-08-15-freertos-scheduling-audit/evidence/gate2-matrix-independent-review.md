# Gate 2 GDFT candidate matrix — independent review

Date: 2026-08-15  
Task: FRTOS-22, attempt 3  
Reviewed base HEAD: `4f0630315eaf852be3da4241124aeb9788ab309f`  
Verdict: **PASS — matrix configuration and host guard only. Gate 2 service/perception remains NOT VERIFIED.**

## Decision

The proposed non-shippable matrix is the smallest valid one-variable PlatformIO experiment:

| Lane | Effective crossover | Only delta from scalar baseline |
|---|---:|---|
| `k1_bench_scheduling_baseline_probe` | default `0` | none |
| `k1_bench_scheduling_gdft_cross40_probe` | `40` | `-DK1_GDFT_X2_CROSSOVER_BIN=40u` |
| `k1_bench_scheduling_gdft_cross80_probe` | `80`, global legacy x2 over the configured 80-bin table | `-DK1_GDFT_X2_CROSSOVER_BIN=80u` |

Both candidates directly extend the existing scalar baseline and append one flag only (`platformio.ini:919-946`). The resolved PlatformIO graph preserves `ARDUINO_RUNNING_CORE=0`, `K1_LED_TASK_CORE=1`, DMA descriptor count 3, 12.8 kHz, 96-sample chunks, novelty d3, both shipping int64 GDFT fixes, the IM69D DSR16 RIGHT input path, source filter, upload/monitor port, scripts, libraries, board and optimisation flags. The base tuple originates at `platformio.ini:59-98`, the IM69D physical-input additions at `platformio.ini:318-336`, and the scalar probe additions at `platformio.ini:916-929`.

The strengthened test resolves PlatformIO's effective graph, preserves flag order, rejects duplicate/later-winning definitions, requires exact values for the frozen tuple, requires candidate flags to equal the baseline list plus exactly one final crossover flag, rejects runtime crossover, true-centre and spectral-window defines, and compares every non-flag option (`tests/test_scheduling_gdft_service_matrix.py:89-131`). This closes the hidden-variable hole found in attempts 1-2.

The upload route is correct and fail-closed: both new envs occur only under B489A500 (`scripts/platformio/k1_device_identities.json:58-72`), and the test exercises actual guard acceptance on B489A500 plus rejection on F887A500 (`tests/test_scheduling_gdft_service_matrix.py:134-154`). No main-K1 or Unit-2 allowlist was broadened.

## Pre-registered compute and geometry facts

`precompute_goertzel_constants()` applies x2 below the crossover and the current one-semitone formula at/above it (`SPECTRASYNQ_K1_FIRMWARE/system/system.h:271-286`). `process_GDFT()` skips bins 71-79 before the inner loop (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:101-134`), so service sums must count the 71 executed bins, not all 80 configured canvas bins.

| Candidate | Executed inner-loop iterations | Min/max resolution | Worst representable centre error | Semantic risk to preserve |
|---|---:|---|---|---|
| cross0 | 34,254 | 6.544 / 609.524 Hz | 154.041 Hz at bin 67 | current reference |
| cross40 | 18,550 | 13.088 / 609.524 Hz | 154.041 Hz at bin 67 | discontinuous knee: bin 39 `N=102` to bin 40 `N=194` |
| cross80 | 17,109 | 13.088 / 1280 Hz | 248.397 Hz at bin 70 | broadest spectral coarsening; compute win is not a semantic win |

These quantities are locked by `tests/test_scheduling_gdft_service_matrix.py:157-194`. They establish candidate identity and modelled work/geometry, not sustainable on-device service or musical quality.

## False-claim boundary

The `musical-semantics probe` wording in `platformio.ini:935-942` describes a capture vehicle only. It does **not** establish semantic acceptance. The governing plan requires sustainable service with margin, bounded sample age/backlog, semantic regression, and a pre-registered real-music comparison (`EXECUTION_PLAN.md:377-390`); its oracle is source/model parity plus real-music paired A/B (`EXECUTION_PLAN.md:539-545`).

Current host machinery cannot close that boundary. The real-GDFT golden explicitly pins the int64 fixes off (`scripts/regression-harness/golden/oracle_gdft.py:77-94`), while semantic replays inject snapshots/stubs rather than exercising candidate GDFT output (`scripts/regression-harness/semantic_state_replay.py:14-24`). Therefore no host-green result may be reported as a musical-semantics pass.

## Validation and rerun

Executed:

```bash
python3 -m pytest -q tests/test_scheduling_gdft_service_matrix.py tests/test_k1_upload_guard.py tests/test_k1_upload_guard_identity_static.py tests/test_gdft_center_honesty.py tests/test_nyquist_bin_hygiene_static.py tests/test_gdft_int64_magnitude.py tests/test_gdft_int64_recurrence.py tests/test_rate_consistency.py
# 86 passed in 1.46s

pio project config --json-output | jq '[.[] | select(.[0] == "env:k1_bench_scheduling_baseline_probe" or .[0] == "env:k1_bench_scheduling_gdft_cross40_probe" or .[0] == "env:k1_bench_scheduling_gdft_cross80_probe")] | length'
# 3
```

An earlier direct `pytest ...` invocation returned `No tests collected` with exit 0 and was rejected as evidence; the successful validation above used `python3 -m pytest`.

Required next mechanical gates, not run by this review:

```bash
pio run -e k1_bench_scheduling_baseline_probe
pio run -e k1_bench_scheduling_gdft_cross40_probe
pio run -e k1_bench_scheduling_gdft_cross80_probe
```

After identity-first B489A500 targeting, Gate 2 still requires same-fixture paired current-device captures for cross0/cross40/cross80, with unchanged scheduler/task/priority/cadence, ordinary streams off except the bounded probe, service/backlog/sample-age evidence, and Captain-confirmed audible real music. If no candidate passes both compute and product contracts, retain cross0 as required by `EXECUTION_PLAN.md:388-390`.

## Scope proof

No firmware, source, test, harness, CI, PlatformIO, identity-manifest, build, upload, flash, monitor, serial or device action was performed by this independent review. The only write is this ignored evidence file.
