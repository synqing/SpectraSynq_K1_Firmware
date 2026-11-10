# Prior art: how sound-reactive lighting and music visualisers handle input level

Scope: external prior art only (no SpectraSynq repository read). Research date 10 November 2026. Source code was read from the public repositories at their default branch on that date unless a tag is named. Time constants are computed from the per-frame coefficients in the code. For a one-pole follower `y += c·(x − y)` the time constant is about 1/c frames. The frame rates used are stated each time. Anything not confirmed is marked UNVERIFIED.

Conventions used below:
- **Short-max normalisation**: output is divided by a recent peak that decays in about 0.5 to 5 s.
- **Long-reference normalisation**: output is divided by a reference that changes over tens of seconds or longer.
- **Fixed scale**: no automatic level control; the user sets a gain.
- **Wideband**: one scalar gain applied to all bands.
- **Per-band**: each band has its own gain.

---

## Q0. What each system actually does (mechanism, not marketing)

### Takeaway
Most hobby and open-source systems normalise to a short recent maximum of one to a few seconds, using a single wideband scalar: Sensory Bridge, Emotiscope, LedFx, the Scott Lawson visualiser and WLED's "Vivid" or "Normal" automatic gain. The exceptions are MilkDrop/projectM, which divides each of three bands by its own roughly 4 s average, and two parts with long memory: WLED "Lazy" and Sensory Bridge's VU-dot mode. Professional tools use a manual gain plus a fall (decay) control and have no automatic gain at all.

### Cited findings

