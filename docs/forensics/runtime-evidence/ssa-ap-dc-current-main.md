# SSA AP/DC Current Main Evidence

Task ID: `AP-DC-CURRENT-MAIN`

Verdict: `VERIFIED` for current-checkout source safeguards. Runtime-on-device behaviour is `NOT_VERIFIED`; no serial ports were opened and no firmware was flashed.

Current checkout: `2abf493` from `git rev-parse --short HEAD`. Existing unrelated untracked runtime-evidence logs were present before this artefact.

## Scope Boundary

- Source-only inspection of `/Users/spectrasynq/SensoryBridge-main 9`.
- No claim is made that current-main behaviour is running on `12201`.
- The AGENTS reference docs `firmware-v3/docs/reference/codebase-map.md` and `firmware-v3/docs/reference/fsm-reference.md` are absent in this checkout; `docs/spec-index.md`, `.claude/CLAUDE.md`, `.claude/handoff.md`, protocol contracts, and active firmware source were used.

## Safeguards Found

| Area | Current source evidence | Behaviour established by source |
|---|---|---|
| DC offset boot guard | `SPECTRASYNQ_K1_FIRMWARE/system/system.h:396-433` | Boot rejects `CONFIG.DC_OFFSET == 0` and `abs(CONFIG.DC_OFFSET) > 30000`, prints a warning, and uses `0` for the boot without saving the override. |
| SSL / broken calibration guard | `SPECTRASYNQ_K1_FIRMWARE/system/system.h:436-458` | If `SWEET_SPOT_MIN_LEVEL > 3000`, it resets SSL to default, disables `STANDBY_DIMMING`, clears `noise_samples[]`, then persists config/noise calibration. |
| Calibration validity predicate | `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:158-164` | A profile is valid only when noise calibration is complete, DC offset is nonzero and within `30000`, and SSL is in `(0, 3000]`. |
| Calibration provenance state | `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:142-183` | Current source tracks `CAL_SOURCE_*`, `calibration_valid`, `calibration_profile_loaded`, and derives source name/status from the validity predicate. |
| Sample extraction and DC-domain peak | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:203-228` | Samples are clipped to +/-32767, waveform is `sample - CONFIG.DC_OFFSET`, and `max_waveform_val_raw` is measured from AC-corrected `waveform[i]`, not DC-biased raw sample. |
| Rail rejection during DC calibration | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:80`, `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:263-287`, `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:122-123` | Phase-A DC calibration ignores samples above `SAMPLE_RAIL_THRESHOLD` (`32000`), counts only valid samples, divides by valid count, and refuses to update DC offset if all samples were rail-pinned. |
| Single-domain SSL phase | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:249-294`, `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h:145-167` | DC is learned first, SSL is sampled later from AC-corrected `max_waveform_val_raw`, and calibration completion saves noise, config, and `/cal_profile.bin` as measured. |
| Noise-cal entry reset | `SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h:1-18` | Starting calibration resets peak state, `noise_iterations`, `dc_offset_sum`, valid-sample counter, `CONFIG.DC_OFFSET`, SSL, and calibration validity before collecting. |
| Noise-cal command arm path | `SPECTRASYNQ_K1_FIRMWARE/control/sb_noise_cal_arm.cpp:19-40`, `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:1778-1790`, `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def:40-45` | `N` only arms, `Y` only queues if the 5s arm window is active, and typed `start_noise_cal` is classified `SC_ARM_REQUIRED` rather than an immediate calibration trigger. |
| Typed command safety invariant | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2417-2471` | Static assertions reject destructive/calibration table rows that carry single-byte hotkeys; typed arm-required commands print guidance rather than firing directly. |
| Wireless control noise-cal guard | `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:447-450`, `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:471-475`, `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:1018-1042` | WS control exposes arm/confirm/status/clear, rejects `calibration.noise.start` / `start_noise_cal`, and requires `CONFIRM` text for clear. |
| Version-independent calibration profile | `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:11-13`, `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:224-273`, `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:275-345`, `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:348-367` | `/cal_profile.bin` has magic/version metadata, saves only valid profiles, seeds from valid config when profile is absent, loads profile when config is invalid, and clears profile explicitly. |
| VPAB invalid-calibration refusal | `SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.cpp:669-683` | VPAB refreshes calibration status and returns before `diag_capture_reset()` / `diag_capture_start()` if `calibration_profile_valid()` is false. |
| AP telemetry provenance | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:470-493`, `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:541-550`, `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:4685-4700` | AP stream, APCAP, and cadence telemetry expose DC, max_raw, follower, peak_scaled, silence, `cal_source`, and/or `cal_valid`. |
| AP capture placement/gating | `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:229-244`, `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:529-531`, `platformio.ini:132-145`, `platformio.ini:210-225` | APCAP storage exists only under `ENABLE_AP_STREAM`; the loop samples AP capture after GDFT; harness/probe envs enable AP stream and mark AP front-end probe non-shippable/default-off. |
| Status surfaces | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:331-341`, `SPECTRASYNQ_K1_FIRMWARE/diag/diagnostic_capture.cpp:240-245`, `SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.cpp:803-808` | Serial dump, diagnostic status, and VPAB status print DC/provenance validity/profile-loaded fields. |
| Static tests for these contracts | `tests/test_calibration_profile_static.py:38-89`, `tests/test_serial_hotkeys_static.py:52-86` | Host static tests assert profile load/save/provenance/VPAB refusal and assert noise-cal hotkeys are arm/confirm guarded. |

