# K1 Look Library — Phase C VP budget probe

**Status:** procedure only. Do not flash or probe until Captain names a GO.

**Device:** Main RPL, chip `9087A500`, env `k1_main_rpl_im69d` only.

## Already in source

- Slot 0 identity apply is a return (no 17³ cost on the boot path).
- Slot 8 is a teal–orange 17³ proof cube installed in PSRAM at boot. Not default.
- `k1_look_xfade_u16` is declared and unused (u16-domain lerp only if named).

## Probe (Captain GO, then agent)

1. **Captain:** named probe GO. No `start_noise_cal`.
2. **Agent:** serial `SYSTEM_FPS` at boot slot 0 (expect ~135, not the old ~78 hole).
3. **Captain:** type `:look=8`. Agent records FPS for ≥10 s.
4. If FPS sags toward ~78, keep type-4 off the default slot. Do not move look to Core 0.

## Stamp that means C timing closed

Slot 0 FPS still healthy, and a named `:look=8` FPS line is in this pack. Default remains 0.
