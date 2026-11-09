"""Lane A5: energy / novelty envelope for the candidate track.

Input: decoded s16le interleaved stereo PCM at 44100 Hz (ffmpeg -f s16le -acodec pcm_s16le).
Method:
  - mono = mean(L, R)
  - 0.5 s non-overlapping windows: RMS in dBFS
  - novelty = |RMS_dB[t] - mean(RMS_dB[t-8:t])| over 4 s look-back vs 4 s look-ahead
    (difference of mean dB in the 4 s after vs 4 s before each window boundary)
  - low-band (<150 Hz) energy ratio per window via FFT, to locate kick drop-outs (breakdowns)
Prints per-second table and the strongest boundaries inside the search range.
"""
import sys
import numpy as np

path, rate, ch = sys.argv[1], 44100, 2
lo_s, hi_s = float(sys.argv[2]), float(sys.argv[3])
x = np.fromfile(path, dtype="<i2").astype(np.float64).reshape(-1, ch).mean(axis=1) / 32768.0
frames = len(x)
win = rate // 2
n = frames // win
seg = x[: n * win].reshape(n, win)
rms_db = 20 * np.log10(np.sqrt((seg ** 2).mean(axis=1)) + 1e-9)
spec = np.abs(np.fft.rfft(seg * np.hanning(win), axis=1)) ** 2
freqs = np.fft.rfftfreq(win, 1 / rate)
low_ratio = spec[:, freqs < 150].sum(axis=1) / (spec.sum(axis=1) + 1e-12)
K = 8  # 4 s each side
bound = np.zeros(n)
for i in range(K, n - K):
    bound[i] = rms_db[i : i + K].mean() - rms_db[i - K : i].mean() + 10 * (
        low_ratio[i : i + K].mean() - low_ratio[i - K : i].mean()
    )
print(f"frames={frames} duration_s={frames / rate:.6f}")
print("t_s  rms_dB  low150_ratio")
for i in range(0, n, 2):
    t = i * 0.5
    if lo_s - 4 <= t <= hi_s + 4:
        print(f"{t:6.1f} {rms_db[i]:7.2f} {low_ratio[i]:.3f}")
idx = [i for i in range(n) if lo_s <= i * 0.5 <= hi_s]
order = sorted(idx, key=lambda i: -abs(bound[i]))
print("strongest boundaries (t_s, score = dB step + 10*low-ratio step; +ve = rise):")
seen = []
for i in order:
    if all(abs(i - j) > 8 for j in seen):
        seen.append(i)
        print(f"  t={i * 0.5:6.1f}  score={bound[i]:+.2f}")
    if len(seen) >= 6:
        break
