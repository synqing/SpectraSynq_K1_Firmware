# Authored edit — intent declared before any comparison (PLAN A20), 2026-11-10

Edit: "bar accent". In the mapping profile's impact dimension (downbeat_accent_u16), lower
`beat_amp_u16` from 48000 to 12000. Downbeat pulses stay at 65535 / 60 ms.

Musical intent: the impact flash marks the bar, not every beat. Off-downbeat beats become a
faint tick (about 18% of full scale instead of 73%); bar starts keep full weight.

Predicted visible consequence in the Prim8 stream (stated before comparing):
1. Only Prim8[1] impact (device: novelty) changes. Prim8[0,2,3,4,5,6,7] byte-identical.
2. Changed frames lie only inside the 40 ms pulse window after each NON-downbeat beat
   (click fixture: beats at 0.5, 1.0, 1.5, 2.5 s; 3.0 s is at duration end, no frame).
   Downbeat windows (0.0 s, 2.0 s) unchanged.
3. Inside a changed window the new value = old value x 12000/48000 (linear ramp scaled by 1/4,
   allowing integer rounding of the VM's BigInt interpolation, +-1).
4. Frame count, seq and t_us unchanged; only Prim8 bytes 20-21 of the affected frames differ.
5. ShowBundle, Intent Trace and .prsm sha256 all change; coverage gate still PASS
   (impact remains dynamic MAPPED_REAL).
Limitation: the locked compiler and mapping_profile_v1 have no per-section scope, so the edit
applies to the whole composition (the click fixture has one section, "full").
