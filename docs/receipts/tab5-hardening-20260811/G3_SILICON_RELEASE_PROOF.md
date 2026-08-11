# G3 silicon release proof — 2026-08-11

## Verdict

**DEPLOYED FIX VERIFIED. HARDENING LANE CLOSED.**

This receipt closes the Tab5 WDT/RSSI repair and its bounded reconnect proof. It
does not override the standing Deck16 production/promotion authority.

```text
DECK16_B1_B2_CORE_FUNCTIONAL_PASS=PASS
EXTENDED_RECOVERY_HARDENING=PASS
STANDBY_DIMMING=STRUCK
PRODUCTION_READY=NO
MERGE_OR_PROMOTION=HOLD
```

## Flashed target

- Device: ESP32-P4 revision 1.0
- Port used: `/dev/tty.usbmodem12401`
- MAC: `30:ed:a0:e0:c1:a0`
- Source commit: `87d4091addc40c4ed591097dd17048a25d23ec5a`
- Firmware ELF SHA-256: `d12a7e0e35714936b331a30edcdf7ce97de7be481ee72d26c21b8f9b9b4b50e4`
- Firmware BIN SHA-256: `806ec0222ce705c352ff529854f529310ca71679d9048e428c618c1cd92cb000`
- Esptool verified every written region by hash.

## Hardware results

- 100/100 P4 reset, BLE reconnect, HELLO, complete SNAPSHOT, and `ARMED`
  cycles passed in 1042.729 seconds.
- Fatal signatures: 0.
- Every accepted cycle reported `armed=1`, `desync=0`, `recovery=0`, and one
  committed snapshot.
- Eleven memory samples were captured. First and last were identical:
  DRAM 121 KB used / 181 KB free; SPIRAM 2124 KB used / 30643 KB free.
- Production transport status reported zero queue drops, duplicate connects,
  RSSI timeouts, and stale RSSI completions.
- No task watchdog, LVGL assertion, panic, Guru Meditation, unexpected reboot,
  or `BLE_ERR_UNK_CONN_ID` storm occurred.
- Deliberate identity-MD5 corruption caused repeated K1 rejection/disconnect as
  expected. Restoring the exact identity recovered to a second complete
  snapshot with `ARMED=1`, `desync=0`, and stable memory.

Machine-readable evidence:
`docs/receipts/tab5-hardening-20260811/g3-reconnect-100.json`.

## Closed boundary

No C6 flash, main K1 flash, full71 intervention, IM69D authority rewrite, or
global lane promotion was performed. The attempted additional ordinary-soak
harness was discarded and is not part of the release evidence.
