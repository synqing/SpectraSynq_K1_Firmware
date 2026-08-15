# Gate 2 device receipt — independent audit

Date: 2026-08-15
Task: FRTOS-23
Reviewed source HEAD: `35de4e530fe3fecf988aa78c31cf6cbb53e66f13`
Final verdict after attempt 2: **ACCEPT the corrected v3 receipt. Gate 2 BLOCKED/OPEN is correct; Gate 3 dependency-block is correct; no candidate meets the compute-tail contract.**

## Attempt history

- **Attempt 1 — REJECTED as a complete matrix:** the original six 15-second exports
  lacked `APCAD_CAPTURE_DONE`, and 388–1,043 device-buffer rows were not exported.
  Those prefixes remained valid negative witnesses but could not support a completeness
  claim.
- **Attempt 2 — ACCEPTED:** the replacement `gate2v3_*` captures use five-second
  acquisition plus a 90-second bounded export. All six now close exactly with
  `BEGIN.count = parsed rows = DONE.count`, both drop counters zero. This repairs the
  attempt-1 admission defect without changing the negative tail result.

## Attempt 1 — superseded incomplete-export audit

### Scope and decision

I re-read `gate2-device-ab-inconclusive.md`, all six filtered Gate-2 APCAD logs and all six JSON summaries, the current Gate-0 margin contract, the Gate-2 execution-plan clauses, the live PlatformIO graph, and the parser that generated the summaries. I recomputed every service-table field from the filtered rows rather than trusting the receipt.

The six exported subsequences independently prove that cross0, cross40 and cross80 all fail the pre-registered AP tail requirement under both no-playback and real-music fixtures. They do **not** form six complete 15-second captures: every host dump timed out before `APCAD_CAPTURE_DONE`. That defect prevents a positive candidate acceptance, but it cannot rescue any candidate from the negative tail result.

## Receipt table verification

The receipt's service table is numerically exact after its displayed rounding. Re-running the checked-in parser over each APCAD log produced exact equality with the corresponding summary's complete `timing_us` object and decision counters.

| Fixture | Cross | Exported rows | AP Hz | Active median / p95 / p99 | Active >7.5 ms | GDFT median | Newest-to-publish p95 | Table check |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| no playback | 0 | 984 | 93.1930 | 9,330 / 11,423.8 / 11,721.51 us | 984 | 7,139 us | 11,330.55 us | exact |
| no playback | 40 | 970 | 131.9624 | 5,994.5 / 8,012.1 / 8,345.86 us | 148 | 3,989.5 us | 7,933.2 us | exact |
| no playback | 80 | 985 | 133.3333 | 6,006 / 8,063 / 8,306.48 us | 176 | 3,723 us | 7,979.8 us | exact |
| real music | 0 | 1,005 | 93.0319 | 9,341 / 11,316.4 / 11,607.92 us | 1,005 | 7,128 us | 11,233.6 us | exact |
| real music | 40 | 987 | 128.5863 | 6,443 / 8,373.2 / 8,668.42 us | 284 | 4,079 us | 8,293.6 us | exact |
| real music | 80 | 958 | 133.3055 | 6,067.5 / 8,123.45 / 8,303.86 us | 221 | 3,750 us | 8,033.75 us | exact |

The parser defines active AP work as `total_us - i2s_us` and counts work strictly above 7,500 us (`scripts/regression-harness/device_ap_cadence_capture.py:450-461,515-516`). Its percentile interpolation and summary fields are at `device_ap_cadence_capture.py:249-301,436-519`.

All six exported row sets also independently reproduce:

- zero frame-index gaps;
- zero capture-sequence gaps inside the received subsequence;
- zero timestamp-order failures and regressions;
- assumption ID `1` on every timestamped row;
- zero I2S-status and byte-count failures;
- one effective tuple only: 12,800 Hz / 96 / d3 / DMA3 / AP0 / VP1.

## Blocking correction — every APCAD export is incomplete

The receipt's zero-gap claim is true only within each received contiguous prefix. It is not proof of a complete dump.

