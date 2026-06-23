#!/usr/bin/env python3
"""Deterministic synthetic-audio fixtures for render_replay (VE-Auto-Loop Tier 1).

Each fixture is NDJSON, one frame per line. RICH SCHEMA (single schema, every mode
reads its subset):
  {"frame": i, "ms": t,
   "chromagram": [c0..c11],              # bloom / waveform / waveform_fast / comet colour
   "spectrogram": [s0..s79],             # spectrum_river (its ONLY audio input)
   "waveform_peak_scaled": float,        # waveform / waveform_fast trail amplitude
   "max_waveform_val_raw": float,        # waveform_fast reactive-dot gate (must be > floor)
   "bass_onset": 0|1,                    # comet kick trigger (edge-detected by event_id)
   "bass_onset_strength": float,         # comet head size
   "silence": bool}

The non-chromagram fields are DERIVED from the existing chromagram/energy so the
corpus stays musically coherent AND deterministic. The chromagram values are
BYTE-IDENTICAL to the prior (chromagram-only) fixtures — same values, same 4-dp
rounding — so BLOOM's render is unchanged (verified: bloom self-test shas match).

DERIVATION (deterministic, no RNG):
  energy        = mean(chromagram)                              # 0..~1
  spectrogram   = 12 chroma bins fanned across 80 freq bins (bin k -> chroma[k*12//80]),
                  bass-tilted so low bins read brighter (river: bass wells at centre).
  waveform_peak = clamp(energy * 1.6, 0, 1)  on active frames, 0 in silence
                  (>= 0.08 reactive-peak floor whenever there's real energy).
  max_wf_raw    = energy > 0 ? 0.5 + energy : 0.0   (nonzero => waveform_fast dot draws;
                  the harness leaves SWEET_SPOT_MIN_LEVEL=0 so any >0 clears the floor).
  bass_onset    = periodic kick schedule (every BEAT_PERIOD frames on the down-pulse),
                  strength scaled by current energy. For musically-static fixtures the
                  schedule still fires so comet has motion to render.

PROVENANCE (map-territory honesty): these are SYNTHETIC structured stimuli, not real
-music captures. Real-music fixtures (wav->K1-GDFT chromagram+spectrogram+onset
extractor) are the documented Tier-1.5 follow-up. For MVP-0 these edge + structured
cases prove the harness end-to-end across all five modes.

Regenerate:  python3 fixtures/gen_fixtures.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MS = 1000.0 / (12800.0 / 96.0)  # 7.5 ms per AP frame
NUM_FREQS = 80
BEAT_PERIOD = 16    # frames between synthetic kicks (matches beat-pulse cadence)


def _energy(chroma):
    return sum(chroma) / 12.0


def _spectrogram(chroma):
    """Fan the 12 chroma bins across 80 freq bins, bass-tilted (low bins brighter).
    Deterministic; no RNG. bin k -> chroma[k*12//80] * tilt."""
    spec = []
    for k in range(NUM_FREQS):
        c = chroma[(k * 12) // NUM_FREQS]
        tilt = 1.0 - 0.5 * (k / (NUM_FREQS - 1))   # 1.0 at bass -> 0.5 at treble
        spec.append(round(c * tilt, 4))
    return spec


def frame(i, chroma, silence=False, force_kick=None):
    """Build one rich frame. `chroma` is the 12-bin chromagram (the colour authority,
    kept byte-identical to the chromagram-only fixtures). All other fields derived."""
    e = _energy(chroma)
    # waveform amplitude: track energy, clear the 0.08 reactive-peak floor when lit.
    wf_peak = 0.0 if silence else round(min(1.0, e * 1.6), 4)
    # waveform_fast reactive-dot gate: any >0 clears the (SWEET_SPOT_MIN_LEVEL=0) floor.
    max_wf = 0.0 if e <= 0.0 else round(0.5 + e, 4)
    # comet kick: periodic schedule on the down-beat frame; explicit override wins.
    if force_kick is None:
        kick = (i % BEAT_PERIOD) == 0 and e > 0.0
    else:
        kick = bool(force_kick)
    bass_str = round(min(1.0, 0.3 + e), 4) if kick else 0.0
    return {
        "frame": i, "ms": int(round(i * MS)),
        "chromagram": [round(x, 4) for x in chroma],
        "spectrogram": _spectrogram(chroma),
        "waveform_peak_scaled": wf_peak,
        "max_waveform_val_raw": max_wf,
        "bass_onset": 1 if kick else 0,
        "bass_onset_strength": bass_str,
        "silence": bool(silence),
    }


def write(name, frames):
    p = HERE / name
    p.write_text("\n".join(json.dumps(f, sort_keys=True) for f in frames) + "\n", encoding="utf-8")
    return name, len(frames)


def main():
    out = []

    # 1. silence — idle/decay; bloom must stay black (golden A4 anchor). No kicks.
    out.append(write("silence.ndjson",
                     [frame(i, [0.0] * 12, silence=True) for i in range(24)]))

    # 2. single-note — one sustained bin; minimal colour, tests centre insert.
    out.append(write("single-note.ndjson",
                     [frame(i, [0.85 if j == 0 else 0.0 for j in range(12)]) for i in range(60)]))

    # NOTE on magnitudes (R-DRIVE): bloom double-squares its input (bin*bin*share,
    # then the SQUARE_ITER loop), so it is DIM for sparse notes and BRIGHT for dense
    # spectra (all-12-bins=1.0 -> white). The musical fixtures below use realistic
    # multi-bin density so the corpus visibly spans dim->bright. They are SYNTHETIC,
    # not real-music chromagrams — see the module docstring.

    # 3. chord — C-E-G triad (bins 0,4,7) high, with a real broadband floor.
    out.append(write("chord-major.ndjson",
                     [frame(i, [0.95 if j in (0, 4, 7) else 0.25 for j in range(12)]) for i in range(60)]))

    # 4. chroma-sweep — a 3-wide note cluster walks 0->11 (8 frames each); colour travel.
    sweep = []
    for i in range(96):
        active = (i // 8) % 12
        sweep.append(frame(i, [0.95 if j == active else (0.45 if abs(j - active) == 1 else 0.1)
                               for j in range(12)]))
    out.append(write("chroma-sweep.ndjson", sweep))

    # 5. beat-pulse — full triad pulses ON 4 frames / OFF 12 over a quiet floor;
    #    exercises motion memory (bloom decay, waveform trail, comet kick on each ON).
    pulse = []
    for i in range(96):
        on = (i % 16) < 4
        hi, lo = (0.95, 0.08)
        # fire a comet kick on the rising edge of each pulse (i % 16 == 0)
        pulse.append(frame(i, [(hi if on else lo) if j in (0, 4, 7) else (0.2 if on else 0.04)
                               for j in range(12)], silence=not on,
                           force_kick=((i % 16) == 0)))
    out.append(write("beat-pulse.ndjson", pulse))

    # 6. broadband-swell — all 12 bins ramp 0.2 -> 0.9 and back; drives bloom to
    #    near-white at the peak + a wide bright river; periodic kicks for comet.
    swell = []
    for i in range(96):
        t = i / 95.0
        lvl = 0.2 + 0.7 * (1.0 - abs(2.0 * t - 1.0))   # triangle 0.2..0.9..0.2
        swell.append(frame(i, [round(lvl, 4)] * 12))
    out.append(write("broadband-swell.ndjson", swell))

    for name, n in out:
        print(f"  {name}: {n} frames")
    print(f"wrote {len(out)} fixtures to {HERE}")


if __name__ == "__main__":
    main()
