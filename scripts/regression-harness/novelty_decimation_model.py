"""Host model of the AP novelty -> tempo decimation (k1_tempo.cpp:1280-1326).

Faithfully mirrors the firmware's peak-hold downsampler so a host test can
assert the behaviour without compiling the full tempo unit. The decimation
constant is parity-checked against the firmware #define by the test, so this
model cannot silently drift from the contract.

Firmware logic mirrored:
  - prime on first call (no emit)
  - peak-hold accumulate every AP frame:  if novelty > accum: accum = novelty
  - emit every K1_NOVELTY_DECIMATION-th frame: sample = accum; accum = 0
The peak-hold is the firmware's anti-alias mechanism: it aggregates ALL frames
in the decimation window (preserving onset spikes), it does NOT pick every Nth
raw sample. A linear pre-decimation low-pass is intentionally ABSENT because it
would smear onset transients and regress beat detection.
"""

# Default mirrors config_types.h:  #define K1_TEMPO_NOVELTY_DECIMATION 3U
DEFAULT_DECIMATION = 3


class PeakHoldDecimator:
    """Mirror of the firmware peak-hold downsampler."""

    def __init__(self, decimation=DEFAULT_DECIMATION):
        if decimation < 1:
            raise ValueError("decimation must be >= 1")
        self.decimation = decimation
        self._primed = False
        self._accum = 0.0
        self._frame_ctr = 0

    def update(self, novelty):
        """Feed one AP-frame novelty value. Returns the emitted sample or None."""
        novelty = 0.0 if novelty < 0.0 else (1.0 if novelty > 1.0 else novelty)

        if not self._primed:
            self._primed = True
            self._accum = novelty
            self._frame_ctr = 0
            return None

        if novelty > self._accum:
            self._accum = novelty

        self._frame_ctr += 1
        if self._frame_ctr < self.decimation:
            return None

        self._frame_ctr = 0
        sample = self._accum
        self._accum = 0.0
        return sample


def naive_every_nth(novelty_stream, decimation=DEFAULT_DECIMATION):
    """The WRONG decimator the task warns about: pick every Nth raw sample,
    dropping the in-between frames unchanged. Used only as a contrast baseline."""
    out = []
    for idx, v in enumerate(novelty_stream):
        # idx 0 is the prime frame in the peak-hold model; align by emitting on
        # the same frames the peak-hold model emits (every Nth after prime).
        if idx >= 1 and (idx % decimation == 0):
            out.append(0.0 if v < 0.0 else (1.0 if v > 1.0 else v))
    return out


def run_stream(novelty_stream, decimation=DEFAULT_DECIMATION):
    """Run the peak-hold decimator over a stream, return the emitted samples."""
    dec = PeakHoldDecimator(decimation)
    out = []
    for v in novelty_stream:
        emitted = dec.update(v)
        if emitted is not None:
            out.append(emitted)
    return out