| Fixture | Cross | Device-buffer count in `APCAD_CAPTURE_BEGIN` | Exported rows | Unexported rows | Dump completion |
|---|---:|---:|---:|---:|---|
| no playback | 0 | 1,394 | 984 | 410 | false |
| no playback | 40 | 1,978 | 970 | 1,008 | false |
| no playback | 80 | 2,000 | 985 | 1,015 | false |
| real music | 0 | 1,393 | 1,005 | 388 | false |
| real music | 40 | 1,936 | 987 | 949 | false |
| real music | 80 | 2,001 | 958 | 1,043 | false |

Every raw log ends with `# apcad_dump_done=False`, every summary has an empty `capture_metadata.done`, and every header count exceeds `row_count`. Device-side `dropped=0` means the internal capture ring did not overwrite records; it does **not** mean the host exported the whole ring. The current receipt's `NO_PLAYBACK_SERVICE_MATRIX = PASS_AS_MEASUREMENT` and `REAL_MUSIC_SERVICE_MATRIX = PASS_AS_MEASUREMENT` should therefore be downgraded to **PARTIAL_NEGATIVE_WITNESS**. Gate 1's governing admission rule explicitly makes capture loss inadmissible (`EXECUTION_PLAN.md:373-375`).

## Why the negative tail verdict remains conclusive

Gate 0 pre-registers `ap_service_p99_max_fraction_of_arrival = 0.8` with a 7,500 us arrival period, so the p99 service ceiling is 6,000 us (`gate0/contract.json`, `production_tuple.ap_arrival_period_us` and `margin_rules.ap_service_p99_max_fraction_of_arrival`). No candidate passes merely because its average cadence recovers (`EXECUTION_PLAN.md:146-159,384-390`).

Even under the most candidate-favourable bound—treat every unexported row as at or below 6,000 us—the already observed rows above 7,500 us exceed 1% of the **full device-buffer count** in all six runs:

| Fixture | Cross | Observed >7.5 ms | 1% of full buffer | Full-run p99 consequence |
|---|---:|---:|---:|---|
| no playback | 0 | 984 | 13.94 | >7.5 ms |
| no playback | 40 | 148 | 19.78 | >7.5 ms |
| no playback | 80 | 176 | 20.00 | >7.5 ms |
| real music | 0 | 1,005 | 13.93 | >7.5 ms |
| real music | 40 | 284 | 19.36 | >7.5 ms |
| real music | 80 | 221 | 20.01 | >7.5 ms |

Therefore every possible completed distribution consistent with these captures has p99 above 7,500 us, and necessarily above the 6,000 us margin. Cross40 and cross80 improve median GDFT/service demand; neither closes tail service. Cross0 is unsustainable throughout the exported rows. The receipt's `GDFT_ONLY_TAIL_MARGIN = FAIL_ALL_CANDIDATES` is correct.

## Hash and fixture verification

All six summary hashes in the receipt match the current files exactly:

```text
3f0543741adf74fbf923177afb36d31367f87e6161b09666b618aff6a1a8d7b8  music cross0
98679a583581a3b0e0b843dfec0058813273d38155d1acfb7192b8318ed22e27  music cross40
c68bcb38665bbe9f6b80fd16dc381c0266da51a8668fe49e69de9852cc4f19fa  music cross80
fc4be9874ce8b4b95ddf89f948be831d81b0681f7e6f6c66be458838fccfdecb  no-playback cross0
29a440f0ba8ac702212fbdc901453d36737eed7ab2b6749897f5ce1c84c4aafa  no-playback cross40
046a6d57cecf403a4cf875d0904fefcc0a7fe695894af030c9329b796ed85609  no-playback cross80
```

The referenced `Anchor Point` file independently hashes to `02925982cf3900d1925fa0338db8e26432c265f7ca18ee93a06818dd4079a938`, matching all three music raw headers and summaries. No-playback raw headers show `track=<none>`, `player=<disabled>` and `playback_cmd=<disabled>`; this supports “host launched no player,” not acoustic silence. All six serial identities are B489A500 / `B4:3A:45:A5:89:B4` on the explicitly recorded port.

