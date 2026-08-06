# SCS-MEM-01 Memory Evidence

## Verdict

Status: CONTRADICTORY / NOT_VERIFIED for the exact remembered phrase.

No claude-mem observation matched exact `self calibrating sensitivity` or `self-calibrating` in either `SensoryBridge-main 9` or `SpectraSynq_K1_Firmware`. The closest fetched observations instead describe:

- persisted noise/calibration profiles;
- runtime/manual `CONFIG.SENSITIVITY` adjustment;
- a Waveform-Fast SSL-proportional gate that changes visual duty cycle/selectivity;
- an IM73D gain/sensitivity stacking hazard;
- a bench-only quiet-music duty trim.

Treating any of these as an implemented "self-calibrating sensitivity function" would launder adjacent calibration/AGC/gating history into a stronger claim than the observations support.

## Search Log

Projects searched:

- `SensoryBridge-main 9`
- `SpectraSynq_K1_Firmware`

Minimum required terms searched in both projects:

- `self calibrating sensitivity`
- `self-calibrating`
- `sensitivity`
- `CONFIG.SENSITIVITY`
- `persisted_profile`
- `snappiness`
- `Waveform-Fast`
- `start_noise_cal`

Exact-phrase refutation:

- `self calibrating sensitivity`: no results in both project filters.
- `self-calibrating`: no results in both project filters.

## Fetched Observations

| ID | Project | Why fetched | What it actually claims | Confidence |
|---:|---|---|---|---|
| 54509 | `SensoryBridge-main 9` | `sensitivity`, `CONFIG.SENSITIVITY`, `start_noise_cal` | `sensitivity=[float]` is a runtime serial command that adjusts `CONFIG.SENSITIVITY` and delayed-saves config; `start_noise_cal` is a calibration trigger that must not be auto-fired. This is manual control, not self-calibration. | High |
| 56818 | `SensoryBridge-main 9` | `persisted_profile` | Calibration profile state machine restores `DC_OFFSET`, `SWEET_SPOT_MIN_LEVEL`, optional max level, and noise samples from persisted profile; explicitly says no silent self-healing or auto-recalibration occurs. | High |
| 73493 | `SpectraSynq_K1_Firmware` | `CONFIG.SENSITIVITY`, `sensitivity` | IM73D input gain placement would double-apply gain with `CONFIG.SENSITIVITY=2.4`; this is a defect/risk analysis, not a feature. | High |
| 73656 | `SpectraSynq_K1_Firmware` | `start_noise_cal` | During `start_noise_cal`, `SSL=0` is safe because calibration branch does not read SSL for drive math; calibration stamps SSL only after validity gates. Ordinary noise calibration proof. | High |
| 74062 | `SpectraSynq_K1_Firmware` | `persisted_profile` | PDM calibration persistence proven: cold boot loads `/cal_profile_pdm.bin` with `cal_source=persisted_profile`, `cal_valid=1`, no re-cal per boot. Persistence, not self-adjusting sensitivity. | High |
| 74069 | `SpectraSynq_K1_Firmware` | `Waveform-Fast`, `snappiness` | Waveform-Fast uses an SSL-proportional reactive gate; IM73D floor-to-signal ratio makes quiet passages less reactive than SPH. VP-side selectivity, not sensitivity self-calibration. | High |
| 74077 | `SpectraSynq_K1_Firmware` | `Waveform-Fast`, `snappiness` | Waveform-Fast smoother is dead code for drive; SSL gate is instantaneous duty-cycle/selectivity, not latency or adaptive sensitivity. | High |
| 74080 | `SpectraSynq_K1_Firmware` | `snappiness`, `Waveform-Fast` | Snappiness synthesis attributes observed behaviour to calibrated floor position plus front-end dynamics; actionable lever is IM73D input-gain retune. It warns fair A/B needs measured SPH calibration. | High |
| 75178 | `SpectraSynq_K1_Firmware` | `Waveform-Fast`, `persisted_profile` | Bench K1 quiet-music duty trim deployed by tightening PDM-gated AGC margin `1.10 -> 0.95`; device re-run matched prediction and persisted cal survived app reflash. Tuning/deployment, not self-calibration. | High |

