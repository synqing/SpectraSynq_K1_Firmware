# K1 Look Library — LGP plate measurement (Phase D)

**Status:** procedure only. Slot 3 stays **IDENTITY** until this pack contains a
measured chart and a host-verified `.klut`. Do not invent a film grade.

**Device:** Main RPL, chip `9087A500`, env `k1_main_rpl_im69d`.
**Do not** copy the WS2816 inverse-gamma onto bench `k1_bench_im69d` / B489.

## Already on silicon / in source

- Slot 0: identity (last night).
- Slot 1: cube-spaced WS2816 inverse-gamma.
- Slot 2: tungsten RGB 1D (R 1.18 / G 1.00 / B 0.78).
- Slot 3: identity placeholder for the measured plate print.

## What to capture (Captain + agent)

1. **Captain:** lock camera / meter: same tripod, same exposure, same white
   balance, lights in the room held. No auto-gain.
2. **Captain:** plate at identity (`:look=0`), then tonight (`:look=1`), then
   bench K1 WS2812B if a match argument is required.
3. **Agent:** store RAW/JPEG + meter CSV in this directory. Name files
   `identity_*.` `look1_*.` `bench_*`.
4. **Agent:** build a 1D RGB or 17³ `.klut` **from those files only**. Host
   verify CRC, monotone, endpoints 0/65535.
5. **Captain:** named load GO. Agent loads slot 3. Boot remains slot 0.
6. **Captain:** eyes-on PASS. Stamp the device-build registry.

## Stamp that means shipped

Slot 3 type is no longer IDENTITY, the `.klut` SHA is recorded here, and
Captain eyes-on PASS is written in this pack.

## Forbidden

- Authoring a “Kodak” / “teal-orange” cube and calling it measured.
- Flashing F887 / B489 with the WS2816 table to “match.”
- `start_noise_cal`.
