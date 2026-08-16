# Gate 3 — Coherent K1AudioFrame

**Date:** 2026-08-17  
**HEAD at land:** `e911f86d` plus this session's sidecar freeze  
**Silicon:** `k1_bench_im69d` @ `e911f86d` already carried `K1_AUDIO_FRAME_V1`. Captain eyes-on PASS on that binary (G2 close) is the perceptual stamp for the frame publication already on silicon. The sidecar freeze (tempo/onset/snapshot/spectrogram copied under the same spinlock) is **source on this branch**, not yet on silicon.

```text
G3_HOST                 = CLOSED
G3_DEVICE_PERCEPTUAL    = CLOSED for the e911f86d frame publication (same binary as G2 PASS)
G3_SIDECAR_FREEZE       = IN_SOURCE (not on silicon until named B489_G3_FLASH)
G3_LOCK_MARGIN_CAPTURE  = NOT_TAKEN (needs named B489_G3_FLASH GO)
```

Candidate A: Core 0 publishes one private frame per hop; Core 1 acquires once at frame top. Tempo, onset, snapshot and spectrogram copy under the same spinlock as the frame. VP bundle does not re-read live AP producers (`k1_vp_audio_access.cpp` uses `k1_audio_frame_copy_acquired_sidecars`).

Host: `tests/test_k1_audio_frame_interleave.py` plus `tests/test_k1_audio_frame_ownership_static.py`.

**Ship path:** named `B489_G3_FLASH` of this branch HEAD on bench `B489A500` only. That flash is the lock-margin capture. No F887 flash.
