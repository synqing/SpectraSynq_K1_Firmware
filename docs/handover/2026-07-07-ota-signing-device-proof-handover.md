---
abstract: "OTA image-signing device-proof handover (2026-07-07, rev 2). The OTA signature SECURITY boundary is PROVEN end-to-end on host with Captain's REAL production key (signed image → Verified OK; tampered/unsigned → rejected, fail-closed; verify-only, no eFuse; private key never in repo). Branch feat/n7-ota-signing @ c34a0e9 (pushed), flag-OFF DRAFT, SB_ENABLE_OTA=0. Residual #1 (on-silicon self-test) is now CODE-COMPLETE + build-proven + committed (:ota_selftest verb) — only the on-device capture remains (brick-safe, any unit). Residual #2 is REFRAMED: a serial base64 image transport (ota_datab64 + ota_sigb64) ALREADY EXISTS — the accept/reject/rollback device-proof runs over it; HTTP-over-AP is NOT a prerequisite (separate enablement-time wiring gated on re-admitting the sb_* stack). Rollback leg = clean BENCH B489A500 only, never the main K1. READ before touching OTA."
---

# K1 OTA Image-Signing — Device-Proof Handover (2026-07-07, rev 2)

> **TL;DR** — OTA **signature security is proven** (host, Captain's real key: good→`Verified OK`, tampered→rejected, fail-closed). Residual #1 (on-silicon self-test) is now **built, build-proven and committed** (`:ota_selftest`) — only the on-device *capture* is left (brick-safe). Residual #2 is **not a transport build** — a serial base64 transport already exists; the security proof runs over it. HTTP-over-AP is a separate enablement item, not a proof prerequisite. Branch `feat/n7-ota-signing` @ `c34a0e9` (pushed, flag-OFF DRAFT). Do **not** ship (D3 Captain gate) and do **not** run the rollback brick-test on the main K1.

## 1. What is PROVEN (do not re-litigate)
- **Crypto scheme is real, not theatre** (orchestrator-reviewed the code, re-ran the crypto): whole-image **SHA-256** folded byte-by-byte in `k1_ota_write`; detached **RSA-3072 PKCS#1 v1.5** signature verified by `mbedtls_pk_verify(…, MBEDTLS_MD_SHA256, …)` against the **embedded operator PUBLIC key**; boot partition flips **only** if the signature verifies; **fail-closed** on every path (no sig / parse fail / wrong key type / verify fail → reject). Verify entry point: `k1_ota_verify_signature()` (k1_ota.cpp:48), called by `k1_ota_end()` (k1_ota.cpp:171).
- **Security boundary is correctly placed**: `esp_ota_end()` on this prebuilt arduino-esp32 lib does NOT verify signatures (`CONFIG_SECURE_SIGNED_ON_UPDATE` compiled out of `libbootloader_support.a`) — that is *why* the app-level RSA check in `k1_ota_end()` is the boundary. Necessary, not redundant.
- **Real-key end-to-end proof (host, 2026-07-07, re-run this session):** the operator-signed blob `k1-ota-proof\n` **verified against the firmware's committed/embedded public key** (`openssl dgst -sha256 -verify` → **`Verified OK`**); a 1-byte tamper → **`bad signature`**. Pubkey parses RSA-3072 / exp 65537.
- **Key hygiene:** production **public** key committed at `SPECTRASYNQ_K1_FIRMWARE/certs/k1_ota_signing_PUBLIC.pem` + embedded in `system/k1_ota_signing_public_key.h`. **Private key lives ONLY at `~/.k1_secrets/k1_ota_signing_PRIVATE.pem` (0600), never in git** (`*_PRIVATE.pem` / `*.key` gitignored, commit `dd83303`).
- **No eFuse / reversible:** signature verification WITHOUT Secure Boot (`CONFIG_SECURE_BOOT` never enabled). Nothing burned; fully reversible.
- **Byte-identical:** entire `system/k1_ota.cpp` TU is wrapped in `#if SB_ENABLE_OTA … #endif` (:7…:329); flag-OFF `k1_hardware` is byte-identical. Independently reconfirmed 2026-07-07 — the commit-gate rebuilt `k1_hardware` (flag-OFF) → SUCCESS, and 594 host tests passed.

## 2. Branch / build state
- **Branch `feat/n7-ota-signing` @ `c34a0e9`** (pushed). Parent chain: `cf406d6` (serial sig accumulation) → `48888a5` (signature verify) → `4cdab68` (`feat/n7-rollback-prereq`, rollback + runbook) → `d4a7824` (`feat/n7-ota-receiver`, flag-OFF receiver).
- **Worktree:** recreate with `git worktree add /private/tmp/k1_ota_sign feat/n7-ota-signing` (the prior worktree was pruned; the branch is safe in the fork's git db).
- **Envs:** `k1_ota_probe` (= `k1_hardware` + `-DSB_ENABLE_OTA=1`, main pin-map, build/link proof) and `k1_bench_ota_probe` (= `k1_bench_reference` + flag, bench `B489A500` pin-map — the brick-risk rollback env). Both **NON-SHIPPABLE**; registered in `k1_upload_guard.py`. Partition table `default_16MB.csv` (A/B OTA slots present).
- **Product line** `lane/remoted-ble-midi-phase-f` (N2b shipped ON) is unaffected — OTA is NOT on it. **NB:** the fork's *main* checkout `/Users/spectrasynq/SpectraSynq_K1_Firmware` is currently on `lane/im73d-pdm-eval` (another agent) — stay out of it; do OTA work in the worktree.

## 3. Serial/OTA API + transport surface (`system/k1_ota.{cpp,h}`)
Crypto/session API: `k1_ota_begin(size) → k1_ota_write(bytes)[folds SHA-256] → k1_ota_set_signature()/k1_ota_append_signature()[384-byte RSA-3072 sig] → k1_ota_end()[SECURITY BOUNDARY: verify-or-reject]`.
`serial_cmd_dispatch_ota()` verbs (all flag-gated), routed generically from `serial_menu.h:2662`:
- `ota_begin` / `ota_status` / `ota_abort` / `ota_end`
- **`ota_datab64`** — one base64 line → decoded image bytes into `k1_ota_write` (**serial image transport — this already exists**).
- **`ota_sigb64`** — base64 signature fragment appended via `k1_ota_append_signature` (the 384-byte sig is streamed across several ≤94-byte frames and concatenated).
- **`ota_selftest`** (NEW, residual #1) — runs the production verify over a compiled-in operator-signed vector; prints `OTA_SELFTEST: good=PASS tamper=REJECT verify=PASS`. Brick-safe (no image write, no boot-slot change).

## 4. RESIDUAL #1 — on-silicon verify proof: CODE DONE, device capture pending
**Status:** the `:ota_selftest` verb is implemented, build-proven (`pio run -e k1_ota_probe` exit 0), suite-green, and committed at **`c34a0e9`**. Vector = the re-proven Captain-signed pair, embedded in `system/k1_ota_selftest_vector.h`; it reuses the EXACT production `k1_ota_verify_signature()` path (not a copy).
**What remains (needs a device — brick-safe, may run on main `F887A500` or bench):**
1. `pio run -e k1_ota_probe -t upload --upload-port <port>` (guard confirms chip-ID).
2. Serial: `ota_selftest` → expect `OTA_SELFTEST: good=PASS tamper=REJECT verify=PASS`.
3. Restore the production build; **log the line in `docs/hardware/device-build-registry.md`** (UPDATE ON EVERY FLASH).
**DoD:** on-silicon `good=PASS tamper=REJECT` captured + logged.

## 5. RESIDUAL #2 — full device-proof matrix (REFRAMED — no transport build needed)
**Correction to rev 1:** rev 1 claimed "there is NO practical way to get an image into the device." That is **stale** — `cf406d6` added a working serial base64 transport (`ota_datab64` + `ota_sigb64`). The security accept/reject/rollback proof runs over that transport **now**; no HTTP build is a prerequisite.
- **HTTP-over-AP** is a *field-OTA nicety*, not a proof prerequisite. The shipping product has **no AP webserver** — `network/sb_*.cpp` is held out of `k1_hardware` pending the wireless A/B (`k1_ota.h:19-22`). Adding HTTP ingress means re-admitting that whole stack — a **D3 / wireless-A/B architectural decision**, out of scope for the device-proof. Do **not** build it on spec.
**Device-proof matrix (procedure in `docs/architecture/n7-ota-bench-proof-runbook.md`, Signature dimension):**
1. **Stage 0 — `:ota_selftest`** (residual #1 device step; brick-safe; any unit).
2. **GOOD signed image** → `ota_begin`→`ota_datab64`×N→`ota_sigb64`×N→`ota_end` → verifies → reboot → boots new slot + self-validates. (Sign: Captain runs `openssl dgst -sha256 -sign ~/.k1_secrets/k1_ota_signing_PRIVATE.pem -out image.sig <firmware.bin>`.)
3. **UNSIGNED / TAMPERED image** → `ota_end` **REJECTs**; running image untouched (**brick-safe, any unit**).
4. **SIGNED-but-BROKEN image** → boots → fails self-validation → **bootloader ROLLS BACK** to last-good slot. Load-bearing anti-brick proof; `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y` is framework-provided (verified in the runbook). **BENCH `B489A500` ONLY.**
**DoD:** all legs captured; registry updated; then D3 (ship) returns to Captain.

## 6. Operating doctrine — carry forward (NON-NEGOTIABLE)
1. **Rollback / signed-but-broken / any brick-risk test → BENCH `B489A500` ONLY, never the main K1 `F887A500`.** The self-test (Stage 0) and the unsigned/tampered REJECT leg are brick-safe and may run on any unit; the rollback leg is the brick-risk one. (The main's native-USB CDC also wedged twice this program under stress — fault/brick injection belongs on the bench.)
2. **Bench is currently hardware-modified + occupied:** IM73D122 PDM mic, SPH0645 removed, NVS cal wiped, active `lane/im73d-pdm-eval`. Coordinate before claiming it; its CP2102 ROM-downloads on scripted pyserial (use interactive `pio device monitor`). The rollback proof needs a **clean, known-good** bench slot.
3. **Identity by chip-ID, never port** — flash only via `pio run -e <env> -t upload --upload-port <port>`; the guard verifies MAC (`F887A500` main / `B489A500` bench) and aborts on mismatch. Ports drift (`1101`/`2101`/`12201`/`12401`).
4. **Never generate or commit a signing key.** Captain custodies the private key; agents verify with the public key only. To sign a test image, hand Captain the exact `openssl … -sign` command and receive back the `.sig`.
5. **`SB_ENABLE_OTA` stays default-0 until D3.** Shipping OTA (flag-ON in `k1_hardware` + merge) is a Captain decision.
6. **Verify claims first-hand** — this handover's rev-2 corrections came from reading the code at `c34a0e9`, not trusting rev 1's prose. Do the same for silicon + the proof matrix.

## 7. Evidence
- Host real-key proof (2026-07-07, re-run): `openssl dgst -sha256 -verify certs/k1_ota_signing_PUBLIC.pem -signature ota_test.sig ota_test.bin` → `Verified OK`; 1-byte tamper → `bad signature`.
- Residual #1: commit `c34a0e9`; `system/k1_ota.cpp` (`ota_selftest` + `k1_ota_run_selftest`), `system/k1_ota_selftest_vector.h`. Build-proof `k1_ota_probe` exit 0 (`firmware.bin` 701,392 B); commit-gate: 594 host tests passed + `k1_hardware` flag-OFF rebuild SUCCESS.
- Runbook (signature dimension added 2026-07-07): `docs/architecture/n7-ota-bench-proof-runbook.md`.
- Gitignore for keys: commit `dd83303`.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-07 | agent:claude-opus-4-8 (CTO) | Created (rev 1). OTA signing device-proof handover: signature security PROVEN on host with Captain's real key; folded in the two residuals. |
| 2026-07-07 | agent:claude-opus-4-8 (CTO) | Rev 2. Corrected residual #2's stale "no transport exists" premise — serial base64 transport (ota_datab64/ota_sigb64) shipped in cf406d6; HTTP-over-AP reframed as enablement-only, not a proof prerequisite. Residual #1 updated to CODE-COMPLETE + build-proven + committed (c34a0e9, :ota_selftest); only device capture pending. Branch tip cf406d6→c34a0e9. Moved the doc onto the OTA branch (was an untracked orphan in the im73d checkout). |
