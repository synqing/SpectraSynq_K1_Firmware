---
abstract: "Bench device-proof runbook for the N7 on-device OTA receiver: anti-brick rollback AND (added on feat/n7-ota-signing) app-level RSA-3072 signature verification. Executes on the 2nd bench K1 (B489A500), NEVER the main K1 (F887A500) — except the brick-safe signature self-test (Stage 0), which may run on any unit. Proves: on-silicon signature verify (:ota_selftest); flag-ON OTA boots and marks its slot valid; a known-good SIGNED image accepted + self-validates after reboot; an unsigned/tampered image REJECTED at k1_ota_end (running image untouched); and — the load-bearing test — bootloader ROLLBACK to last-good slot on a signed-but-broken image. Image ingress is the EXISTING serial base64 transport (ota_datab64 + ota_sigb64) — no HTTP-over-AP build is required for the security proof (that is separate enablement-time wiring, gated on re-admitting the sb_* stack). NO hardware connected at authoring; run when a bench unit is attached. Enables OTA in NO shipping build; creates NO signing key."
---

# N7 OTA Bench Proof Runbook — anti-brick rollback verification

**Lane:** `feat/n7-rollback-prereq` (branched from the OTA DRAFT `feat/n7-ota-receiver`).
**Status at authoring:** PLAN ONLY. No hardware connected. Execute when a bench K1 is attached.
**Target device:** 2nd bench K1 — chip `B489A500`, USB serial `B4:3A:45:A5:89:B4`, port `/dev/tty.usbmodem12201`.
**NEVER the main K1** (`F887A500`, port `/dev/tty.usbmodem1401`). The bench proof is a brick-risk exercise; it stays on the disposable bench unit.

## Why this runbook exists

`SPECTRASYNQ_K1_FIRMWARE/system/k1_ota.cpp` is a **flag-OFF DRAFT** (`SB_ENABLE_OTA` defaults `0`). Its anti-brick guarantee is the call `esp_ota_mark_app_valid_cancel_rollback()` in `k1_ota_mark_app_valid_after_boot()`: once a freshly-flashed image proves it boots, it cancels the bootloader's pending rollback; if it never proves a healthy boot, the bootloader reverts to the last-good slot on the next reset. That guarantee is only real if the bootloader actually arms rollback at boot. This runbook proves it does, on hardware, before OTA is ever considered for enablement.

## Prerequisites already satisfied (verified 2026-06-30, this lane)

These were believed missing when the DRAFT was written (`k1_ota.h` enablement notes); they are in fact **already provided** by the pioarduino 54.03.20 / arduino-esp32 3.2.0 / ESP-IDF 5.4.1 toolchain:

1. **Rollback bootloader config** — `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y` and `CONFIG_APP_ROLLBACK_ENABLE=y` are already `=y` in the prebuilt `framework-arduinoespressif32-libs/esp32s3/sdkconfig` (lines 444 and 3750). The arduino framework ships a **precompiled** bootloader, so this repo's build does not recompile it; the config is baked into the shipped bootloader binary. `sdkconfig.defaults` in this lane pins the same two keys as an **intent / drift sentinel** only — it is byte-neutral to the product binary (see Blast-radius below).
2. **A/B OTA partition layout** — `board_build.partitions = default_16MB.csv` (the current `k1_hardware` table) already defines `app0` (subtype `ota_0`, 0x640000 = 6.5 MB), `app1` (subtype `ota_1`, 6.5 MB) and `otadata` (0x2000). No custom `partitions.csv` is required; `esp_ota_get_next_update_partition()` returns a valid inactive slot at runtime.
3. **Symbol linkage** — the flag-ON build (`k1_ota_probe`) links `esp_ota_begin`, `esp_ota_get_next_update_partition`, `esp_ota_set_boot_partition` and `esp_ota_mark_app_valid_cancel_rollback` at real text addresses (verified via `nm` on `firmware.elf`). The flag-OFF `k1_hardware` build contains **zero** OTA symbols.

### Blast-radius note (load-bearing)

Adding `sdkconfig.defaults` (rollback keys only) does **not** change the `k1_hardware` product binary content. Proven this lane: flag-OFF `firmware.bin` stays exactly **649,280 B**; a clean rebuild with `sdkconfig.defaults` present differs from the baseline in only 67 bytes, and a control rebuild **without** the file differs by an equivalent 68 bytes — both deltas are confined to the embedded build-timestamp string plus the two derived hashes that cascade from it (the `app_elf_sha256` field in `esp_app_desc_t` and the appended image hash). There is no code, rodata or partition difference. **Do not** add any IDF-source `sdkconfig` key that would force an "arduino-as-component" rebuild — that *would* recompile the bootloader/libs and alter the product binary, and must stay OTA-branch-only.

## Build envs for the proof

