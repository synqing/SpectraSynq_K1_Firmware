# G0R cadence-authority inventory

Date: 2026-08-16  
Pin context: harness `H=14c53d239524aa891e71470880f6917d4adf2ea6`, receipt `R=6b48c51ece1a56c4bb99765fccc9f60a6e557dd1`  
Scope: classify every on-disk “10 ms” / “100 Hz” hit that could bind product cadence. **No contract mutation.**

## Frozen deployed contract (authority until Captain stamps otherwise)

```text
path: docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/contract.json
sha256: d17aa7c66b05281b79bafed2178f40f823ce92c04463b920d51fae63df919849
contract_id: K1_SCHEDULING_GATE0_2026_08_15
sample_rate_hz: 12800
samples_per_chunk: 96
tempo_novelty_decimation: 3
ap_arrival_period_us: 7500
ap_service_p99_max_fraction_of_arrival: 0.8  ⇒ 6000 µs
vp_target_fps: 120
```

Hop vs analysis window (must not be conflated):

```text
hop_n = CONFIG.SAMPLES_PER_CHUNK  (AP emit cadence)
spectral_window_n = per-bin frequencies[i].block_size  (GDFT analysis length)
source: SPECTRASYNQ_K1_FIRMWARE/audio/k1_spectral_honesty.h
```

## Current execution-rate facts (source, not memory)

Verified in tree at inventory time:

| Rate surface | Approx value @ 12800/96/d3 | Source |
|---|---|---|
| AP acquisition / loop | 133.333 Hz | `DEFAULT_SAMPLE_RATE/DEFAULT_SAMPLES_PER_CHUNK` |
| `process_GDFT()` | once per AP iteration | `SPECTRASYNQ_K1_FIRMWARE.ino` |
| `calculate_novelty()` | once per AP iteration | same |
| onset / semantic snapshot | once per AP iteration | same |
| Tempo novelty ingest / heavy ACF/PLL | 44.444 Hz | `K1_NOVELTY_DECIMATION` every 3rd AP frame in `k1_tempo.cpp` |
| Tempo publication | every AP call path: heavy emit at 44.444 Hz; on non-emit frames under `K1_TEMPO_FLYWHEEL_V2`, may republish with `beat_tick` forced false | `k1_tempo.cpp` ~1368–1382 |

Therefore `NOVELTY_UPDATE_RATE_HZ = 44.444` as a single field is **ambiguous** and must not be used as the sole novelty contract field.

## Git history for contract-setting commits

```text
contract.json samples_per_chunk:
  19047912 test: qualify K1 scheduling Gate 0 oracle
  ed56dfb5 chore(fork): initial SpectraSynq K1 firmware

config_types.h DEFAULT_SAMPLES_PER_CHUNK:
  (no recent product hop change in this search; production remains 96)
```

## Inventory hits

### HIT-001 — Deployed Gate 0 production tuple

```text
hit_id: HIT-001
path: docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/contract.json
sha_or_date: d17aa7c66b… / Gate 0 close 68c9a51e lineage
verbatim_quote: "sample_rate_hz": 12800, "samples_per_chunk": 96, "tempo_novelty_decimation": 3, "ap_arrival_period_us": 7500
surface_class: I2S_DMA_HOP | AP_SEMANTIC_PERIOD
product_vs_probe: PRODUCT_DECISION
binds_sample_rate: yes
binds_chunk_samples: yes
binds_tempo_decimation: yes
captain_speech_act: APPROVED (via Gate 0 programme + FULL_UNRESTRICTED_SCHEDULING_IMPLEMENTATION_GO_2026-08-15 operating on this frozen contract)
admissible_as_g0r_authority: yes — currently controlling DEPLOYED_CONTRACT
```

### HIT-002 — June 2026 AP0/VP1 100 Hz probe candidates (explicitly not next move)