#### Lixie Labs Sensory Bridge (firmware 4.1.1 = `main`; 12.8 kHz sample rate, 96-sample chunks, so one analysis frame is about 7.5 ms, about 133 frames/s)
- Defaults: `DEFAULT_SAMPLE_RATE 12800`, `SAMPLES_PER_CHUNK 96`, `SENSITIVITY 1.0`, `SWEET_SPOT_MIN_LEVEL 750`, `SWEET_SPOT_MAX_LEVEL 30000`, `STANDBY_DIMMING true`. Sources: [constants.h L4](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/constants.h#L4) and [globals.h L54-L68](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/globals.h#L54-L68).
- **Fixed digital gain (SENSITIVITY).** In `acquire_sample_chunk()` each sample is computed as `sample = raw*0.000512 + 56000 − 5120; sample >>= 2; sample *= CONFIG.SENSITIVITY`, then hard-clipped to ±32767. This is a plain multiplier with no automation — [i2s_audio.h L62-L75](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/i2s_audio.h#L62-L75).
  - The user sets it through the serial command `sensitivity=[float]`, documented as "Sets the scaling of audio data (>1.0 is more sensitive…" — `serial_menu.h` L318 and L899-L909 ([repo](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/serial_menu.h)).
  - It was exposed on the web settings page from release 3.1.0 — [release 3.1.0 notes](https://github.com/connornishijima/SensoryBridge/releases/tag/3.1.0).
- **Waveform peak follower (`max_waveform_val_follower`).**
  - Computes `max_waveform_val = max|sample| − SWEET_SPOT_MIN_LEVEL`.
  - The follower rises with coefficient 0.25 per frame (about 4 frames, about 30 ms) and falls with 0.005 per frame (about 200 frames, about 1.5 s). It is floored at `SWEET_SPOT_MIN_LEVEL`.
  - `waveform_peak_scaled = max_waveform_val / follower`, then smoothed at 0.25 — [i2s_audio.h L108-L129](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/i2s_audio.h#L108-L129).
  - In 4.1.1, `waveform_peak_scaled` is consumed only in one commented-out line, `//fadeToBlackBy(leds, 128, 255-255*waveform_peak_scaled);` ([lightshow_modes.h L165](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/lightshow_modes.h#L165)). A grep of every firmware file on `main` found no other consumer (this research).
  - The follower first appears in release 3.0.0 and is absent in 1.0.0, 1.1.0 and 2.0.0 (scan of every release tag; this research).
- **Spectrogram auto-range (`goertzel_max_value`): single wideband scalar.** In `process_GDFT()`:
  - `max_value` is the maximum over all 64 bins of `magnitudes_final`, multiplied by 0.995.
  - `goertzel_max_value` rises with coefficient 0.005 per frame (about 200 frames, about 1.5 s) and falls with 0.0025 per frame (about 400 frames, about 3 s).
  - It is floored at 4.0.
  - Every bin is multiplied by `1/goertzel_max_value` — [GDFT.h L169-L198](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/GDFT.h#L169-L198).
  - The same code is present at tags 4.0.0 and 4.1.1 (tag scan, this research).
- **Per-bin smoothing before auto-range.** `magnitudes_normalized_avg = 0.3·new + 0.7·old`, then `low_pass_array(..., 1.0 + 10.0*MOOD)`. The MOOD knob controls smoothing, not level — [GDFT.h L118, L149](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/GDFT.h#L118-L149).
- **Chromagram auto-range.** `max_peak *= 0.999` each call (about 1000 calls). It rises at 0.05 toward any `chromagram_smooth` bin above it and is floored at 0.01; the output is divided by `max_peak` — [led_utilities.h L1225-L1239](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/led_utilities.h#L1225-L1239). The call rate is the LED-thread rate, so the time constant in seconds is UNVERIFIED.
- **VU modes.**
  - `calculate_vu()` computes the chunk RMS, subtracts the calibrated `VU_LEVEL_FLOOR`, then divides by `(1 − VU_LEVEL_FLOOR)` — [i2s_audio.h L190-L247](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/i2s_audio.h#L190-L247).
  - `light_mode_vu_dot()` then auto-ranges against `max_level`, which rises at 0.1 toward 1.1 × level and decays ×0.9999 per call (about 10,000 calls) with a floor of 0.0025 — [lightshow_modes.h L180-L205](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/lightshow_modes.h#L180-L205).
  - At an LED rate of 100–200 calls/s that is about 50–100 s of memory. The call rate is inferred, not measured. This is the longest-memory normaliser in the upstream code.
- **Noise calibration (NOISE button).** Over 256 frames:
  - Per bin it max-holds `magnitudes_normalized_avg` into `noise_samples[]`. Afterwards it subtracts `noise_samples[i]*1.5` from each bin ("Treat noise 1.5x louder than calibration") — [GDFT.h L121-L146](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/GDFT.h#L121-L146).
  - `SWEET_SPOT_MIN_LEVEL` is set to 1.10 × peak amplitude seen during frames 64–192 — [i2s_audio.h L97-L106](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/i2s_audio.h#L97-L106).
  - `VU_LEVEL_FLOOR` is set to 1.5 × the largest RMS seen — [i2s_audio.h L226-L230](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/i2s_audio.h#L226-L230).
  - `start_noise_cal()` resets these values — [noise_cal.h](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/noise_cal.h).
  - The README describes it as: "pause the music for a moment and press the NOISE BUTTON to run a 3-second calibration" — [README](https://github.com/connornishijima/SensoryBridge/blob/main/README.md).
- **Sweet-spot indicator.** This is a fixed-threshold meter on raw peak amplitude, not part of the gain path.
  - State −1 if `max_waveform_val_raw ≤ SWEET_SPOT_MIN_LEVEL·1.10`, +1 if ≥ `SWEET_SPOT_MAX_LEVEL` (30000), else 0 — [i2s_audio.h L137-L155](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/i2s_audio.h#L137-L155).
  - README: the three LEDs "indicate if your music is playing too quietly for the auto-ranger to account for, or if it's too loud! (Close to clipping!)" — [README](https://github.com/connornishijima/SensoryBridge/blob/main/README.md).
- **Silence / standby.**
  - After 10 s continuously in state −1, `silence = true`.
  - With `STANDBY_DIMMING`, `silent_scale` eases to 0 (IIR 0.1/0.9) — [i2s_audio.h L157-L173](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/i2s_audio.h#L157-L173).
  - Master brightness = `MASTER_BRIGHTNESS * PHOTONS² * silent_scale` — [led_utilities.h L208](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/led_utilities.h#L208).
  - PHOTONS (brightness) is a user knob, squared.
- **No multi-band or "cochlear" automatic gain in the original.** A regex scan (`agc`, `cochlear`, `auto gain`, `AUTO_GAIN`, `loud guard`) of every `.h/.ino/.cpp` file at release tags 1.0.0, 1.1.0, 2.0.0, 3.0.0, 3.2.0, 4.0.0 and 4.1.1 returned zero hits (this research; repo [connornishijima/SensoryBridge](https://github.com/connornishijima/SensoryBridge), tags listed at [/tags](https://github.com/connornishijima/SensoryBridge/tags)). The upstream level chain is exactly:
  1. fixed SENSITIVITY multiplier;
  2. per-bin calibrated noise subtraction;
  3. one wideband spectrogram max-follower (1.5 s up, 3 s down);
  4. a separate chromagram max-follower;
  5. a VU floor plus a slow VU max (VU modes only);
  6. a waveform peak follower whose output is unused in 4.1.1.

#### Lixie Labs Emotiscope (`main`; 12.8 kHz, 64-sample chunks, so about 200 frames/s; Goertzel bins updated on alternate frames)
- Chunk size and rate: `CHUNK_SIZE 64`, `SAMPLE_RATE 12800` — [microphone.h L23-L24](https://github.com/connornishijima/Emotiscope/blob/main/src/microphone.h#L23-L24).
- The CPU loop is `acquire_sample_chunk(); calculate_magnitudes(); get_chromagram(); run_vu(); update_tempo();` — [cpu_core.h L28-L40](https://github.com/connornishijima/Emotiscope/blob/main/src/cpu_core.h#L28-L40).
- **Spectrum auto-range ("autoranger"): single wideband scalar.**
  - `max_val` is the maximum over 64 bins of the 2-frame-averaged, noise-filtered magnitudes.
  - `max_val_smooth` moves toward it with a symmetric coefficient of 0.005 per frame in both directions (about 200 frames, about 1 s).
  - It is floored at 0.0025 ("below this we don't auto-range anymore").
  - `magnitude = clip(magnitudes_smooth * (1/max_val_smooth))` — [goertzel.h L311-L333](https://github.com/connornishijima/Emotiscope/blob/main/src/goertzel.h#L311-L333).
  - A 12-frame moving average then produces `spectrogram_smooth` — [goertzel.h L52, L336-L349](https://github.com/connornishijima/Emotiscope/blob/main/src/goertzel.h#L336-L349).
- **Adaptive per-bin noise floor (replaced the calibration button).**
  - Once per second the raw magnitudes are snapshotted into a 10-deep history.
  - `noise_floor[i] = 0.99·noise_floor[i] + 0.01·(0.9 × mean of the 10 snapshots)`.
  - `magnitude = max(raw − noise_floor, 0)` — [goertzel.h L229-L269](https://github.com/connornishijima/Emotiscope/blob/main/src/goertzel.h#L229-L269).
  - The author's description in the 1.1 changelog: "If Emotiscope hears a note for more than about 10 seconds without the note changing, it grows a small 'blind spot' where that note is … constant hums like traffic outside, A/C units, or microwaves get automatically filtered away even while music is playing, no calibration needed … that microphone calibration icon is gone" — [CHANGELOG_1.1.md](https://github.com/connornishijima/Emotiscope/blob/main/extras/CHANGELOG_1.1.md).
- **VU.**
  - `max_amplitude_now` = maximum of sample² over the chunk.
  - Every 250 ms a value is logged into a 20-slot ring (5 s). `vu_floor` = 0.9 × the ring mean.
  - The floor is subtracted, then the result is auto-scaled by `max_amplitude_cap`, which tracks symmetrically at 0.1 per frame (about 10 frames, about 50 ms), with a floor of 0.000025.
  - The result is a 12-sample moving average — [vu.h L26-L92](https://github.com/connornishijima/Emotiscope/blob/main/src/vu.h#L26-L92).
  - Consequence (inference): VU reads level above 90 % of its own 5 s mean, normalised to a ~50 ms peak, so steady loud music reads low and onsets read high.
- **Novelty and tempo normalisation.**
  - `normalize_novelty_curve()` decays `max_val *= 0.99` per call and scales the whole history by `1/max_val`. A smoothed `max_val_smooth` is computed but not used for the scaling — [tempo.h L225-L259](https://github.com/connornishijima/Emotiscope/blob/main/src/tempo.h#L225-L259).
  - Tempo-bin magnitudes are normalised per frame to their maximum (floor 0.02) and then cubed — [tempo.h L188-L221](https://github.com/connornishijima/Emotiscope/blob/main/src/tempo.h#L188-L221).
- **Author's stated design goal (level invariance).** Connor Nishijima, replying to a Tindie review: "a bunch of DSP going on to help Emotiscope react the same whether music is near, far, quiet or loud. My general observation is that as long as Emotiscope can hear the music slightly louder than any other dialog or noise in the room, you'll get a great show." — [Tindie product page, reviews section](https://www.tindie.com/products/lixielabs/emotiscope-a-music-visualizer-from-the-future/).
- **What changed relative to Sensory Bridge, and why.**
  - Calibration button replaced by a continuous per-bin adaptive floor (changelog above).
  - Auto-range made symmetric and faster: about 1 s both ways, against Sensory Bridge's 1.5 s up and 3 s down (code above).
  - The Tindie and Hackster pages say Emotiscope is an evolution of Sensory Bridge, which was limited by having only three knobs — [Hackster](https://www.hackster.io/lixielabs/emotiscope-a-music-visualizer-from-the-future-6761b9).
  - I found no write-up from the author explaining the auto-range constant change itself (see Gaps).

#### WLED Audio Reactive (in-tree usermod in `wled/WLED` `main`, file `usermods/audioreactive_v1/audio_reactive.cpp`; carries WLED-SR/MoonModules code and comments)
- **Presets: normal, vivid, lazy** — [audio_reactive.cpp L192-L204](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L192-L204):
  - `agcSampleDecay` {0.9994, 0.9985, 0.9997}
  - `agcZoneLow` {32, 28, 36}
  - `agcZoneHigh` {240, 240, 248}
  - `agcZoneStop` {336, 448, 304}
  - `agcTarget0` {112, 144, 164}
  - `agcTarget0Up` {88, 64, 116}
  - `agcTarget1` {220, 224, 216}
  - `agcFollowFast` {1/192, 1/128, 1/256}
  - `agcFollowSlow` {1/6144, 1/4096, 1/8192}
  - `agcControlKp` {0.6, 1.5, 0.65}
  - `agcControlKi` {1.7, 1.85, 1.2}
  - `agcSampleSmooth` {1/12, 1/6, 1/16}
- **Timing.** `getSample()` and `agcAvg()` run on a simulated 2 ms clock, 500 steps/s — [L1599-L1603](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L1599-L1603). Time constants follow from that:
  - Peak decay: 3.3 s (normal), 1.3 s (vivid), 6.7 s (lazy).
  - Slow gain follow: 12.3 s, 8.2 s, 16.4 s.
  - Fast gain follow: 0.38 s, 0.26 s, 0.51 s.
  - FastLED's port states the same numbers, in [auto_gain.cpp.hpp L29-L57](https://github.com/FastLED/FastLED/blob/master/src/fl/audio/auto_gain.cpp.hpp#L29-L57).
  - The WLED code comments say "~0.15 sec" (fast), "~2-15 secs" (slow) and "signal to zero --> 5-8sec".
- **Measured quantity.**
  - `getSample()` removes DC with a slow tracker (`micLev += (x − micLev)/12288`, snapping down to minima).
  - It takes `|x − micLev|` through an exponential smoother with weighting 0.2, giving `expAdjF`.
  - It applies the squelch gate `expAdjF = (expAdjF <= soundSquelch) ? 0 : expAdjF`.
  - It keeps a peak `sampleMax`: rises at 0.5 per step, otherwise decays by `agcSampleDecay` — [L1079-L1148](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L1079-L1148).
- **PI controller (`agcAvg()`)** — [L994-L1075](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L994-L1075):
  - Setpoint gain = `agcTarget0/sampleMax`, or `agcTarget1/sampleMax` once the amplified signal exceeds `agcTarget0Up` (comment: "a poor man's bang-bang").
  - Error = setpoint − current gain. The integrator accumulates `error·0.002·0.25`, with anti-windup.
  - In the "emergency zone" (amplified signal > `agcZoneHigh` or < `soundSquelch + agcZoneLow`) the fast follow rate is used, otherwise the slow one.
  - Gain is clamped to 1/64…32, that is −36 dB to +30 dB.
  - In silence (`|sampleReal| < 2` or `sampleMax < 1`) the integrator spins down ×0.91.
- **Single wideband gain.** The same scalar `multAgc` multiplies the volume and every one of the 16 GEQ channels: `fftCalc[i] *= soundAgc ? multAgc : (sampleGain/40·inputLevel/128 + 1/16)` — [L648-L663](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L648-L663).
  - The only per-band shaping is a fixed pink-noise correction table, `fftResultPink[16] = {1.70 … 6.83, 9.55}` — [L223](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L223).
  - It is followed by a fixed log, linear or square-root display mapping (`FFTScalingMode`, default 3 = square root) — [L680-L712](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L680-L712).
- **Dynamics limiter.**
  - `limitSampleDynamics()` slew-limits `volumeSmth` to at most 196 units per `attackTime` (default 80 ms) rising and per `decayTime` (default 1400 ms) falling. It is on by default — [L112-L117, L1156-L1180](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L1156-L1180).
  - GEQ channels rise at 0.75 and fall at 0.17 per FFT cycle (~21 ms) by default — [L663-L668](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L663-L668).
- **Defaults.** AGC is off by default (`SR_AGC` 0), squelch 10, gain 60 — [usermod readme](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/readme.md).
- **Official documentation.**
  - Squelch: "Start with a higher squelch value and lower it until the LEDs just stop reacting to ambient noise in your room".
  - AGC: "The prerequisite is that Squelch is set correctly first, so AGC knows what 'silence' looks like."
  - Presets: Normal "Smoothly follows changes in volume"; Vivid "Reacts quickly … More dramatic LED response to dynamics"; Lazy "Slower to adjust. Works well for GEQ effects or music with wide dynamic range."
  - First-time setup: gain high, squelch 1, AGC off; raise squelch in a quiet room; then set gain to about 40 at normal music volume; "Optionally, enable AGC" — [kno.wled.ge Audio Reactive](https://kno.wled.ge/advanced/audio-reactive/).
- **MoonModules / WLED-SR documentation.**
  - Lazy: "Recommended for GEQ effects, or when listening to music that features strong 'dynamics'". Vivid: "Recommended in case you want 'more blinken from your LEDs'".
  - "Line-in signals are typically much lower… Rather than use an auto gain function, you can manually adjust the gain from 1 to 255, which translates to 0.1 up to almost 6.5 gain … -20dB up to +16dB."
  - AGC is "not enabled by default" — [mm.kno.wled.ge Sound Settings](https://mm.kno.wled.ge/soundreactive/Sound-Settings/).
- **WLED-MM's own source not read.** The `MoonModules/WLED-MM` `mdev` tree now contains only `pio-scripts/patch_audioreactive.py` for audio reactive; the usermod source is pulled from elsewhere (tree listing, this research). The `wled/WLED` readme says "New pull requests must be made against the out-of-tree V2 usermod" — [readme](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/readme.md). WLED-MM's current copy and the V2 usermod were not read: UNVERIFIED whether they differ from the v1 code above.

#### FastLED `fl::audio::AutoGain` (a WLED-derived port; relevant because K1 already links FastLED)
- Header comment: "The AGC uses a PI (proportional-integral) controller with slow peak envelope tracking, inspired by WLED Sound Reactive. It adapts to source-level differences (MEMS mic vs line-in) rather than musical dynamics, avoiding cross-band coupling that plagues fast-tracking AGC designs." — [auto_gain.h L20-L25, L62-L73](https://github.com/FastLED/FastLED/blob/master/src/fl/audio/auto_gain.h#L20-L73).
- Algorithm: peak envelope of input RMS with fast attack (10 ms) and slow decay (3.3, 1.3 or 6.7 s by preset). Target gain = `targetRMSLevel / peakEnvelope`. A PI controller uses a 12.3 s slow or 0.38 s fast time constant. Gain is clamped to 1/64…32. The integrator spins down in silence — [auto_gain.cpp.hpp L29-L62, L98-L185](https://github.com/FastLED/FastLED/blob/master/src/fl/audio/auto_gain.cpp.hpp#L29-L62).

#### LedFx (`main`)
- **Silence gate.**
  - `volume = 1 + aubio.db_spl(frame)/100`, clamped to 0…1 and filtered with `ExpFilter(alpha_decay=0.99, alpha_rise=0.99)`, which is almost no smoothing.
  - If `volume ≤ min_volume` the frequency domain is replaced by zeros — [audio.py L46-L47, L1091-L1110](https://github.com/LedFx/LedFx/blob/main/ledfx/effects/audio.py#L1091-L1110).
  - The default `min_volume` was not located: UNVERIFIED.
- **Fixed spectral tilt.** A pre-emphasis biquad "to balance the input volume of lows to highs", with coefficients depending on the mel type — [audio.py L731-L743](https://github.com/LedFx/LedFx/blob/main/ledfx/effects/audio.py#L731-L743).
- **Melbank normalisation: single wideband scalar, instant attack, slow release.** `filter_banks **= power_factor` (peak isolation), then:
  - `mel_gain = ExpFilter(alpha_decay=0.01, alpha_rise=0.99)` updated with `np.max(fast_blur_array(filter_banks, sigma=1.0))`;
  - `filter_banks /= mel_gain.value`;
  - `mel_smoothing` (decay 0.7, rise 0.99);
  - plus a common-mode-subtracted "filtered" bank (`common_filter` 0.99/0.01, `diff_filter` 0.15/0.99) — [melbank.py L325-L352](https://github.com/LedFx/LedFx/blob/main/ledfx/effects/melbank.py#L325-L352).
  - With alpha 0.01 per frame the release is about 100 frames. LedFx's audio frame rate was not confirmed (UNVERIFIED); at 60 fps it would be about 1.7 s.
- **Per-effect "sensitivity" is a speed control, not a gain.** In the Energy effect, `alpha_rise = sensitivity` and `alpha_decay = (sensitivity − 0.1)·0.7` — [energy.py L23-L45](https://github.com/LedFx/LedFx/blob/main/ledfx/effects/energy.py#L23-L45).
- **Ancestor: Scott Lawson's audio-reactive-led-strip, at 60 FPS and a 44.1 kHz microphone** ([config.py L58-L61](https://github.com/scottlawsonbc/audio-reactive-led-strip/blob/master/python/config.py#L58-L61)).
  - Same `mel_gain = ExpFilter(alpha_decay=0.01, alpha_rise=0.99)` wideband normaliser, about 1.7 s release — [visualization.py L181-L182, L220-L221](https://github.com/scottlawsonbc/audio-reactive-led-strip/blob/master/python/visualization.py#L181-L221).
  - In addition, a **per-bin** `gain = ExpFilter(np.tile(0.01, N_FFT_BINS), alpha_decay=0.001, alpha_rise=0.99)` with `y /= gain.value` is used by the scroll and energy effects. That is about 1000 frames, about 17 s per-bin release — [visualization.py L101-L110, L131-L132](https://github.com/scottlawsonbc/audio-reactive-led-strip/blob/master/python/visualization.py#L101-L132).
  - Silence gate: `MIN_VOLUME_THRESHOLD = 1e-7` on peak amplitude — [config.py L104](https://github.com/scottlawsonbc/audio-reactive-led-strip/blob/master/python/config.py#L104); [visualization.py L200-L201](https://github.com/scottlawsonbc/audio-reactive-led-strip/blob/master/python/visualization.py#L200-L201).
- **User complaints.** No LedFx-specific GitHub issue about level or normalisation was found within budget (Gaps).

#### MilkDrop / projectM (`bass`, `mid`, `treb`, `bass_att` and the others)
- **Definition (author's preset guide).** "bass … retrieves the current amount of bass. 1 is normal; below ~0.7 is quiet; above ~1.3 is loud bass". "bass_att … retrieves an attenuated reading on the bass, meaning that it is damped in time and doesn't change so rapidly." — [MilkDrop preset authoring guide (Ryan Geiss)](https://www.geisswerks.com/milkdrop/milkdrop_preset_authoring.html).
- **Mechanism (projectM's implementation of the MilkDrop behaviour), `Loudness::UpdateBandAverage`:**
  - Each band (bass, mid, treble = thirds of the lower half of the spectrum) sums its bins into `m_current`.
  - Short average: rate 0.2 when rising, 0.5 when falling, per 30 fps-equivalent frame.
  - Long average: rate 0.992, about 125 frames, about 4.2 s at 30 fps; 0.9 during the first 50 frames.
  - `bass = current/longAverage`, `bass_att = shortAverage/longAverage`. Rates are re-based to the actual frame rate by `pow(pow(rate,30), dt)` — [Loudness.cpp](https://github.com/projectM-visualizer/projectm/blob/master/src/libprojectM/Audio/Loudness.cpp); [Loudness.hpp](https://github.com/projectM-visualizer/projectm/blob/master/src/libprojectM/Audio/Loudness.hpp) ("This value will revolve around 1.0, with <0.7 being very silent and >1.3 very loud audio").
- **Why this design.** The guide states values relative to "normal". I found no explicit author rationale (Gaps). Inference: dividing by a ~4 s per-band average makes presets volume-independent and lets preset authors write fixed thresholds such as `bass > 1.3`.

#### Consumer products
- **Philips Hue Sync.**
  - Four intensity levels: Subtle, Moderate, High, Intense (Extreme on the HDMI Sync Box), plus a separate brightness setting. The press release describes intensity as changing "the speed at which your lights change with the content" — [Signify press release 2018](https://www.signify.com/en-us/about/news/press-releases/2018/20180531-create-surround-sound-for-your-eyes-with-philips-hue-sync); [MacRumors Sync Box review](https://www.macrumors.com/review/philips-hue-play-hdmi-sync-box/); [Hue "sync with music" page](https://www.philips-hue.com/en-us/explore-hue/blog/sync-with-music).
  - No public description of input-level handling: UNVERIFIED. Hue Sync desktop takes the system's digital audio, not a room microphone (UNVERIFIED for every Hue product).
- **Nanoleaf Rhythm.** The response visibly depends on absolute loudness:
  - "the light reaction to the sound is tied to both the volume and the duration of the sound. A quiet 'hello' … activates just a couple of the triangle lights … the slam of a door activates all of the lights" — [MacRumors Aurora Rhythm review](https://www.macrumors.com/review/nanoleaf-aurora-rhythm/).
  - The app has a sensitivity slider — [BGR review](https://bgr.com/tech/nanoleaf-rhythm-edition-review-smart-home-lighting-with-a-colorful-twist/).
  - Effects such as Paint Splatter and Sound Bar scale area or colour with loudness ("The louder the sound, the larger the area it covers") — [iOSHacker review](https://ioshacker.com/reviews/rhythm-module-for-nanoleaf-review).
  - Third-party troubleshooting pages (low authority) report both failure modes: "music too quiet" (no response) and sensitivity above about 70 % "causes constant triggering" — [trunetto guide](https://www.trunetto.com/troubleshooting/smart-lighting/nanoleaf/nanoleaf-rhythm-module-triggering-background-noise); [trunetto guide 2](https://www.trunetto.com/troubleshooting/smart-lighting/nanoleaf/nanoleaf-rhythm-music-sync-not-working).
  - Whether the module has internal automatic gain: UNVERIFIED.
- **Twinkly Music.** Marketed as a "smart microphone" with a "BPM counter" and "multicore DSP" — [Twinkly Music page](https://twinkly.com/twinkly-music); [Twinkly UK product page](https://twinkly.com/uk-gb/products/music-dongle). Retailer copy claims "auto volume sensitivity adjustment" (seen in a search-result summary, not opened; listings include [Adorama](https://www.adorama.com/twtmd01usb.html)). Algorithm UNVERIFIED; no manual sensitivity setting found.
- **Govee.** No reliable public description of microphone music-mode level handling was found. The "sensitivity" in Govee Desktop's guide refers to screen-sync responsiveness — [Govee Desktop user guide](https://desktop.govee.com/user-manual/user-guide). Everything else about Govee here is UNVERIFIED.

#### Professional practice
- **Resolume.** Each animated parameter gets FFT animation with **Gain** ("boost the signal until it is having the right amount of effect") and **Fall** ("how quickly the value falls back from a peak"). There is also a master audio gain in Preferences and the toolbar — [Resolume parameter animation docs](https://resolume.com/support/en/6/parameter-animation).
  - Users report the Fall behaviour changed in 6/7 to act "like a reverb" — [forum](https://resolume.com/forum/viewtopic.php?p=81397).
  - Workarounds for weak input are manual: raise clip volume, add an EQ plug-in — [forum](https://www.resolume.com/forum/viewtopic.php?p=30907).
  - No automatic gain is documented.
- **grandMA2.** The Sound Input window has a **Snd In** fader ("sets the gain of the incoming sound signal"), a **Snd Fade** fader and a BPM fader that follows tempo automatically. The XLR input needs at least 20 mV — [grandMA2 help: Sound Input window](https://help.malighting.com/grandMA2/en/help/key_ost_sound_input_window.html).
- **grandMA3.** The **Sound Fade** master "changes the fall-off speed of all of the channels. While a lower number results in more accurate tracking of quickly changing dynamics, the response may appear undesirably erratic. A higher value results in a smoother response." The BPM master locks automatically — [grandMA3 Sound Viewer](https://help.malighting.com/grandMA3/2.2/HTML/sound_viewer.html). No automatic gain is mentioned on the pages read.
- **TouchDesigner (`audioAnalysis` palette component).** Per-band Low, Mid and High **Threshold / Smooth / Gain / Add**, plus Kick, Snare and Rhythm thresholds, all manual — [Derivative docs](https://derivative.ca/UserGuide/Palette:audioAnalysis). The `audioSet` component has an input gain in dB before a compressor, "if the signal to be compressed is not in a useful dynamic range" — [Derivative docs: audioSet](https://derivative.ca/UserGuide/Palette:audioSet). Community advice is to "lower the threshold … until you start getting a usable output" — [Interactive & Immersive HQ](https://interactiveimmersive.io/blog/touchdesigner-lessons/audio-reactive-visuals-a-beginner-guide/).
- **DJ lighting: SoundSwitch (inMusic, now also in rekordbox).** It analyses tracks in advance from the DJ software ("detect musical sections and instrumentation, then create a unique light show for each track"), with beat-synced Autoloops for unanalysed or streaming tracks — [Magnetic Magazine, Sep 2026](https://magneticmag.com/2026/09/alphatheta-brings-soundswitch-into-rekordbox/); [SoundSwitch user guide](https://cdn.inmusicbrands.com/soundswitch/files/User%20Guide.pdf). This side-steps microphone level entirely.
- **Broadcast and install audio automatic gain (general reference).** An automatic gain control is described as "a special case of a compressor with its threshold set at a very low level; moderate to slow attack times, long release times, and low ratios", aimed at "maintaining program dynamics" — [Rane HAL AGC block reference](https://ranecommercial.com/legacy/hal/OnlineHelp/Content/Reference_Block_Topics/BlockReference_Dynamics_AGC.htm). Quoted from a search-result summary; the page was not opened.

### Inferences
- Upstream Sensory Bridge has one wideband spectral auto-ranger with a 1.5 s attack and 3 s release, plus fixed calibrated floors. A multi-band "cochlear" automatic gain and a "loud guard" limiter are not in any upstream release, so they must be additions in the K1 fork. The upstream waveform peak follower exists but is unused in 4.1.1, so any K1 use of it as a normaliser is also a fork change.
- Emotiscope moved further toward level invariance: about 1 s symmetric auto-range, a VU measured relative to its own 5 s mean, and a continuous adaptive per-bin floor. The author's own words show this was intended.

### Gaps
- No Lixie Labs blog post or video found that explains the choice of auto-range constants or the change between Sensory Bridge and Emotiscope (budget; YouTube descriptions not searched).
- WLED-MM's current and V2 out-of-tree audio-reactive source not read.
- LedFx audio frame rate and `min_volume` default not located.
- Hue, Nanoleaf, Govee and Twinkly internals are not public; only reviews and marketing were found.

---

## Q1. Short recent maximum, long average, or no normalisation?

### Takeaway
Short-max (about 1–3 s) dominates hobby and open-source practice. MilkDrop uses a medium per-band average (about 4 s). Professional consoles and VJ tools use a fixed scale with a manual gain. Long-memory references exist only as minority options: WLED "Lazy" with a 6.7 s peak and 16 s slow follow, Sensory Bridge's VU-dot max with an inferred ~50–100 s decay, and Scott Lawson's ~17 s per-bin gain.

### Cited findings
- **Short-max:**
  - Sensory Bridge spectrogram: 1.5 s up, 3 s down — [GDFT.h L169-L198](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/GDFT.h#L169-L198).
  - Emotiscope spectrum: about 1 s symmetric; VU cap about 50 ms — [goertzel.h L311-L333](https://github.com/connornishijima/Emotiscope/blob/main/src/goertzel.h#L311-L333), [vu.h L62-L76](https://github.com/connornishijima/Emotiscope/blob/main/src/vu.h#L62-L76).
  - LedFx and Scott Lawson melbank: instant attack, release about 100 frames (about 1.7 s at 60 fps) — [melbank.py L325-L347](https://github.com/LedFx/LedFx/blob/main/ledfx/effects/melbank.py#L325-L347), [visualization.py L181-L182](https://github.com/scottlawsonbc/audio-reactive-led-strip/blob/master/python/visualization.py#L181-L182).
  - WLED Vivid: 1.3 s peak decay — [audio_reactive.cpp L193](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L193).
- **Medium per-band average:** MilkDrop/projectM long average about 4.2 s — [Loudness.cpp](https://github.com/projectM-visualizer/projectm/blob/master/src/libprojectM/Audio/Loudness.cpp).
- **Longer references:**
  - WLED Normal and Lazy: peak 3.3 or 6.7 s; slow follow 12.3 or 16.4 s; a fast zone only when the signal leaves the 32–240 "normal zone" — [audio_reactive.cpp L192-L204, L1044-L1050](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L1044-L1050).
  - Sensory Bridge VU-dot `max_level *= 0.9999` per call — [lightshow_modes.h L189-L197](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/lightshow_modes.h#L189-L197).
  - Scott Lawson per-bin gain decay alpha 0.001 — [visualization.py L101-L102](https://github.com/scottlawsonbc/audio-reactive-led-strip/blob/master/python/visualization.py#L101-L102).
- **No normalisation (fixed scale plus user gain):**
  - WLED with AGC off (the default) — [readme](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/readme.md).
  - Resolume Gain/Fall — [docs](https://resolume.com/support/en/6/parameter-animation).
  - grandMA Snd In — [grandMA2 help](https://help.malighting.com/grandMA2/en/help/key_ost_sound_input_window.html).
  - TouchDesigner per-band Gain/Threshold — [docs](https://derivative.ca/UserGuide/Palette:audioAnalysis).

### Inferences
- With a short-max reference, any section longer than about 3–5 release time constants is rescaled to full range. For Sensory Bridge that is about 10–15 s, for Emotiscope about 3–5 s, for LedFx about 5–8 s. A 30 s breakdown therefore ends up as bright as a chorus. This is the "louder is not brighter" symptom; it is a direct consequence of these constants, not a tuning bug.
- MilkDrop's ~4 s average has the same effect on section dynamics. It is acceptable there because MilkDrop uses the values for motion and pulse, not brightness.

### Gaps
- No published measurement of any of these systems' brightness against section loudness on real music was found.

---

## Q2. Single wideband gain or per-band gain, and what artefacts each produces?

### Takeaway
Nearly every system uses one wideband scalar. Per-band normalisation appears only in MilkDrop (three bands, against a ~4 s average) and Scott Lawson's scroll and energy effects (per-bin, about 17 s release). FastLED's maintainers explicitly reject fast-tracking automatic gain because of "cross-band coupling". Per-band normalisation trades timbre and spectral-balance fidelity for per-band liveliness.

### Cited findings
- **Wideband scalar:**
  - Sensory Bridge `goertzel_max_value` (maximum across all 64 bins) — [GDFT.h L172-L198](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/GDFT.h#L172-L198).
  - Emotiscope `max_val_smooth` — [goertzel.h L289-L333](https://github.com/connornishijima/Emotiscope/blob/main/src/goertzel.h#L289-L333).
  - WLED `multAgc` applied to all 16 GEQ channels — [L657](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L657).
  - LedFx `mel_gain` (scalar maximum) — [melbank.py L346-L347](https://github.com/LedFx/LedFx/blob/main/ledfx/effects/melbank.py#L346-L347).
- **Fixed (non-adaptive) spectral tilt instead of per-band automatic gain:**
  - WLED `fftResultPink[]` multipliers, 1.70 rising to 9.55 at the top channel — [L223](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L223).
  - LedFx pre-emphasis biquad — [audio.py L731-L743](https://github.com/LedFx/LedFx/blob/main/ledfx/effects/audio.py#L731-L743).
- **Per-band:**
  - MilkDrop/projectM bass, mid and treble, each divided by its own long average — [Loudness.cpp](https://github.com/projectM-visualizer/projectm/blob/master/src/libprojectM/Audio/Loudness.cpp).
  - Scott Lawson per-bin `gain` — [visualization.py L101-L110](https://github.com/scottlawsonbc/audio-reactive-led-strip/blob/master/python/visualization.py#L101-L110).
  - TouchDesigner per-band manual gain — [docs](https://derivative.ca/UserGuide/Palette:audioAnalysis).
- **Practitioner statement against fast automatic gain:** "adapts to source-level differences … rather than musical dynamics, avoiding cross-band coupling that plagues fast-tracking AGC designs" — [FastLED auto_gain.h L22-L25](https://github.com/FastLED/FastLED/blob/master/src/fl/audio/auto_gain.h#L20-L25).
- **Artefacts the documentation acknowledges:**
  - WLED recommends Lazy (slowest) "for GEQ effects or music with wide dynamic range" and describes Vivid as "more dramatic LED response to dynamics" — [kno.wled.ge](https://kno.wled.ge/advanced/audio-reactive/); [mm.kno.wled.ge](https://mm.kno.wled.ge/soundreactive/Sound-Settings/). This implies faster automatic gain distorts spectrum-display and dynamic material.
  - grandMA3: a short fall time is "more accurate tracking of quickly changing dynamics, [but] may appear undesirably erratic" — [grandMA3 Sound Viewer](https://help.malighting.com/grandMA3/2.2/HTML/sound_viewer.html).

### Inferences
- **Wideband short-max artefacts:**
  - Pumping: one loud bass hit dims everything else for the release time.
  - Section flattening.
  - Loud-dense music "cut": a strong band pins the shared maximum and the other bands look small.
  - Noise lift in quiet passages, bounded only by the floor (Sensory Bridge 4.0, Emotiscope 0.0025).
- **Per-band short-max artefacts:**
  - Every band is driven toward the top independently, so spectral balance (timbre, "colour of the mix") is lost.
  - A quiet hi-hat looks as big as a kick.
  - A band carrying only noise is amplified. MilkDrop's band ratios around 1.0 avoid brightness issues only because they are used for motion.
- Stacking several of these, as the K1 description says (fixed gain + peak follower + 4-band automatic gain + limiter), compounds both families of artefact. No prior-art system stacks more than one adaptive gain in series on the same path; WLED explicitly has one gain (`multAgc`) plus a separate slew limiter on the volume only.

### Gaps
- No controlled A/B study of wideband against per-band normalisation in light shows was found.

---

## Q3. How is silence treated (gate, squelch, noise-floor learning), and what goes wrong?

### Takeaway
There are three patterns:
1. A manual one-shot calibration that the user triggers in silence (Sensory Bridge).
2. A manual squelch threshold (WLED, the professional thresholds in TouchDesigner, LedFx `min_volume`).
3. A continuously adapting per-bin floor (Emotiscope from 1.1).

Each has a known failure mode: a stale or poisoned calibration, a squelch set wrong so the automatic gain amplifies noise, and an adaptive floor that eats sustained notes. A hard floor under the auto-ranger, so that it never scales noise to full range, is common and important.

### Cited findings
- **Sensory Bridge.**
  - Button calibration: about 256 frames, "3-second" — [README](https://github.com/connornishijima/SensoryBridge/blob/main/README.md).
  - Per-bin noise subtracted ×1.5; floors for VU and sweet spot set at 1.5× and 1.1× the observed maxima — [GDFT.h L121-L146](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/GDFT.h#L121-L146); [i2s_audio.h L97-L106, L226-L230](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/i2s_audio.h#L97-L106).
  - Auto-range floor 4.0 — [GDFT.h L188-L190](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/GDFT.h#L188-L190).
  - Fade to black after 10 s below the floor — [i2s_audio.h L157-L173](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/i2s_audio.h#L157-L173).
- **Emotiscope.**
  - Continuous per-bin floor from a 10 s history; anything sustained about 10 s becomes a "blind spot". The calibration icon was removed — [CHANGELOG_1.1.md](https://github.com/connornishijima/Emotiscope/blob/main/extras/CHANGELOG_1.1.md); [goertzel.h L229-L269](https://github.com/connornishijima/Emotiscope/blob/main/src/goertzel.h#L229-L269).
  - VU floor = 0.9 × 5 s mean of peak² — [vu.h L41-L60](https://github.com/connornishijima/Emotiscope/blob/main/src/vu.h#L41-L60).
  - Auto-range floor 0.0025 — [goertzel.h L321-L324](https://github.com/connornishijima/Emotiscope/blob/main/src/goertzel.h#L321-L324).
- **WLED.**
  - Squelch is a time-domain level gate (`expAdjF <= soundSquelch → 0`) — [L1117-L1118](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L1117-L1118).
  - The GEQ post-gain is skipped and magnitude muted when the smoothed volume is below its gate — [L556](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L556), [L1612](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L1612).
  - The automatic gain integrator spins down in silence — [L1016-L1021](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L1016-L1021).
  - The low "emergency zone" is relative to squelch (`soundSquelch + agcZoneLow`) — [L1044](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L1044).
  - Docs: the automatic gain needs squelch set "so AGC knows what 'silence' looks like"; set squelch "until the LEDs just stop reacting to ambient noise"; digital microphones typically need 1–20, analogue up to 64 — [kno.wled.ge](https://kno.wled.ge/advanced/audio-reactive/).
- **LedFx.** A dB-SPL threshold zeroes the spectrum — [audio.py L1098-L1110](https://github.com/LedFx/LedFx/blob/main/ledfx/effects/audio.py#L1098-L1110).
- **Scott Lawson.** A fixed `1e-7` peak gate — [config.py L104](https://github.com/scottlawsonbc/audio-reactive-led-strip/blob/master/python/config.py#L104).
- **Consumer failures.** Nanoleaf third-party guides report both no reaction to quiet music and constant triggering at high sensitivity — [trunetto](https://www.trunetto.com/troubleshooting/smart-lighting/nanoleaf/nanoleaf-rhythm-module-triggering-background-noise). Low-authority source.

### Inferences
- **What goes wrong:**
  - Calibration taken during music raises the floors and mutes quiet material. Sensory Bridge's calibration takes the max-hold over the window, so any music in the window becomes "noise".
  - Squelch set too low with automatic gain on lets the gain ride up on room noise.
  - Emotiscope's adaptive floor removes long drones and pads (by design), and its 5 s VU floor makes sustained loud music read as low level.
- A fixed floor below which the auto-ranger stops increasing gain (Sensory Bridge 4.0, Emotiscope 0.0025, WLED's maximum gain of 32) is the pattern that prevents "noise bloom in silence". Its value sets the quietest music that will still fill the display. Sensory Bridge exposes exactly that boundary through the sweet-spot LEDs.

### Gaps
- No quantitative reports of how often users mis-calibrate were found.

---

## Q4. Is a user sensitivity control a weakness or the reliable solution?

### Takeaway
In professional tools a manual input gain plus a fall control is the norm, and no automatic gain is offered or documented. In WLED, manual squelch plus gain is the documented primary method; the automatic gain is optional, off by default and requires a correct squelch. Consumer and Lixie Labs products move the other way, toward hiding or removing calibration (Emotiscope 1.1, Twinkly's claimed automatic sensitivity). Users of Nanoleaf's sensitivity slider report it as necessary but finicky.

### Cited findings
- **Professional.**
  - Resolume Gain + Fall per parameter plus master gain — [docs](https://resolume.com/support/en/6/parameter-animation).
  - grandMA2 Snd In gain fader — [help](https://help.malighting.com/grandMA2/en/help/key_ost_sound_input_window.html).
  - grandMA3 Sound Fade master — [help](https://help.malighting.com/grandMA3/2.2/HTML/sound_viewer.html).
  - TouchDesigner per-band Gain and Threshold — [docs](https://derivative.ca/UserGuide/Palette:audioAnalysis).
- **WLED.**
  - "Rather than use an auto gain function, you can manually adjust the gain" — [mm.kno.wled.ge](https://mm.kno.wled.ge/soundreactive/Sound-Settings/).
  - Setup: squelch, then gain, then "Optionally, enable AGC" — [kno.wled.ge](https://kno.wled.ge/advanced/audio-reactive/).
  - Automatic gain off by default — [readme](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/readme.md).
- **Lixie Labs.**
  - Sensory Bridge keeps a SENSITIVITY multiplier (serial or web) and a NOISE button — [serial_menu.h](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/serial_menu.h); [README](https://github.com/connornishijima/SensoryBridge/blob/main/README.md).
  - Emotiscope removed the calibration UI ("that microphone calibration icon is gone") — [CHANGELOG_1.1.md](https://github.com/connornishijima/Emotiscope/blob/main/extras/CHANGELOG_1.1.md).
  - A user review: it "seems to adjust well to different volume levels" — [Tindie reviews](https://www.tindie.com/products/lixielabs/emotiscope-a-music-visualizer-from-the-future/).
- **Consumer.** Nanoleaf sensitivity slider — [BGR](https://bgr.com/tech/nanoleaf-rhythm-edition-review-smart-home-lighting-with-a-colorful-twist/). Twinkly marketed as automatic — [Twinkly](https://twinkly.com/twinkly-music), mechanism UNVERIFIED.
- **LedFx "sensitivity" is not a gain at all but a smoothing speed** — [energy.py L23-L45](https://github.com/LedFx/LedFx/blob/main/ledfx/effects/energy.py#L23-L45).

### Inferences
- Professionals keep manual gain because an operator is present and wants section contrast under their own control. Automatic gain is the unattended-product answer, and every unattended product pays for it with flattened dynamics.
- A user gain trim set once per room, with no automatic gain, preserves dynamics completely but fails when the playback volume changes. That is why consumer products avoid it.

### Gaps
- No user study comparing manual against automatic sensitivity satisfaction was found.

---

## Q5. Does any system preserve section-level dynamics (drop brighter than breakdown) while working unattended across room volumes?

### Takeaway
No system found does both explicitly and verifiably. The closest designs separate two time scales:
1. A very slow reference, or a fast-up / very-slow-down peak, that absorbs room or source level over tens of seconds to minutes.
2. Leaving within-song dynamics on a fixed scale under that reference.

Examples are the WLED Lazy preset and its FastLED port, whose stated intent is to adapt to "source-level differences … rather than musical dynamics", and Sensory Bridge's VU-dot mode. The professional and DJ answer is either a human on the gain fader or offline track analysis (SoundSwitch).

### Cited findings
- **FastLED/WLED-derived design intent:** "adapts to source-level differences (MEMS mic vs line-in) rather than musical dynamics" — [auto_gain.h L22-L25](https://github.com/FastLED/FastLED/blob/master/src/fl/audio/auto_gain.h#L20-L25).
  - Implemented with a 10 ms-attack, 3.3–6.7 s-decay peak and a 12–16 s slow PI follow — [auto_gain.cpp.hpp L29-L62](https://github.com/FastLED/FastLED/blob/master/src/fl/audio/auto_gain.cpp.hpp#L29-L62).
  - A fast zone (0.26–0.51 s) applies only near clipping or near the floor — [WLED L1044-L1050](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L1044-L1050).
  - WLED docs recommend Lazy for "music with wide dynamic range" — [kno.wled.ge](https://kno.wled.ge/advanced/audio-reactive/).
- **Sensory Bridge VU-dot:** rises fast to 1.1 × level (coefficient 0.1), decays ×0.9999 per call (about 10,000 calls) — [lightshow_modes.h L189-L197](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/lightshow_modes.h#L189-L197).
- **SoundSwitch:** analyses tracks to "detect musical sections and instrumentation" offline instead of reacting to a microphone — [Magnetic Magazine](https://magneticmag.com/2026/09/alphatheta-brings-soundswitch-into-rekordbox/).
- **Nanoleaf (Aurora Rhythm):** observed to keep absolute loudness (quiet voice lights a few panels, a door slam lights all) — [MacRumors](https://www.macrumors.com/review/nanoleaf-aurora-rhythm/). This preserves dynamics, but third-party guides report the expected failure at low playback level — [trunetto](https://www.trunetto.com/troubleshooting/smart-lighting/nanoleaf/nanoleaf-rhythm-music-sync-not-working). Whether it has any automatic gain: UNVERIFIED.

### Inferences
- **WLED Lazy still compresses section contrast.** With a 6.7 s peak decay and 16 s slow follow, a breakdown of about 30 s or more is partly re-amplified. It preserves drop-against-breakdown contrast only for sections shorter than about 10 s. The "fast-up, very-slow-down" variant (Sensory Bridge VU-dot, about a minute) preserves contrast across a whole song but takes about a minute to recover after the room volume is turned down.
- **Unexplored combination.** A plausible unattended design consistent with all the prior art has these parts:
  1. One wideband reference tracking the loud end of the recent distribution (for example a high percentile or a peak with a release of tens of seconds to minutes).
  2. Fast reduction only on clipping.
  3. A hard floor or gate under it.
  4. Musical dynamics shown on a fixed (logarithmic) scale under that reference, with no per-band automatic gain.
  
  This is an inference; none of the systems reviewed implement exactly this with published validation.

### Gaps
- No talk, paper or blog post was found (within budget) on designing audio-reactive visuals specifically to preserve section-level dynamics.
- No published evaluation of any product's drop-against-breakdown brightness ratio was found.

---

## Comparison table

| System | What is measured | Normalised against | Time constants (attack / release) | Wideband or per-band | Silence handling | User level control | Known complaints or artefacts |
|---|---|---|---|---|---|---|---|
| Sensory Bridge 4.1.1, spectrogram | 64 Goertzel bins (110 Hz–4.2 kHz) | Max over bins (`goertzel_max_value`), floor 4.0 | 1.5 s / 3 s at about 133 fps | Wideband scalar | Button calibration: per-bin noise ×1.5 subtracted; 10 s silence fades output | SENSITIVITY multiplier (serial or web), PHOTONS brightness, MOOD smoothing | Sweet-spot LEDs tell the user when the input is "too quiet for the auto-ranger" or near clipping |
| Sensory Bridge, waveform follower | Peak abs sample minus floor | Own peak (`max_waveform_val_follower`) | 30 ms / 1.5 s | n/a | Floor = 1.1 × calibrated peak | — | Output unused in 4.1.1 (only a commented line) |
| Sensory Bridge, VU-dot | Chunk RMS minus floor | `max_level` (1.1 × level) | Fast up (0.1) / ×0.9999 per call (~50–100 s, inferred) | Wideband | `VU_LEVEL_FLOOR` from calibration | — | — |
| Emotiscope, spectrum | 64 Goertzel bins, 2-frame average | Max over bins (`max_val_smooth`), floor 0.0025 | 1 s / 1 s at about 200 fps | Wideband scalar | Adaptive per-bin floor from a 10 s history ("blind spot") | None for level; calibration removed in 1.1 | Sustained notes longer than about 10 s suppressed (by design) |
| Emotiscope, VU | Peak² per chunk | 0.9 × 5 s mean (floor) and a 50 ms cap | 50 ms / 50 ms | Wideband | Floor = 90 % of the 5 s mean | — | Steady loud music reads low (inference) |
| MilkDrop / projectM | Sum of three spectrum bands | Each band's own long average | Long average about 4.2 s; `_att` short average 0.2 rising / 0.5 falling per 30 fps frame | Per-band (3) | None (ratio defaults to 1.0 if the average is under 0.001) | None (presets use thresholds around 1.0) | Volume-independent by construction; no section dynamics beyond about 4 s |
| WLED AR, AGC off (default) | DC-removed abs level, exponentially smoothed; 16 FFT channels | Nothing (fixed gain) | GEQ rise 0.75 / fall 0.17 per ~21 ms; limiter 80 ms / 1.4 s on volume | Wideband gain plus fixed pink tilt | Manual squelch gate | Gain 1–255 (−20 to +16 dB), squelch, input level | Must re-tune per source and room |
| WLED AR, Normal / Vivid / Lazy | as above | `sampleMax` peak via PI to setpoints 112–164 and 216–224 of 255 | Peak decay 3.3 / 1.3 / 6.7 s; follow slow 12.3 / 8.2 / 16.4 s, fast 0.38 / 0.26 / 0.51 s; gain clamp 1/64–32 | Wideband scalar `multAgc` | Requires squelch; integrator spins down | Preset choice | Docs: Lazy for GEQ and "wide dynamic range"; Vivid for "more blinken" |
| FastLED `AutoGain` | Input RMS | Peak envelope via PI to a target RMS | 10 ms attack; WLED preset decays | Wideband | Integrator spin-down below RMS 10 | Preset or custom | Design note: avoid fast automatic gain ("cross-band coupling") |
| LedFx | Mel bank (power-law "peak isolation") | Max of the blurred bank (`mel_gain`) | Instant / alpha 0.01 per frame (about 1.7 s if 60 fps; LedFx rate unverified) | Wideband scalar plus fixed pre-emphasis | dB-SPL `min_volume` gate zeroes the spectrum | Per-effect "sensitivity" (= smoothing speed) | No LedFx issue found in budget |
| Scott Lawson ARLS | Mel bank | `mel_gain` (wideband) and per-bin `gain` | 1.7 s (wideband); about 17 s per-bin at 60 fps | Both, depending on effect | 1e-7 peak gate | None | — |
| Philips Hue Sync | Unknown (digital system audio) | Unknown | "Intensity" = speed of change | Unknown | Unknown | Intensity (4 levels), brightness | — |
| Nanoleaf Rhythm | Microphone loudness and beat | Appears absolute (reviewer: response scales with loudness) | Unknown | Unknown | Sensitivity slider | Sensitivity slider; Sound or Beat mode | Quiet music: no reaction; high sensitivity: constant triggering (third-party) |
| Twinkly Music | Microphone, DSP, BPM | Claimed automatic sensitivity | Unknown | Unknown | Unknown | None found | — |
| Resolume / grandMA / TouchDesigner | FFT bands or level | Nothing (manual) | User Fall / Sound Fade / Smooth | Per-parameter or per-band manual | Manual threshold | Gain fader (master and per-parameter) | Resolume users dispute the v6/7 "Fall" behaviour |
| SoundSwitch | Offline track analysis | n/a | n/a | n/a | n/a | Scripting | Scripting large libraries is impractical (user) |

---

## Patterns that work / anti-patterns

### Patterns that work (with evidence)
1. **Hard floor under any auto-ranger.** Stop raising gain below a fixed level so silence and room noise never fill the display: Sensory Bridge `goertzel_max_value ≥ 4.0`, Emotiscope `≥ 0.0025`, WLED gain ≤ 32 — [GDFT.h L188](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/GDFT.h#L188-L190); [goertzel.h L321](https://github.com/connornishijima/Emotiscope/blob/main/src/goertzel.h#L321-L324); [audio_reactive.cpp L1030-L1031, L1054-L1055](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L1030-L1031).
2. **Exactly one adaptive gain stage, wideband.** WLED applies one `multAgc` to both volume and GEQ. FastLED's port explicitly warns against fast automatic gain because of cross-band coupling — [audio_reactive.cpp L657](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L657); [auto_gain.h](https://github.com/FastLED/FastLED/blob/master/src/fl/audio/auto_gain.h#L20-L25).
3. **Slow automatic gain whose job is source and room level, not music.** Use a slow normal-zone follow (12–16 s) and switch to a fast rate only near clipping or the floor — [WLED agcAvg](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L1044-L1050); [FastLED design note](https://github.com/FastLED/FastLED/blob/master/src/fl/audio/auto_gain.h#L20-L25). WLED recommends this (Lazy) for dynamic music — [kno.wled.ge](https://kno.wled.ge/advanced/audio-reactive/).
4. **Fixed spectral tilt rather than per-band automatic gain** to balance bass against treble: WLED `fftResultPink`, LedFx pre-emphasis — [L223](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L223); [audio.py L731-L743](https://github.com/LedFx/LedFx/blob/main/ledfx/effects/audio.py#L731-L743).
5. **Separate the release (fall) control from level.** Every professional tool exposes fall or decay separately from gain (Resolume Fall, grandMA Sound Fade, TouchDesigner Smooth); WLED has its dynamics limiter — [Resolume](https://resolume.com/support/en/6/parameter-animation); [grandMA3](https://help.malighting.com/grandMA3/2.2/HTML/sound_viewer.html).
6. **Tell the user when the input is outside the auto-ranger's range** instead of silently failing: the Sensory Bridge sweet-spot LEDs — [README](https://github.com/connornishijima/SensoryBridge/blob/main/README.md).
7. **Integrator spin-down in silence**, so the automatic gain does not wind up toward its maximum during pauses — [WLED L1016-L1021](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L1016-L1021).
8. **Long-memory reference for brightness-like outputs.** Sensory Bridge's VU-dot uses a fast-up, roughly minute-long decay, which keeps chorus against verse contrast — [lightshow_modes.h L189-L197](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/lightshow_modes.h#L189-L197). Evidence is the code only; no user evaluation found.

### Anti-patterns (with evidence or direct consequence of the code)
1. **Short-max normalisation driving brightness** (release of about 1–3 s: Sensory Bridge spectrogram, Emotiscope, LedFx, WLED Vivid). Any section longer than a few seconds is rescaled to full range, so a quiet breakdown ends up as bright as the drop. This follows from the constants cited in Q1. WLED's own docs steer dynamic material away from the fast preset — [kno.wled.ge](https://kno.wled.ge/advanced/audio-reactive/).
2. **Several adaptive gain stages in series.** No prior-art system does this (inference from the code reviewed). Each stage's release removes more of the remaining dynamics, and interacting time constants cause pumping.
3. **Per-band automatic gain on brightness or colour.** It destroys the spectral balance, timbre and the colour cue, and boosts empty bands. Only MilkDrop does per-band normalisation, and it uses the result for motion, not luminance — [MilkDrop guide](https://www.geisswerks.com/milkdrop/milkdrop_preset_authoring.html). FastLED explicitly warns about cross-band coupling in fast automatic gain — [auto_gain.h](https://github.com/FastLED/FastLED/blob/master/src/fl/audio/auto_gain.h#L20-L25).
4. **Automatic gain without a correct floor or squelch.** WLED documents that squelch must be set before the automatic gain, or the gain amplifies ambient noise — [kno.wled.ge](https://kno.wled.ge/advanced/audio-reactive/).
5. **Calibration by max-hold over a window that may contain music.** Sensory Bridge's per-bin noise and sweet-spot floors take the maximum seen during calibration, with ×1.5 and ×1.1 margins. Music during calibration permanently raises the floors and mutes quiet material — [GDFT.h L121-L146](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/GDFT.h#L121-L146).
6. **Adaptive floors that learn from the music itself.** Emotiscope's 10 s per-bin floor and 5 s VU floor remove sustained notes and make steady loud music read low. This is acceptable for an onset-driven show, wrong for a level or brightness cue — [CHANGELOG_1.1.md](https://github.com/connornishijima/Emotiscope/blob/main/extras/CHANGELOG_1.1.md); [vu.h L41-L60](https://github.com/connornishijima/Emotiscope/blob/main/src/vu.h#L41-L60).
7. **"Sensitivity" controls that mean different things.** It is a gain in Sensory Bridge, a smoothing speed in LedFx and a trigger threshold in Nanoleaf. Users of Nanoleaf report both under- and over-triggering — [energy.py](https://github.com/LedFx/LedFx/blob/main/ledfx/effects/energy.py#L23-L45); [trunetto](https://www.trunetto.com/troubleshooting/smart-lighting/nanoleaf/nanoleaf-rhythm-module-triggering-background-noise).
8. **Hard clipping before analysis.** Sensory Bridge clips at ±32767 after the SENSITIVITY multiply, so too much gain flattens loud dense music before any auto-ranger sees it. The sweet-spot "too loud" LED exists for this — [i2s_audio.h L69-L75](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/i2s_audio.h#L69-L75).
