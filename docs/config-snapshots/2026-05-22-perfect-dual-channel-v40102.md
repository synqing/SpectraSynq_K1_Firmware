# Perfect Dual Channel Snapshot

Captured: 2026-05-22 19:56 AWST

Source: live serial output supplied by Captain from running firmware `40102`.

Critical handling:

- Do not reboot or upload before manually preserving these values somewhere outside runtime memory.
- The running device firmware is older than the current repo head because its `dump` still prints `CONFIG.IS_MAIN_UNIT`.
- `SECONDARY_BASE_COAT` is raw `true`, but it is not visually active while `VP_FIX_SECONDARY_CLEAN` is on.

## Primary Channel

```ini
FIRMWARE_VERSION=40102
CHIP_ID=763E7500

CONFIG.PHOTONS=0.200195
CONFIG.CHROMA=0.000000
CONFIG.MOOD=0.116638
CONFIG.LIGHTSHOW_MODE=3
CONFIG.MIRROR_ENABLED=1
CONFIG.CHROMAGRAM_RANGE=60
CONFIG.SAMPLE_RATE=12800
CONFIG.NOTE_OFFSET=12
CONFIG.SQUARE_ITER=1.00
CONFIG.LED_TYPE=0
CONFIG.LED_COUNT=160
CONFIG.LED_COLOR_ORDER=66
CONFIG.SAMPLES_PER_CHUNK=96
CONFIG.SENSITIVITY=2.400000
CONFIG.BOOT_ANIMATION=1
CONFIG.SWEET_SPOT_MIN_LEVEL=302
CONFIG.SWEET_SPOT_MAX_LEVEL=30000
CONFIG.DC_OFFSET=-8084
CONFIG.STANDBY_DIMMING=0
CONFIG.REVERSE_ORDER=0
CONFIG.IS_MAIN_UNIT=0
CONFIG.MAX_CURRENT_MA=1500
CONFIG.TEMPORAL_DITHERING=1
CONFIG.AUTO_COLOR_SHIFT=1
CONFIG.INCANDESCENT_FILTER=0.50
CONFIG.INCANDESCENT_MODE=0
CONFIG.BULB_OPACITY=0.13
CONFIG.SATURATION=1.00
CONFIG.PRISM_COUNT=6.00
CONFIG.BASE_COAT=0

MASTER_BRIGHTNESS=1.00
noise_complete=1
silence=0
SYSTEM_FPS=48.26
LED_FPS=115.86
```

## Secondary Channel

```ini
SECONDARY_ENABLED=true
SECONDARY_CONTROL=false
SECONDARY_MODE=7
SECONDARY_MODE_NAME=WAVEFORM-FAST
SECONDARY_PHOTONS=1.000000
SECONDARY_CHROMA=0.033325
SECONDARY_MOOD=0.216614
SECONDARY_SATURATION=1.000000
SECONDARY_PRISM_COUNT=2.00
SECONDARY_MIRROR_ENABLED=true
SECONDARY_REVERSE_ORDER=false
SECONDARY_BASE_COAT_RAW=true
SECONDARY_BASE_COAT_EFFECTIVE=false
SECONDARY_PALETTE_MODE_ENABLED=true
SECONDARY_PALETTE_INDEX=10
SECONDARY_PALETTE_NAME=es_vintage_01_gp
```

## Visual Pipeline

```ini
VP_PROFILE=candidate
VP_FIX_AGC_SOFT_KNEE=on
VP_FIX_CHROMAGRAM_SPARSENESS=on
VP_FIX_PRISM_DEFAULT_OFF=on
VP_FIX_BLOOM_DECAY=off
VP_FIX_HSV_SOURCE_SAT=on
VP_FIX_SECONDARY_CLEAN=on

VP_BLOOM_ALPHA=0.9900
VP_BLOOM_SHIFT=1.0000
VP_BLOOM_FORCE_SAT=on

VP_WAVEFORM_IDLE_FADE=0.9850
VP_WAVEFORM_RAW_MARGIN=1.1000
VP_WAVEFORM_PEAK_FLOOR=0.0800
VP_WAVEFORM_ACTIVE_FADE=0.0400
VP_WAVEFORM_BLEND_GAIN=2.0000
VP_WAVEFORM_FALLBACK=1.0000
VP_WAVEFORM_VU_FLOOR=0.0200
VP_WAVEFORM_SHIFT_RATE=120.0000

VP_CHROMA_SEQ=245221
VP_CHROMA_RANGE=60
VP_CHROMA_PRE_MAX=0.2869
VP_CHROMA_PRE_MEAN=0.1978
VP_CHROMA_NORM_MAX=0.8104
VP_CHROMA_NORM_MEAN=0.5587
VP_CHROMA_FLATNESS=0.2517
VP_CHROMA_FINAL_MAX=0.6100
VP_CHROMA_FINAL_MEAN=0.3949

VP_AGC_GAIN=0.2708
VP_AGC_ENVELOPE=0.8627
VP_AGC_FLOOR=0.0010
VP_AGC_GATED=false

VP_RENDER_US_LAST=1741
VP_RENDER_US_AVG=1911
VP_RENDER_US_MAX=8207
```

## Existing Serial Restore Commands

These are the commands supported by the current source for the values that have serial setters. They are not a complete restore path for primary knob values because primary `PHOTONS`, `CHROMA`, and `MOOD` are currently encoder-owned, not serial-settable in this source.

```text
set_mode=3
mirror_enabled=true
chromagram_range=60
sample_rate=12800
note_offset=12
square_iter=1
samples_per_chunk=96
sensitivity=2.4
boot_animation=true
sweet_spot_min=302
sweet_spot_max=30000
standby_dimming=false
reverse_order=false
max_current_ma=1500
temporal_dithering=true
auto_color_shift=true
incandescent_filter=0.50
incandescent_mode=false
bulb_opacity=0.13
saturation=1.00
prism_count=6
base_coat=false

secondary_enabled=true
secondary_mode=7
secondary_photons=1.000000
secondary_chroma=0.033325
secondary_mood=0.216614
secondary_saturation=1.000000
secondary_prism_count=2.00
secondary_mirror_enabled=true
secondary_reverse_order=false
secondary_base_coat=true
secondary_palette_mode=true
secondary_palette_index=10

vp_profile=candidate
vp_bloom_alpha=0.9900
vp_bloom_shift=1.0000
vp_bloom_force_sat=on
vp_wave_idle_fade=0.9850
vp_wave_raw_margin=1.1000
vp_wave_peak_floor=0.0800
vp_wave_active_fade=0.0400
vp_wave_blend_gain=2.0000
vp_wave_fallback=1.0000
vp_wave_vu_floor=0.0200
vp_wave_shift=120.0000
```

## Interpretation Notes

- `SECONDARY_BASE_COAT_RAW=true` came directly from `secondary_status`.
- `SECONDARY_BASE_COAT_EFFECTIVE=false` because `VP_PROFILE=candidate` sets `VP_FIX_SECONDARY_CLEAN=on`, and the current secondary output code applies base coat only when `SECONDARY_BASE_COAT && !VP_FIX_SECONDARY_CLEAN`.
- If `VP_FIX_SECONDARY_CLEAN` is turned off later, the secondary base coat may become visible. That would no longer be this exact look.
