# SSA Evidence: AP-DC-OLD-9EB3CEE

Task ID: AP-DC-OLD-9EB3CEE

Source tree inspected: `/private/tmp/sb-k1-rollback-9eb3cee-20260610`

Question: what do AP telemetry fields `SSL` and `DC` mean, how are they computed during/after noise calibration, and is a row like `NOISE CAL COMPLETE` followed by `[AP] SSL=391 DC=-984 max_raw=741 follower=8082 peak_scaled=0.092 silent_scale=1.000 silence=0 cal_source=measured cal_valid=1` evidence of broken DC offset or normal signed mic bias estimate in this old fork?

## Verdict

VERIFIED: in this old fork, that row is evidence of a valid measured calibration with a normal signed mic bias estimate, not evidence of a broken DC offset.

## Source Evidence

### AP field meanings

The AP telemetry line is printed in `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:445-449`:

`[AP] SSL=%u DC=%d max_raw=%.0f follower=%.0f peak_scaled=%.3f silent_scale=%.3f silence=%d cal_source=%s cal_valid=%d`

The printed values are:

| AP field | Source value | Citation |
| --- | --- | --- |
| `SSL` | `CONFIG.SWEET_SPOT_MIN_LEVEL` | `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:445-449` |
| `DC` | `(int)CONFIG.DC_OFFSET` | `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:445-449` |
| `max_raw` | `max_waveform_val_raw` | `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:445-449` |
| `follower` | `max_waveform_val_follower` | `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:445-449` |
| `peak_scaled` | `waveform_peak_scaled` | `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:445-449` |
| `silent_scale` | `silent_scale` | `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:445-449` |
| `silence` | `silence ? 1 : 0` | `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:445-449` |
| `cal_source` | `calibration_source_name()` | `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:445-449` |
| `cal_valid` | `calibration_valid ? 1 : 0` | `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:445-449` |

`serial_menu.h` prints the same lower-case AP/status meanings: `ssl` is `CONFIG.SWEET_SPOT_MIN_LEVEL`, and `dc` is `CONFIG.DC_OFFSET` (`/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:400-407`).

### Noise calibration computation

`start_noise_cal()` resets calibration state before measurement: `noise_complete = false`, `noise_iterations = 0`, `dc_offset_sum = 0`, `dc_offset_samples = 0`, `CONFIG.DC_OFFSET = 0`, and `CONFIG.SWEET_SPOT_MIN_LEVEL = 0` (`/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h:1-11`).

Each chunk first converts raw I2S data into `sample`, clips it, and computes `waveform[i] = sample - CONFIG.DC_OFFSET` (`/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:165-177`). It then tracks `max_waveform_val_raw` from `abs(waveform[i])`; the local comment explicitly says this is AC-corrected peak tracking, not DC-biased peak tracking (`/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:182-190`).

During noise calibration, the old fork uses a two-phase calibration:

| Phase | Iterations | Computation | Citation |
| --- | --- | --- | --- |
| A | `< 128` | If `abs(waveform[0]) <= SAMPLE_RAIL_THRESHOLD`, add `waveform[0]` into `dc_offset_sum` and increment `dc_offset_samples`. | `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:225-236` |
| Stamp DC | `== 128` | If valid samples exist, set `CONFIG.DC_OFFSET = dc_offset_sum / dc_offset_samples`; otherwise refuse to update. | `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:237-249` |
| B | `129..240` | Set `CONFIG.SWEET_SPOT_MIN_LEVEL` to the maximum observed `max_waveform_val_raw * 1.10`; comment says this is AC-domain SSL. | `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:251-256` |
| Complete | `>= 256` | Mark `noise_complete = true`, print `NOISE CAL COMPLETE`, and persist calibration/config/profile. | `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h:143-167` |

The fork's own explanatory comment states the intended domain explicitly: DC is stamped at iter 128; SSL is sampled after DC is established from AC-corrected `max_waveform_val_raw`; at iter 256 both values are already correctly stamped and no further correction is needed (`/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:211-224`). `GDFT.h` repeats that no post-hoc subtraction of `DC_OFFSET` from SSL should occur because it would double-correct (`/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h:148-152`).

### Validity and signed DC interpretation

`CONFIG.DC_OFFSET` is an `int32_t`, while `CONFIG.SWEET_SPOT_MIN_LEVEL` is a `uint32_t` (`/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:155-157`). Persistence writes and reads `dc_offset` as `int32_t`, and writes/reads `sweet_spot_min` as `uint32_t` (`/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:241-253`, `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:296-309`, `/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:329-343`).

The old fork considers a calibration valid when `noise_complete == true`, `CONFIG.DC_OFFSET != 0`, `abs(CONFIG.DC_OFFSET) <= 30000`, `CONFIG.SWEET_SPOT_MIN_LEVEL > 0`, and `CONFIG.SWEET_SPOT_MIN_LEVEL <= 3000` (`/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/system/globals.h:158-163`). The AP row's `DC=-984` is non-zero and has absolute value 984, far below the invalid threshold of 30000; `SSL=391` is above zero and below 3000. The row's own `cal_valid=1` is printed from `calibration_valid` (`/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:445-449`).

The boot guard describes real SPH0645 mic bias in these post-extraction units as signed, with examples of negative bias values (`S2 = -8102`, `K1 = -4710`), and only rejects `CONFIG.DC_OFFSET == 0` or `abs(CONFIG.DC_OFFSET) > 30000` (`/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/system/system.h:361-398`). That directly refutes the idea that a negative `DC` value is inherently broken in this fork.

`cal_source=measured` is also internally consistent: `CAL_SOURCE_MEASURED` maps to string `"measured"` (`/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/system/globals.h:166-173`), and calibration completion calls `save_calibration_profile(CAL_SOURCE_MEASURED)` (`/private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h:165-167`).

## Conclusion

The sample row is not evidence of a broken DC offset in `/private/tmp/sb-k1-rollback-9eb3cee-20260610`. In that fork, `DC=-984` is a normal signed mic bias estimate computed as the average of valid Phase-A post-extraction silence samples, then used to AC-correct subsequent waveform samples. `SSL=391` is the AC-domain sweet-spot/silence floor learned later in Phase B from `max_waveform_val_raw * 1.10`. The row satisfies the old fork's validity predicate and reports `cal_source=measured cal_valid=1`, so the source-backed classification is normal measured calibration, not broken DC.

## Re-run Commands

```sh
nl -ba /private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '165,190p;208,256p;438,452p'
nl -ba /private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h | sed -n '143,167p'
nl -ba /private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h | sed -n '1,19p'
nl -ba /private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/system/globals.h | sed -n '158,183p'
nl -ba /private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/system/system.h | sed -n '361,398p'
nl -ba /private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h | sed -n '241,253p;296,309p;329,343p'
nl -ba /private/tmp/sb-k1-rollback-9eb3cee-20260610/SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '400,407p'
```