## Captain and restored-state authority

The following authority is from the orchestrator's live turn/tool transcript, not from the six committed capture files:

- Audible-fixture answer: `Yes, audible (Recommended)` to “Can you hear ‘Anchor Point’ clearly through the MacBook Pro speakers at a suitable level for the K1 microphone?”
- Product verdict: Captain said he could not tell a meaningful difference among all three over insignificant sequential 20-second runs on one unit, required at least two simultaneous differently flashed units across multiple tracks for roughly 30–60 minutes, and explicitly ordered: `Mark this test as inconclusive.`
- Post-restore readback: `BUILD: version=40103 git=35de4e53 epoch=1786777774 env=k1_bench_scheduling_baseline_probe`.

The last on-disk capture is also cross0 by timestamp, but the exact post-restore build/env statement has transcript provenance only; no separate restoration log currently exists on disk. This is enough to preserve the operational state in the active turn, but a durable receipt should embed that readback before later promotion.

## Upload transport review

Current `platformio.ini:919-950` sets `upload_speed = 460800` on the scalar baseline, and both crossover candidates inherit it. `pio project config --json-output` resolves 460800 for all three environments. `upload_speed` changes the host flashing transport only; it does not add or alter a firmware define, task, priority, cadence, DSP formula or runtime telemetry path. The matrix test now locks this value and still requires exact baseline-plus-one candidate flags (`tests/test_scheduling_gdft_service_matrix.py:89-131`).

The reported 921600 final-ACK incident and four later successful guarded uploads are orchestrator/runtime provenance; the six cadence logs are post-boot serial captures and do not themselves prove the upload transactions.

## Final gate status

```text
DEVICE_IDENTITY                   = PASS
SERVICE_TABLE_ARITHMETIC          = PASS_ON_EXPORTED_ROWS
COMPLETE_15S_CAPTURE_MATRIX       = FAIL
GDFT_ONLY_TAIL_MARGIN             = FAIL_ALL_CANDIDATES
SEQUENTIAL_PRODUCT_COMPARISON     = INCONCLUSIVE_BY_CAPTAIN
FULL_SEMANTIC_ACCEPTANCE          = NOT_VERIFIED
GATE2_SELECTION                   = BLOCKED_OPEN
GATE3_ENTRY                       = BLOCKED_BY_GATE2
BENCH_FINAL_STATE                 = CROSS0_BASELINE_RESTORED_TRANSCRIPT_PROOF
```

This is the safe status. Gate 2 requires sustainable service, bounded freshness and the pre-registered real-music product comparison (`EXECUTION_PLAN.md:377-390`). None is eligible for promotion: all fail the compute tail, the dumps are incomplete, and Captain rejected the perceptual procedure. Gate 3 explicitly depends on Gate 2 (`EXECUTION_PLAN.md:392-394`), so proceeding would violate the gate DAG. Keep cross0 as the unchanged operational baseline while Gate 2 is open; do not promote cross40/cross80, change priority, enlarge the hop, or begin Gate 3.

## Commands and validation

```bash
shasum -a 256 build/audio-semantic-metrics/device-ap-cadence-capture/gate2_*__summary.json
shasum -a 256 build/audio-semantic-metrics/device-ap-cadence-capture/gate2_*__apcad.log
shasum -a 256 build/audio-semantic-metrics/device-ap-cadence-capture/gate2_*__raw.log
shasum -a 256 "/Users/spectrasynq/Music/Music/Media.localized/Music/Ahmed Spins_Stevo Atambire/Anchor Point EP/Anchor Point.mp3"
pio project config --json-output
python3 -m pytest -q tests/test_scheduling_gdft_service_matrix.py tests/test_scheduling_ap_cadence_parser.py
# 10 passed in 1.27s
```

