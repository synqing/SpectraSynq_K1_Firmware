#!/usr/bin/env bash
# Tight wrapper around `pio run -e <env>` for agent use.
# Accepts exactly one env argument and rejects any dangerous token.
# This wrapper exists because Devin `Exec(pio run -e ...)` permissions are
# prefix-based and can match appended arguments.
#
# Defense in depth: the allowlist grep below already rejects any argument
# that is not exactly one of the declared allowed env names. The dangerous-token
# scan is a second layer in case the allowlist logic is ever loosened.

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "ERROR: exactly one env argument required" >&2
  exit 1
fi

ENV="$1"

# Primary gate: exact-match allowlist. grep -w matches whole words only,
# so any argument with appended flags/spaces is rejected here.
# k1_sync_probe_{main,main_sync_only,bench} = dual-K1 sync Phase-0 probes (historical).
# k1_bench_im73d_ble = standing Captain "bench K1 firmware" (registry 2026-07-06).
# k1_bench_im69d_ble = Deck16 P0 radio baseline on the active IM69D bench base.
# k1_custom = dual-206 custom strip length (K1_CUSTOM_LED_V1); non-shippable.
# k1_bench_scheduling_stage_{min,full}_probe = non-shippable B489 Gate-2
# measurement envs (identity still enforced by k1_upload_guard.py; this wrapper
# builds only — never upload).
# k1_bench_scheduling_gdft_cross40_lane4_full_probe = non-shippable combined
# Cross40 × Lane-4 exact backend with full stage attribution (B489 only).
# k1_bench_scheduling_gdft_cross40_lane4_tempo_inc_full_probe = same surface plus
# exact rolling ACF residual candidate (B489 only).
# k1_bench_im69d_wfhyb_fade = waveform-hybrid colour-novelty A/B (mode-11 trail
# deposit + mode-32 variant pack 33-37); non-shippable, B489 only, build-only here.
# k1_main_rpl_i2sled_probe = direct Yves LCD_CAM LED emit eval (Captain GO
# 2026-08-20); non-shippable, 9087A500 only. Bench i2sled env deleted.
# k1_main_rpl_rtrace_probe = Lever-2 packed-u16 rtrace occupancy (build-only
# here; flash only after named Captain GO). 9087A500 only. Never ship.
ALLOWED_ENVS="k1_hardware k1_bench_reference k1_bench_im73d k1_bench_im73d_mic_auto_telemetry k1_bench_im73d_dsr16 k1_bench_im69d k1_bench_im69d_ble k1_bench_im73d_ble k1_custom k1_sync_probe_main k1_sync_probe_main_sync_only k1_sync_probe_bench k1_bench_scheduling_stage_min_probe k1_bench_scheduling_stage_full_probe k1_bench_scheduling_gdft_cross40_lane4_full_probe k1_bench_scheduling_gdft_cross40_lane4_tempo_inc_full_probe k1_bench_im69d_wfhyb_fade k1_main_rpl_im69d k1_main_rpl_i2sled_probe k1_main_rpl_rtrace_probe k1_usb_audio_mac_probe"
case "$ENV" in
  k1_hardware|k1_bench_reference|k1_bench_im73d|k1_bench_im73d_mic_auto_telemetry|k1_bench_im73d_dsr16|k1_bench_im69d|k1_bench_im69d_ble|k1_bench_im73d_ble|k1_custom|k1_sync_probe_main|k1_sync_probe_main_sync_only|k1_sync_probe_bench|k1_bench_scheduling_stage_min_probe|k1_bench_scheduling_stage_full_probe|k1_bench_scheduling_gdft_cross40_lane4_full_probe|k1_bench_im69d_wfhyb_fade|k1_main_rpl_im69d|k1_main_rpl_i2sled_probe|k1_main_rpl_rtrace_probe|k1_usb_audio_mac_probe|k1_bench_scheduling_gdft_cross40_lane4_tempo_inc_full_probe)
    : ;;
  *)
    echo "ERROR: env '$ENV' is not in allowed list: $ALLOWED_ENVS" >&2
    exit 1
    ;;
esac

# Secondary gate: reject dangerous tokens even if the allowlist is loosened.
if [[ "$ENV" == *"upload"* ]] || \
   [[ "$ENV" == *"--target"* ]] || \
   [[ "$ENV" == *"-t"* ]] || \
   [[ "$ENV" == *"erase"* ]] || \
   [[ "$ENV" == *"monitor"* ]] || \
   [[ "$ENV" == *"device"* ]] || \
   [[ "$ENV" == *";"* ]] || \
   [[ "$ENV" == *"|"* ]] || \
   [[ "$ENV" == *"&"* ]] || \
   [[ "$ENV" == *'`'* ]] || \
   [[ "$ENV" == *'$('* ]] || \
   [[ "$ENV" == *'${'* ]] || \
   [[ "$ENV" == *'<'* ]] || \
   [[ "$ENV" == *'>'* ]] || \
   [[ "$ENV" == *$'\n'* ]]; then
  echo "ERROR: env argument contains forbidden token" >&2
  exit 1
fi

# Execute the narrowly-scoped build command only.
exec pio run -e "$ENV"