## Candidate Old-vs-Current Deltas

These are source-backed current-main fixes that may not exist in old `9eb3cee`; this pass did not read the old tree, so absence in `9eb3cee` remains `NOT_VERIFIED`.

- Current source marks the single-domain calibration fix dated 2026-05-20: AC-corrected peak tracking in `i2s_audio.h:220-228`, two-phase DC/SSL collection in `i2s_audio.h:249-294`, and removed post-hoc SSL correction in `GDFT.h:148-167`.
- Current source marks Fix-D dated 2026-05-24: boot DC sanity clamp in `system.h:396-433`, rail-rejected DC accumulator in `i2s_audio.h:263-287`, and valid-sample counter state in `globals.h:122-123`.
- Current source contains `/cal_profile.bin` version-independent persistence and bootstrap in `bridge_fs.h:11-13` and `bridge_fs.h:224-367`.
- Current source contains provenance/validity telemetry fields across serial/AP/VPAB surfaces: `globals.h:142-183`, `i2s_audio.h:470-493`, `i2s_audio.h:541-550`, `diag/vpab_capture.cpp:523-526`, and `serial_menu.h:331-341`.
- Current source contains guarded noise-cal command surfaces: `serial_cmd_table.def:40-45`, `serial_menu.h:1778-1790`, `serial_menu.h:2417-2471`, `sb_noise_cal_arm.cpp:19-40`, and WS control rejection/arm-confirm paths in `sb_k1_control_facade.cpp:471-475` and `sb_k1_control_facade.cpp:1018-1042`.
- Current source contains VPAB invalid-calibration refusal before capture allocation/start in `diag/vpab_capture.cpp:669-683`.

## Required Re-run Command

```bash
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '76,88p;203,294p;470,555p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/system.h | sed -n '396,459p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals.h | sed -n '122,187p;229,244p;350,354p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h | sed -n '1,30p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_noise_cal_arm.cpp | sed -n '19,49p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '447,475p;1018,1042p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def | sed -n '40,45p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '331,341p;1778,1790p;2417,2471p;4685,4700p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h | sed -n '11,13p;224,367p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h | sed -n '145,167p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.cpp | sed -n '523,526p;669,683p;803,808p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/diag/diagnostic_capture.cpp | sed -n '240,245p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino | sed -n '529,531p'
nl -ba platformio.ini | sed -n '132,145p;210,225p'
nl -ba tests/test_calibration_profile_static.py | sed -n '38,89p'
nl -ba tests/test_serial_hotkeys_static.py | sed -n '52,86p'
```