The arithmetic recomputation imported only the parser's pure read/summary functions and wrote no artefact. No build, upload, flash, serial/device action, source edit, receipt edit or git mutation was performed. This ignored independent-review file is the only write.

## Attempt 2 — corrected complete v3 audit

### Admission and arithmetic

I re-read the revised receipt and all six complete `gate2v3_*__apcad.log` files and
their six JSON summaries in full. I parsed every APCAD row with the checked-in parser,
recomputed the summaries from those rows, and compared every parser-derived field after
normal JSON serialisation. All recomputed fields match the saved summaries exactly.

| Fixture | Cross | Begin | Parsed rows | Done | Drops begin/done | AP Hz | Active median / p95 / p99 | >7.5 ms | GDFT median | Newest-to-publish p99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| no playback | 0 | 485 | 485 | 485 | 0 / 0 | 96.84 | 8,470 / 10,537.2 / 10,816.40 us | 485 | 7,134 us | 10,639.32 us |
| no playback | 40 | 667 | 667 | 667 | 0 / 0 | 133.33 | 5,445 / 7,644.7 / 7,941.12 us | 65 | 4,048 us | 7,873.82 us |
| no playback | 80 | 667 | 667 | 667 | 0 / 0 | 133.33 | 5,083 / 7,316.7 / 7,571.46 us | 10 | 3,693 us | 7,497.82 us |
| real music | 0 | 465 | 465 | 465 | 0 / 0 | 92.86 | 9,375 / 11,425.4 / 11,820.04 us | 465 | 7,174 us | 11,736.68 us |
| real music | 40 | 640 | 640 | 640 | 0 / 0 | 127.85 | 6,430.5 / 8,534 / 8,721.05 us | 162 | 4,094.5 us | 8,655.32 us |
| real music | 80 | 664 | 664 | 664 | 0 / 0 | 132.68 | 6,048 / 8,040.45 / 8,421.66 us | 134 | 3,778 us | 8,351.92 us |

Every v3 summary has `capture_complete=true` and `capture_admissible=true`. Every
recomputed capture has zero frame gaps, capture-sequence gaps, timestamp regressions,
timestamp-order failures, I2S failures and byte-count failures. All timestamped rows use
assumption ID 1. The effective tuple in every row is 12,800 Hz / 96 samples / DMA d3 x
96 / AP0 / VP1. The no-playback summaries record no player or track; the music
summaries record `afplay` and the expected track hash. All six identities are B489A500 /
`B4:3A:45:A5:89:B4`.

### Contract decision

Gate 0 fixes the AP arrival period at 7,500 us and the p99 service ceiling at 80% of
arrival, exactly 6,000 us (`gate0/contract.json`, `production_tuple` and
`margin_rules`). Each of the six recomputed active-work p99 values is above 6,000 us.
Cross40 and cross80 recover average cadence but do not meet the tail margin. The v3
matrix is therefore a **complete negative witness for every candidate**, not evidence
to promote one. This agrees with `EXECUTION_PLAN.md:377-394`: retain the current
formula and reopen requirements when no candidate meets compute and product contracts;
Gate 3 depends on Gate 2.

### Hash verification

The revised receipt's twelve hashes match the live files exactly:

```text
8b20a030641ce673a8623db1dde6fabd2e73be80ea8d143a7adb7a66d129f58e  music cross0 APCAD
442cef829e529cec3782d96d3dd2cc2c2c36b1570f0d1746da88101dc672182c  music cross40 APCAD
854a67a7aa5097d2b44295d5c7f3d5ea68fa98020c7b625401a582932ee6fed0  music cross80 APCAD
804a105653073b4467d956b68eae28670bd5a80fe6cbad6a1241b36ddee7cd75  no-playback cross0 APCAD
c75862eff1649c658294bb3ec114c618c91a209c81195bdb7e2bfc0667fc1138  no-playback cross40 APCAD
1fc34b4c924c8f32bab45c9eb5e34b4abfa134d3806f74f0c9513a780c44f3c1  no-playback cross80 APCAD
088d8f725944776ac1ff4fbfbcbdc945233c525f6d6c04613af0d17450273297  music cross0 summary
23c5196046b9437dc33019693fb49354a3a654a11130eec4f8e9c3b200c84662  music cross40 summary
537b6a4f5db556f22ee9dacfe0161ccb9a49582136b403d5ff17f17296868c76  music cross80 summary
08313bb56615434854eee58756b2846b9ce8db27c1469ace648960d908baa71e  no-playback cross0 summary
1b57d91d349245c7133a13071ce7d9aeec4f7998c4af31d9ee64be91b226760c  no-playback cross40 summary
e2c561a50d3b2ebe9f6e4032b545435c84da19bf15bfbfed170b915b58a9bc7f  no-playback cross80 summary
```

