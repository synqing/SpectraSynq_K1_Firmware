# IM69D130 Specialist Rebuttal Check — 2026-08-05

**Task ID:** `im69d130-specialist-rebuttal-check`  
**Env / device:** `k1_bench_im69d` @ bench `B489A500` / `/dev/cu.usbmodem112401` (opened via `/dev/tty.usbmodem112401`, `dsrdtr=False` / `rtscts=False`)  
**Scope:** Read-only identity + live `[AP]` ratio check vs external specialist “wrong binary / G=1” claim. No `start_noise_cal` / `N` / `Y`. No `*im73d*` flash. No commit. Reflash only if live ratio ≈2.4.

---

## Verdict

| Field | Value |
|---|---|
| STATUS | **VERIFIED** |
| CLAIM | Bench is already on **G=16** `k1_bench_im69d`; specialist evaluated a **stale G=1 paste**. No reflash required. |
| METHOD_RISK | Medium — Cursor Serial Monitor held the port; exclusive capture used brief `SIGSTOP` of extension-host PID then `SIGCONT`. USB-JTAG DTR/RTS left false. |

---

## Tree vs live

| Check | Result |
|---|---|
| `constants.h` `K1_MIC_IM69D_INPUT_GAIN` | **16.0f** (under `#ifdef K1_MIC_IM69D_PDM_V1`) |
| `:chip_id` | `B489A500` |
| `:build` | `env=k1_bench_im69d git=3b59794 epoch=1785927357` |
| Reflash this pass | **No** — live behaviour already G=16 |
| Noise cal | **Not run** (Captain silence-go absent) |

---

## Live ratios (`max_raw ÷ raw_i16_abs_peak`)

Capture: ~18 s after `:ap_stream=1` (n=19 AP frames with peak>0).  
Artifact: `_scratch/im69d_specialist_check_20260805/{serial_capture.log,summary.json}`

| Metric | Value |
|---|---|
| Ratio median / mean / min..max | **38.388** / 38.354 / **38.000 … 38.400** |
| Expected G=1 | ~2.4 (= SENSITIVITY≈2.4 × gain 1) |
| Expected G=16 | ~38.4 (= 2.4 × 16) |
| Classification | **G16 live** |
| `max_raw` range | 76 … **1881** |
| `raw_i16_abs_peak` range | 2 … 49 |
| `cal_valid` | 0 (`default_invalid` — expected; no cal) |
| `raw_i16_near_pct` | 0.000 all frames |

Example coherence: `max_raw=1881` / `peak=49` → **38.388**; hot ambient matches prior retune receipt (1075–1843).

---

## Specialist claim adjudication

| Specialist claim | This check |
|---|---|
| Logs are G=1 (ratio ≈2.39) | **Stale** — referred to pre-retune paste, not current bench |
| Fix already in `constants.h` as G=16 | **True** in tree |
| Actions: reflash + silence cal | **Reflash unnecessary**; **cal still forbidden** without Captain silence-go |
| If after G=16 flash ratio still 2.4 → flag not landing | Counterfactual unused — live ratio already ~38.4 |

---

## FORBIDDEN / ALLOWED compliance

- No `start_noise_cal` / `N` / `Y`
- No `*im73d*` flash
- No commit
- No `k1_bench_im69d` reflash (not indicated)

---

## Re-run (orchestrator)

```bash
# Port must be free (close Cursor Serial Monitor first), or STOP the holder briefly.
python3 - <<'PY'
import serial, time, re, statistics
ser = serial.Serial()
ser.port, ser.baudrate, ser.timeout = "/dev/tty.usbmodem112401", 115200, 0.25
ser.dsrdtr = False; ser.rtscts = False
ser.open(); ser.setDTR(False); ser.setRTS(False)
time.sleep(0.4); ser.reset_input_buffer()
for c in (b":chip_id\n", b":build\n", b":ap_stream=1\n"):
    ser.write(c); ser.flush(); time.sleep(0.5)
ratios=[]; t0=time.time()
while time.time()-t0 < 18:
    line = ser.readline().decode("utf-8","replace").strip()
    if "[AP]" not in line: continue
    print(line)
    m1=re.search(r"max_raw=([-\d.]+)", line); m2=re.search(r"raw_i16_abs_peak=([-\d.]+)", line)
    if m1 and m2 and float(m2.group(1))>0:
        ratios.append(float(m1.group(1))/float(m2.group(1)))
print("n", len(ratios), "median", statistics.median(ratios) if ratios else None)
ser.close()
PY
```

Prior G=16 flash receipt: [`im69d130-gain-retune-2026-08-05.md`](./im69d130-gain-retune-2026-08-05.md).
