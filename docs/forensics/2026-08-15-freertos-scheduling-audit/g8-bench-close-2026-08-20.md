---
abstract: "G8 closed on bench B489A500. Captain 2026-08-20 approved the integrated HEAD plus honour-on-k1_hardware. Flash k1_bench_im69d @ 69e21140. F887 copy deferred. AP-input P4 stays a separate programme."
---

# G8 bench close — 2026-08-20

Captain GO (same turn): resolve the palette-safe resolver lane; promote
`K1_EDGE_PALETTE_HONOUR_V1` onto `k1_hardware`; flash the resolver onto B489;
close G8 on the bench; leave AP-input P4 open.

## Host

```
HEAD                  = 69e21140
pytest                = 1426 passed, 1 skipped
pio-build k1_hardware = SUCCESS
GATE0_TRUST_ROOT      = PASS files=6
k1_hardware.bin       = sha256 ba8e27deec9f576d1dc88aadf9180533084ee707860c891f99538ee080e06c39
                        size 713344 (post-honour provenance)
```

Honour flag is on `[env:k1_hardware]`. The other five colour-fix flags stay
leak-blocked.

## Device (G8 surface = bench, not F887)

```
IDENTITY OK: git=69e21140 env=k1_bench_im69d epoch=1787164605
CHIP ID: B489A500
USB: B4:3A:45:A5:89:B4
port: /dev/cu.usbmodem1101   (drift; registry 12401 is stale this session)
SYSTEM_FPS: 136.63
LED_FPS: 202.34
CAL_SOURCE: persisted_profile
CAL_VALID: 1
EDGE_MODE: split
EDGE_EFFECTIVE_SECONDARY: split_palette
EDGE_EFFECTIVE_PRIMARY: split_palette
```

`split_palette` (not `untouched`) is the serial proof that the palette-safe
resolver is live. Cal inherited. No `start_noise_cal`. Main RPL `9087A500` on
`/dev/cu.usbmodem1401` remains `k1_main_rpl_im69d` @ `79d220fa`. Unit 2 and
F887 not touched.

Guard: *verified as 2nd bench K1 (B4:3A:45:A5:89:B4, chip B489A500)*.

## Rollback

- B489 look / honour-bypass restore: `k1_bench_im69d` @ `573206c0`
- Honour off `k1_hardware`: delete the `-DK1_EDGE_PALETTE_HONOUR_V1` line on
  that env (child RPL/bench `-D` lines stay)

## Residuals (named, not withholds)

1. `F887_PRODUCTION_FLASH` when `F887A500` returns — copies this HEAD onto
   `k1_hardware` silicon. Captain token still required.
2. Gate 5 capture→photon causal trace remains `NOT_PROVEN`.
3. Remaining five colour-fix flags stay off shippable envs.
4. AP-input-integrity P4 stays a separate open programme.