The real-music fixture independently hashes to
`02925982cf3900d1925fa0338db8e26432c265f7ca18ee93a06818dd4079a938`,
matching all three music capture records.

### Restored baseline and Captain authority

The durable restoration artefact
`evidence/gate2-bench-restore-readback.log` hashes to
`3a7651282bcd5882cc1aad054f28381849bfb1d85580b301156c04bea2b3f93b`
and records the explicit port, B489A500 identity and running response:

```text
BUILD: version=40103 git=35de4e53 epoch=1786778678 env=k1_bench_scheduling_baseline_probe
```

This supersedes attempt 1's transcript-only restoration provenance. The Captain's
audibility confirmation and final product verdict remain orchestrator-turn authority,
not fields proven by the cadence files. The exact final boundary is that he could not
tell a meaningful difference among the three sequential 20-second builds on one unit,
required at least two simultaneously running differently flashed units, multiple tracks
and roughly 30–60 minutes, and ordered the test marked inconclusive. I therefore accept
the receipt's **inconclusive / not verified** product boundary; no candidate has earned a
semantic or perceptual win. Intermediate qualitative bullet labels in the receipt are
not needed for, and do not override, that final Captain-owned decision.

### Final verdict — ACCEPT

```text
CORRECTED_V3_CAPTURE_COMPLETENESS = PASS
SERVICE_TABLE_AND_HASHES          = PASS
GDFT_ONLY_TAIL_MARGIN             = FAIL_ALL_CANDIDATES
CAPTAIN_PRODUCT_COMPARISON        = INCONCLUSIVE
FULL_SEMANTIC_ACCEPTANCE          = NOT_VERIFIED
GATE2_SELECTION                   = BLOCKED_OPEN
GATE3_ENTRY                       = BLOCKED_BY_GATE2
BENCH_FINAL_STATE                 = CROSS0_BASELINE_RESTORED_ON_DISK
INDEPENDENT_RECEIPT_VERDICT       = ACCEPT
```

The prior rejection applied to the superseded incomplete v2 exports. The corrected v3
receipt fixes that defect and its blocked/open decision is source-supported. Acceptance
does not promote cross40 or cross80 and does not authorise Gate 3.

### Attempt-2 commands and validation

```bash
# Pure parser recomputation over gate2v3_*__apcad.log, compared to every saved summary field
python3 -B - <<'PY'
# import device_ap_cadence_capture.py; parse all six logs; summarise_rows(..., 12800, 96, 3)
# compare JSON-normalised parser fields and print completeness/integrity/tail checks
PY
shasum -a 256 build/audio-semantic-metrics/device-ap-cadence-capture/gate2v3_*__apcad.log \
  build/audio-semantic-metrics/device-ap-cadence-capture/gate2v3_*__summary.json \
  docs/forensics/2026-08-15-freertos-scheduling-audit/evidence/gate2-bench-restore-readback.log
shasum -a 256 "/Users/spectrasynq/Music/Music/Media.localized/Music/Ahmed Spins_Stevo Atambire/Anchor Point EP/Anchor Point.mp3"
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_scheduling_gdft_service_matrix.py tests/test_scheduling_ap_cadence_parser.py
# 12 passed in 1.30s
```

No build, upload, flash, serial/device or git action was performed. The independent
review file is the only file changed.
