"""Host model for the K1 noise-calibration quality gate.

This mirrors the firmware thresholds used to decide whether a user-confirmed
calibration window is accepted, rejected, or restored to the previous profile.
It is not an audio simulator; it is a deterministic model of the acceptance
contract around Phase-A DC and Phase-B SSL.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median


DC_PHASE_A_FRAMES = 128
SAMPLES_PER_CHUNK = 96
DC_MIN_VALID_RATIO_NUM = 3
DC_MIN_VALID_RATIO_DEN = 4
DC_MAX_VALID_ABS = 12000
SAMPLE_RAIL_THRESHOLD = 32000

SSL_PHASE_B_MAX_RAW = 1500.0
SSL_PHASE_B_MIN_ACCEPTED_FRAMES = 96
SSL_TRUSTED_P90_MAX_RAW = 650.0
SSL_MAX_P90_TO_P50_RATIO = 2.50
SSL_MIN_VALID_RAW = 50
SSL_MAX_VALID_RAW = 720


@dataclass(frozen=True)
class NoiseCalDecision:
    accepted: bool
    reason: str
    dc_offset: int = 0
    sweet_spot_min: int = 0
    ssl_p50: float = 0.0
    ssl_p90: float = 0.0


def percentile_floor(values: list[float], numerator: int, denominator: int = 10) -> float:
    if not values:
        raise ValueError("percentile requires values")
    ordered = sorted(values)
    index = ((len(ordered) - 1) * numerator) // denominator
    return ordered[index]


def decide_noise_calibration(dc_samples: list[int], phase_b_peaks: list[float]) -> NoiseCalDecision:
    expected_dc = DC_PHASE_A_FRAMES * SAMPLES_PER_CHUNK
    min_dc = (expected_dc * DC_MIN_VALID_RATIO_NUM) // DC_MIN_VALID_RATIO_DEN
    valid_dc_samples = [sample for sample in dc_samples if abs(sample) <= SAMPLE_RAIL_THRESHOLD]
    if len(valid_dc_samples) < min_dc:
        return NoiseCalDecision(False, "dc_samples")

    dc_offset = int(sum(valid_dc_samples) / len(valid_dc_samples))
    if abs(dc_offset) > DC_MAX_VALID_ABS:
        return NoiseCalDecision(False, "dc_range", dc_offset=dc_offset)

    accepted_peaks = [peak for peak in phase_b_peaks if peak <= SSL_PHASE_B_MAX_RAW]
    if len(accepted_peaks) < SSL_PHASE_B_MIN_ACCEPTED_FRAMES:
        return NoiseCalDecision(False, "ssl_samples", dc_offset=dc_offset)

    p50 = percentile_floor(accepted_peaks, 5)
    p90 = percentile_floor(accepted_peaks, 9)
    learned_ssl = int(p90 * 1.10 + 0.5)
    p90_to_p50 = (p90 / p50) if p50 > 1.0 else p90

    if p90 > SSL_TRUSTED_P90_MAX_RAW:
        return NoiseCalDecision(False, "ssl_too_loud", dc_offset=dc_offset, ssl_p50=p50, ssl_p90=p90)
    if p90_to_p50 > SSL_MAX_P90_TO_P50_RATIO:
        return NoiseCalDecision(False, "ssl_unstable", dc_offset=dc_offset, ssl_p50=p50, ssl_p90=p90)
    if learned_ssl < SSL_MIN_VALID_RAW or learned_ssl > SSL_MAX_VALID_RAW:
        return NoiseCalDecision(False, "ssl_range", dc_offset=dc_offset, ssl_p50=p50, ssl_p90=p90)

    return NoiseCalDecision(
        True,
        "none",
        dc_offset=dc_offset,
        sweet_spot_min=learned_ssl,
        ssl_p50=p50,
        ssl_p90=p90,
    )


def summarise_peaks(peaks: list[float]) -> dict[str, float]:
    if not peaks:
        return {"min": 0.0, "median": 0.0, "p90": 0.0, "max": 0.0}
    return {
        "min": min(peaks),
        "median": float(median(peaks)),
        "p90": percentile_floor(peaks, 9),
        "max": max(peaks),
    }
