# Gate 3 — Coherent K1AudioFrame

**Date:** 2026-08-17  
**Silicon:** bench `B489A500` `/dev/cu.usbmodem12401` — `k1_bench_im69d` @ **`c671ddf3`** (epoch `1786912321`). Captain `B489_G3_FLASH`. Identity `IDENTITY OK: git=c671ddf3 env=k1_bench_im69d epoch=1786912321`. F887 / 1101 untouched.

```text
G3_HOST                 = CLOSED
G3_SIDECAR_FREEZE       = ON_SILICON (c671ddf3)
G3_DEVICE_PERCEPTUAL    = CLOSED 2026-08-17 (Captain: still looks good, call it a pass)
G3_LOCK_MARGIN_CAPTURE  = NOT_TAKEN (production binary keeps lock stats in RAM; no serial dump this flash)
```

Candidate A: Core 0 publishes one private frame per hop; Core 1 acquires once at frame top. Tempo, onset, snapshot and spectrogram copy under the same spinlock as the frame. VP bundle does not re-read live AP producers.

**Ship path:** G3 perceptual CLOSED. Next = G7B on bench `B489A500`. G8 waits until Captain has a replacement main unit; that `F887_PRODUCTION_FLASH` is shipped.
