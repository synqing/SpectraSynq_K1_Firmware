---
abstract: "N7 OTA receiver — Captain-decision memo (D3) + device-proof plan. A flag-OFF (SB_ENABLE_OTA=0) on-device OTA receiver + anti-brick rollback is built and host-gated on DRAFT branch feat/n7-ota-receiver (flag-OFF build is BYTE-IDENTICAL to the shipped product line; flag-ON adds 1,872 B). NOT enabled, NO keys committed. D3 gates enablement: (a) enable in v1? (b) image-signing key custody, (c) distribution server. Read before enabling OTA — a bad OTA path bricks fleets (highest blast radius in the repo)."
---

# N7 — OTA receiver: D3 decision memo + device-proof plan

**Class C/B · P0-operational · Decision: D3 (Captain-only — irreversible blast radius + secret custody).**
**DRAFT:** branch `feat/n7-ota-receiver` @ `d4a7824` (pushed, NOT merged to product).

## What is built (autonomous DoD met)
- New TU `system/k1_ota.{cpp,h}`: on-device OTA receiver (`esp_ota_begin/write/end/set_boot_partition`) + anti-brick rollback (`esp_ota_mark_app_valid_cancel_rollback` from the boot-health path), **all behind `#if SB_ENABLE_OTA` (default 0)**.
- Flag `SB_ENABLE_OTA` in `system/constants.h` (mirrors `SB_ENABLE_USB_MSC_UPDATE`), flag-gated serial ingress, `k1_ota_probe` env (flag-ON), upload-guard registration, `tests/test_ota_receiver_static.py`.
- **Gate (all green):** flag-OFF `k1_hardware` build is **byte-identical to the shipped product line (649,280 B) → zero regression**; flag-ON `k1_ota_probe` builds + links esp_ota (+1,872 B); golden master + Gate-0 + static + guard = **19 passed**.
- **NOT done (by design — D3):** OTA is not enabled, no signing key exists/committed, no distribution server, no device-proof run yet (needs the plan below).

## Device-proof plan (the B-class gate before any enablement — run on the BENCH unit `B489A500`, not the only main K1)
1. Flash `k1_ota_probe` (flag-ON) to the bench K1; confirm normal boot + `esp_ota_mark_app_valid_cancel_rollback` marks the running slot valid.
2. Push a **known-good** image to the inactive slot via the receiver → `esp_ota_set_boot_partition` → reboot → confirm it boots the new slot and self-validates.
3. Push a **deliberately-bad** image (e.g. truncated) → reboot → confirm the bootloader **rolls back** to the last-good slot (anti-brick). This is the load-bearing test — it proves a bad OTA cannot brick a unit.
4. Requires `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y` pinned in an `sdkconfig.defaults` (an N7-enable prerequisite — note it; the repo currently has no sdkconfig.defaults — pairs with N2b).

## D3 — the three enablement STOPs (accept/reject)
- **(a) Enable OTA in v1?** *Recommended: YES* — it is the single biggest field-operability gap; without it the first post-ship bug is an RMA per unit. But enabling REQUIRES (b) + (c). **Default if no override:** receiver stays flag-OFF; v1 ships without field update (documented limitation).
- **(b) Image-signing key custody.** Unsigned OTA is **unsafe** — anyone on the K1 AP could push arbitrary firmware. Enabling MUST pair with signed images + secure-boot/signature verification. The signing **private key is a secret (Class D)** — Captain decides custody (HSM / secrets manager / offline). **The agent will never generate or commit a key.** **Default:** no enablement without a key-custody decision.
- **(c) Distribution / update server.** Where images come from. **Default:** AP-local manual upload for the first cut (no hosted server); a hosted update server is Kickstarter-fulfilment infra and can follow.

**Blast radius:** a bad OTA path bricks fleets — the highest in the repo. That is why enablement is yours alone; the build is done so the decision is unblocked, not the risk.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:claude-opus-4-8 (CTO) | Created. N7 OTA flag-OFF DRAFT built + host-gated (byte-identical flag-OFF, 19 tests pass) on feat/n7-ota-receiver; D3 memo (enable/keys/server) + bench device-proof plan (incl. deliberately-bad-image rollback test). Built by an SSA that died on an API error at the gate step; orchestrator preserved, gated, and pushed the work. |