```text
hit_id: HIT-002
path: docs/forensics/tempo_tracking_refactor/2026-06-06-ap0-vp1-implementation-handover.md
sha_or_date: 2026-06-06 handover §7
verbatim_quote: "The 100 Hz maps passed click but are not the immediate next move" … "12.8k / 128 /2" AP 100.040 NOV 50.007; "16k / 160 /2" AP 100.027 NOV 50.003
surface_class: PROBE_CANDIDATE
product_vs_probe: PROBE_CANDIDATE
binds_sample_rate: yes (as probe map)
binds_chunk_samples: yes
binds_tempo_decimation: yes (/2)
captain_speech_act: CANDIDATE (click-pass) + explicit NON-promotion as immediate next move
admissible_as_g0r_authority: no — cannot silently replace HIT-001; may inform Captain stamp options B/C/E only after reissue
```

### HIT-003 — June APCAD matrix probe env names for 12800/128 and 16000/160

```text
hit_id: HIT-003
path: docs/forensics/tempo_tracking_refactor/2026-06-06-ap-cadence-probe-implementation.md
verbatim_quote: k1_ap_frontend_probe_matrix_12800_128_d2_ap0_vp1 "Budget-isolation test at 100 Hz AP"; k1_ap_frontend_probe_matrix_16000_160_d2_ap0_vp1 "100 Hz AP product-candidate timing map"
surface_class: PROBE_CANDIDATE
product_vs_probe: PROBE_CANDIDATE (label "product-candidate" is historical matrix prose, not Gate 0 freeze)
binds_sample_rate / chunk / tempo_decimation: yes as probe
captain_speech_act: UNSTATED as product hop approval
admissible_as_g0r_authority: no
```

### HIT-004 — IM69D cadence risk note for hypothetical 128/d2 ship

```text
hit_id: HIT-004
path: docs/forensics/im69d-bringup-2026-08-06/ssa2-cadence.md
verbatim_quote: "If the proposed 128/d2 (100 Hz, dt=10 ms) hop ever ships, these will silently retune" … K1V2_MEDIAN_WIN 14×10ms=140ms; EMA alphas derived for dt=7.5ms
surface_class: PROBE_CANDIDATE + ACTIVE_WORK_BUDGET risk note
product_vs_probe: PROBE_CANDIDATE / warning
captain_speech_act: UNSTATED (warns against silent retune)
admissible_as_g0r_authority: no for replacing 7.5 ms; yes as mandatory rebound requirement IF stamp B/C
```

### HIT-005 — Stashed / uncommitted 128/d2 promotion claims (negative witness)

```text
hit_id: HIT-005
path: docs/forensics/im69d-bringup-2026-08-06/FINDING-stashed-cadence.md
verbatim_quote: config_types at db300db compiles DEFAULT_SAMPLES_PER_CHUNK 96; 12800/128/d2 appears ONLY in isolated probe envs; stashed docs assert "Promoted the compiled AP tuple to 12800/128/d2" — contradicted by committed source
surface_class: PROBE_CANDIDATE / STALE_PROSE (stash claims)
product_vs_probe: UNCLEAR / REFUTED as committed product
captain_speech_act: REJECTED as product truth by the finding itself
admissible_as_g0r_authority: no — proves absence of committed 10 ms product hop
```

### HIT-006 — Stale VP 100 FPS / 10 ms frame prose

```text
hit_id: HIT-006
path: CLAUDE.md / AGENTS.md Core Timing
verbatim_quote: "Visual Render Rate: 100 FPS (10 ms per frame, soft real-time)"
surface_class: VP_FRAME_BUDGET | STALE_PROSE
product_vs_probe: STALE_PROSE vs Gate 0 VP_TARGET=120 FPS
binds_sample_rate/chunk/tempo: no
captain_speech_act: UNSTATED for AP hop
admissible_as_g0r_authority: no — must not be read as AP 100 Hz / 10 ms hop
```

### HIT-007 — Apparent-motion interval sweep (unrelated 5–10 ms steps)