## Most Direct Match

The closest match to Captain's vague memory is the July 3-5 IM73D/Waveform-Fast cluster:

- #74069 and #74077: SSL-proportional Waveform-Fast gate changes visual duty cycle/selectivity by calibrated floor position.
- #74080: synthesis says perceived snappiness is real but comes from floor position and front-end dynamics, not AP drive speed.
- #75178: later bench trim changed the PDM-gated margin and verified expected duty-cycle change.

These collectively claim a calibrated-floor-driven visual response and a manual/tuned threshold adjustment. They do not claim an autonomous "self-calibrating sensitivity function".

## Re-run Commands / Tool Calls

claude-mem MCP calls cannot be re-run as shell commands from this environment, so the exact tool calls are:

```text
mcp__claude_mem.search({"query":"self calibrating sensitivity","limit":10,"project":"SensoryBridge-main 9","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"self calibrating sensitivity","limit":10,"project":"SpectraSynq_K1_Firmware","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"self-calibrating","limit":10,"project":"SensoryBridge-main 9","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"self-calibrating","limit":10,"project":"SpectraSynq_K1_Firmware","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"sensitivity","limit":12,"project":"SensoryBridge-main 9","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"sensitivity","limit":12,"project":"SpectraSynq_K1_Firmware","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"CONFIG.SENSITIVITY","limit":12,"project":"SensoryBridge-main 9","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"CONFIG.SENSITIVITY","limit":12,"project":"SpectraSynq_K1_Firmware","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"persisted_profile","limit":12,"project":"SensoryBridge-main 9","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"persisted_profile","limit":12,"project":"SpectraSynq_K1_Firmware","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"snappiness","limit":12,"project":"SensoryBridge-main 9","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"snappiness","limit":12,"project":"SpectraSynq_K1_Firmware","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"Waveform-Fast","limit":12,"project":"SensoryBridge-main 9","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"Waveform-Fast","limit":12,"project":"SpectraSynq_K1_Firmware","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"start_noise_cal","limit":12,"project":"SensoryBridge-main 9","type":"observations","orderBy":"relevance"})
mcp__claude_mem.search({"query":"start_noise_cal","limit":12,"project":"SpectraSynq_K1_Firmware","type":"observations","orderBy":"relevance"})
mcp__claude_mem.timeline({"anchor":74080,"depth_before":4,"depth_after":4,"project":"SpectraSynq_K1_Firmware"})
mcp__claude_mem.timeline({"anchor":56818,"depth_before":3,"depth_after":3,"project":"SensoryBridge-main 9"})
mcp__claude_mem.timeline({"anchor":74069,"depth_before":3,"depth_after":4,"project":"SpectraSynq_K1_Firmware"})
mcp__claude_mem.timeline({"anchor":74062,"depth_before":3,"depth_after":3,"project":"SpectraSynq_K1_Firmware"})
mcp__claude_mem.timeline({"anchor":75178,"depth_before":3,"depth_after":3,"project":"SpectraSynq_K1_Firmware"})
mcp__claude_mem.timeline({"anchor":73656,"depth_before":3,"depth_after":3,"project":"SpectraSynq_K1_Firmware"})
mcp__claude_mem.get_observations({"ids":[56818,54509,73656,74062,74069,74077,74080,73493,75178],"orderBy":"date_asc","limit":20})
```

## Blockers / Caveats

- This is claude-mem evidence, not current-source verification.
- No observation fetched claims an implemented autonomous sensitivity loop.
- Ordinary noise calibration, persisted calibration, AGC margin tuning, and `CONFIG.SENSITIVITY` serial control must remain separate categories.