| Env | Device | Notes |
|-----|--------|-------|
| `k1_bench_ota_probe` | bench K1 `B489A500` / port 12201 | flag-ON OTA on the bench-reference GPIO pin-map; upload guard accepts the bench unit. **Use this for the proof.** |
| `k1_ota_probe` | main K1 `F887A500` / port 1401 | flag-ON OTA on the main pin-map; do NOT use for the brick-risk bench proof. |

`k1_bench_ota_probe` extends `k1_bench_reference` (bench GPIO map + `-DSB_K1_BENCH_REFERENCE_PINMAP=1`) and adds `-DSB_ENABLE_OTA=1`. It is registered in `scripts/platformio/k1_upload_guard.py` under the 2nd-bench-K1 target, so the guard refuses to flash it to the main K1.

## Pre-flight (before touching the bench unit)

1. Confirm the bench unit is the one connected. Enumerate USB serials; the proof port MUST report serial `B4:3A:45:A5:89:B4`. If it reports `B4:3A:45:A5:87:F8` you are on the main K1 — **STOP**.
2. Build both images in advance (host only, no upload):
   - Good image: `pio run -e k1_bench_ota_probe` → `.pio/build/k1_bench_ota_probe/firmware.bin`.
   - Bad image: take the good `firmware.bin`, copy it, and **truncate** it to ~50 % of its length (a deliberately corrupt app that fails `esp_ota_end()` image validation or panics on boot). Keep it clearly named, e.g. `firmware.bad.bin`. This synthetic corruption is a file-truncation only — no audio, no device interaction.
3. Have the serial monitor ready at 115200 on port 12201. The boot log identifies the running slot and the OTA state.

## Proof procedure

All uploads use the bench port `/dev/tty.usbmodem12201`. Reboots are power-cycle or the serial `reset` path — no other side effects.

### Stage 1 — flag-ON boots and marks its slot valid
1. Flash the good image to the bench unit:
   `pio run -e k1_bench_ota_probe -t upload --upload-port /dev/tty.usbmodem12201`.
2. Open the serial monitor. Confirm the device boots into a healthy app loop.
3. Confirm the running app calls `k1_ota_mark_app_valid_after_boot()` and the slot leaves `PENDING_VERIFY` (i.e. the boot is marked valid). Evidence: the boot/health log line emitted by that path, and the absence of an unexpected rollback on the next reset.
4. **Pass criterion:** device boots, runs, and the running slot is marked valid (no spontaneous rollback on a clean reset).

### Stage 2 — known-good OTA into the inactive slot, self-validates
1. With the device running, drive the OTA serial ingress (`ota_*` DRAFT verbs in `serial_cmd_dispatch_ota`) to stream the **good** `firmware.bin` into the inactive OTA slot: `k1_ota_begin()` → `k1_ota_write()` chunks → `k1_ota_end()` (sets the inactive slot as boot partition).
2. Reboot.
3. Confirm the device now boots from the **previously-inactive** slot, runs healthily, and marks that slot valid (cancels the armed rollback).
4. **Pass criterion:** the new good image becomes the running slot AND survives reboot because it self-validated. The slots have swapped.

### Stage 3 — deliberately-bad OTA rolls back (THE load-bearing anti-brick proof)
1. With the device running on a known-good slot, drive the OTA ingress to push the **truncated bad** image (`firmware.bad.bin`) into the inactive slot and set it as the next boot partition.
   - If `k1_ota_end()` rejects the image at validation time, that is a first-line defence (good) — to prove the *bootloader* rollback specifically, you may need an image that links/validates but fails to reach the "mark valid" point (e.g. boots then panics in early init before `k1_ota_mark_app_valid_after_boot()`). Document which failure mode you exercised.
2. Reboot.
3. Observe: the bad slot fails to prove a healthy boot, so it never calls `esp_ota_mark_app_valid_cancel_rollback()`. On the following reset the **bootloader rolls back** to the last-good slot.
4. Confirm via serial that the device is once again running the **last-good** image, not the bad one — the unit is NOT bricked.
5. **Pass criterion (anti-brick):** after pushing and booting a bad image, the device autonomously recovers to the last-good slot. If the device bricks (no recovery, requires a wired re-flash to revive), the rollback guarantee is **NOT** proven and OTA must not be enabled.

## Signature dimension (added on `feat/n7-ota-signing`, 2026-07-07)