```text
hit_id: HIT-007
path: docs/measurements/apparent-motion-on-k1.md
verbatim_quote: interval_ms swept (e.g. 5 → 120 in ~5–10 ms steps)
surface_class: UNKNOWN / perceptual stimulus
product_vs_probe: UNCLEAR
admissible_as_g0r_authority: no
```

### HIT-008 — Harness “100 Hz” serial subsample arithmetic (not AP hop)

```text
hit_id: HIT-008
path: docs/k1-refactor-2026-05/phase2-plan-agent-3-harness-design.md
verbatim_quote: 5 s × every-4th-frame × 100 Hz = 125 lines
surface_class: STALE_PROSE / diagnostic bandwidth estimate
admissible_as_g0r_authority: no
```

### HIT-009 — PRD note comparing 133 vs 100 Hz (verification item, not approval)

```text
hit_id: HIT-009
path: docs/prd/ve-auto-loop/03-effects-archaeology-synthesis-2026-06-04.md
verbatim_quote: confirm AP rate and tempo accuracy (133 vs 100Hz; 14 vs …
surface_class: PROBE_CANDIDATE / verification checklist
admissible_as_g0r_authority: no
```

### HIT-010 — Captain verbal “approved 10 ms” (this conversation)

```text
hit_id: HIT-010
path: Captain verdict 2026-08-16 (chat) — not yet an on-disk decision artefact
verbatim_quote: Captain states a prior personal approval of a 10 ms window, and simultaneously that available evidence does NOT identify whether it meant I2S hop, AP semantic period, DSP window, active-work budget, or other
surface_class: UNKNOWN (governance trigger)
product_vs_probe: UNCLEAR pending A–E stamp
captain_speech_act: APPROVED-as-governance-reconciliation-trigger; NOT yet a bound tuple
admissible_as_g0r_authority: triggers G0R; does NOT by itself replace HIT-001
```

### HIT-011 — Scheduling audit README / EXECUTION_PLAN 7.5 ms framing

```text
hit_id: HIT-011
path: docs/forensics/2026-08-15-freertos-scheduling-audit/EXECUTION_PLAN.md
verbatim_quote: Gate 2 must not hide deficit with a larger hop; 7.5 ms hop and long low-frequency windows are distinct
surface_class: AP_SEMANTIC_PERIOD + DSP_ANALYSIS_WINDOW distinction
product_vs_probe: PRODUCT_DECISION (programme law)
admissible_as_g0r_authority: yes for process; does not invent a 10 ms tuple
```

## Red-team rejects (must remain rejected)

| Attack | Result |
|---|---|
| Treat June click-pass 100 Hz maps as Captain product approval | REJECTED (HIT-002 explicitly not next move) |
| Treat VP 100 FPS / 10 ms prose as AP 100 Hz | REJECTED (HIT-006) |
| Treat GDFT ~152.8 ms low-bin window as hop | REJECTED (spectral honesty hop_n ≠ spectral_window_n) |
| Treat “sub-8 ms latency” as AP period | REJECTED (EXECUTION_PLAN: universal sub-8 ms unusable) |
| Infer 16 kHz/160 or 24 kHz/240 from “10 ms” | REJECTED (separate programmes; contract marks spectral_24k_180 out of scope) |
| Use stash prose that “promoted 12800/128/d2” | REJECTED (HIT-005) |

## Inventory conclusion for R3/R6

```text
STRONGEST_ON_DISK_PRODUCT_BINDING     = HIT-001 (7.5 ms / 96 / d3)
STRONGEST_ON_DISK_10MS_AP_HOP_HIT     = HIT-002/HIT-003 (PROBE_CANDIDATE only)
AUTHORITATIVE_10MS_PRODUCT_ARTEFACT   = NOT_FOUND
G0R_REQUIRED                          = YES (Captain verbal trigger HIT-010)
RECOMMENDED_CARD_LEAN                 = A unless Captain reissues B/C as product
```

No `gate0/contract.json` bytes were modified in this task.