The child branch `feat/n7-ota-signing` adds an **application-level signature check** as
the security boundary: `k1_ota_end()` finalises the whole-image SHA-256 and calls
`k1_ota_verify_signature()` (RSA-3072 / PKCS#1 v1.5, `mbedtls_pk_verify` against the
embedded `certs/k1_ota_signing_PUBLIC.pem`). The boot partition flips ONLY if the
detached signature verifies. This is verify-only — **no eFuse, no Secure Boot** — so it
is reversible. Host proof (2026-07-07, Captain's real key): a signed blob → `Verified OK`;
a one-byte tamper → `bad signature`.

**Ingress already exists — do NOT build a transport first.** `serial_cmd_dispatch_ota()`
implements `ota_datab64` (base64 image chunks) and `ota_sigb64` (fragmented base64
signature; the 384-byte sig is streamed across several ≤94-byte frames and concatenated).
This serial transport is sufficient for the full accept/reject/rollback proof below.
HTTP-over-AP ingress is a *nicety for field OTA*, not a prerequisite for this proof, and
is gated on re-admitting the held-out `network/sb_*.cpp` stack (a D3 / wireless-A/B
decision) — it is NOT in scope here.

### Stage 0 — on-silicon signature self-test (`:ota_selftest`) — BRICK-SAFE, any unit
Residual #1. Proves the exact production verify path runs identically on ESP32-S3 silicon.
No image is written and the boot partition is never touched, so this may run on the main
K1 as well as the bench.
1. Build + flash the flag-ON probe: `pio run -e k1_ota_probe -t upload --upload-port <port>`
   (or `k1_bench_ota_probe` on the bench). Confirm the guard prints the matching chip-ID.
2. On the serial console, issue `ota_selftest`.
3. **Pass criterion:** `OTA_SELFTEST: good=PASS tamper=REJECT verify=PASS`.
4. Restore the device's production build afterwards. Log the line in
   `docs/hardware/device-build-registry.md`.

### Signed-image proof — supersedes Stage 2's ingress note
Stage 2 (known-good OTA) MUST now also stream the detached signature, or `k1_ota_end()`
will correctly REJECT the image. Sequence: `ota_begin` → repeated `ota_datab64` (image) →
repeated `ota_sigb64` (signature fragments, in order) → `ota_end`. The signature is
produced offline by the operator (Captain action — the private key never leaves
`~/.k1_secrets/`): `openssl dgst -sha256 -sign ~/.k1_secrets/k1_ota_signing_PRIVATE.pem
-out image.sig <firmware.bin>`.

### Stage 2b — unsigned / tampered image REJECTED — BRICK-SAFE, any unit
The signature security boundary. Push a **complete, valid** image via `ota_datab64` but
supply NO signature (or a tampered `ota_sigb64` fragment), then `ota_end`.
**Pass criterion:** `[ota] end REJECT — image refused …`; the running image is untouched.
Because the running slot never changes, this leg cannot brick and may run on any unit.

The rollback leg (Stage 3) remains the only brick-risk test and stays **bench-only**.

## What this runbook does NOT do

- Does NOT enable OTA in any shipping build (`SB_ENABLE_OTA` stays `0` everywhere except the two probe envs).
- Does NOT create, hold, or commit any signing key, certificate, or secret. App-level
  signature *verification* (verify-only, no eFuse) IS now covered — see the Signature
  dimension above — but the PRIVATE key is Captain-custodied (`~/.k1_secrets/`, never in
  repo) and eFuse **Secure Boot** stays out of scope (irreversible; a human STOP below).
- Does NOT stand up a distribution/update server. The ingress proven here is the serial DRAFT transport, not a field OTA channel.
- Does NOT run on the main K1.

## Human decision STOPs before OTA can ship (irreversible — agent cannot resolve)

These are the highest-blast-radius decisions in the repo. An agent must not pre-empt any of them:

1. **OTA-in-v1 scope** — is on-device field OTA in the v1 product at all? If no, this entire lane stays DRAFT and the bench proof is archived as readiness evidence only.
2. **Signing-key custody** — if OTA ships, images MUST be signed and the bootloader MUST verify (secure boot / signed app). The signing key custody model is a human decision: HSM, a secrets manager, or an offline air-gapped signer. **The agent never generates or holds the key.** No key, certificate, or secret is created in this repo by this lane.
3. **Distribution source** — where do update images come from and how is their authenticity established end-to-end (server identity, transport security, version/anti-rollback policy)? None exists; none is created here.

Until all three are resolved by the Captain, OTA remains flag-OFF and this runbook is preparation, not authorisation.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:build-ssa | Created. Bench anti-brick rollback proof procedure on B489A500; documents that rollback config + A/B partitions are already framework-provided; records the sdkconfig.defaults byte-neutrality finding; adds k1_bench_ota_probe env + guard registration; enumerates the three human key-custody/scope STOPs. |
| 2026-07-07 | agent:claude-opus-4-8 (CTO) | Added the Signature dimension (feat/n7-ota-signing): Stage 0 on-silicon :ota_selftest (brick-safe), signed-image ingress via the EXISTING serial base64 transport (ota_datab64 + ota_sigb64 — corrects the "no transport" premise), Stage 2b unsigned/tampered REJECT (brick-safe). Clarified HTTP-over-AP is enablement-time only, not a proof prerequisite. Reframed the signing scope bullet (verify-only in scope; eFuse Secure Boot out). |
