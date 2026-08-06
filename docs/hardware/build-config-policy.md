---
abstract: "Build-config policy DRIFT-GATE for k1_hardware (Lane B, narrowed). Documents the resolved brownout/coredump/WDT IDF policy and explains why it is a drift-detector, not 'sdkconfig pinning': framework=arduino on pioarduino bakes the IDF sdkconfig into the precompiled libs, so a project sdkconfig.defaults is INERT (only the custom_sdkconfig option is honoured, and it forces a from-source rebuild). Records the corrected reality — coredump-to-flash is ALREADY enabled and the default_16MB.csv already has a coredump partition — and the host gate that locks these against silent platform-version drift. Read before touching build config, brownout, coredump, or watchdog settings."
---

# Build-config policy (k1_hardware) — resolved values + drift-gate

> **This documents and *detects drift in* the build's resolved IDF config. It
> does not change the binary.** The lane that produced it (Lane B, narrowed)
> made zero firmware and zero binary changes — it is a characterization +
> drift-detection gate, not config tuning.

## 1. Why this is a drift-gate, not "sdkconfig pinning"

`k1_hardware` builds with `framework = arduino` on the pioarduino platform
(`platform-espressif32` 54.03.x). In that mode the ESP-IDF `sdkconfig` is
**baked into the precompiled** `framework-arduinoespressif32-libs/<chip>/sdkconfig`
that the app links against. Consequences, verified first-hand in the platform's
`builder/frameworks/arduino.py`:

- A bare project-root **`sdkconfig.defaults` is never read** under
  `framework = arduino` (the `sdkconfig.defaults` reader lives only in the
  `framework = espidf` path). Adding one would be **inert theatre** — a file
  that looks like it pins config but changes nothing.
- The **only** override vehicle is pioarduino's `custom_sdkconfig` option
  (platformio.ini env option or `board.espidf.custom_sdkconfig`). Setting it
  triggers a **from-source rebuild** of the Arduino IDF libs — a binary-changing
  operation that would require its own device-proof. It is **out of scope** for
  a behaviour-neutral lane.

So the achievable, honest win is to **pin the current resolved values as a
golden and fail a host test when they drift** (e.g. a platform/package bump
silently changes them). It enforces nothing into the binary; it *notices* when
the binary's config moves under us.

Concrete drift evidence already present: `platformio.ini` pins the
`.../54.03.20/platform-espressif32.zip` release, but the installed platform
self-reports version **54.03.21**. The resolved config can move without the
pin changing — which is exactly what this gate watches.

## 2. The pinned policy (resolved 2026-06-27, esp32s3 prebuilt libs)

| Domain | Key | Value | Intent |
|---|---|---|---|
| Brownout | `CONFIG_ESP_BROWNOUT_DET` / `_LVL` | `y` / `7` | Undervoltage reset protection at the highest trip level. |
| **Coredump** | `CONFIG_ESP_COREDUMP_ENABLE_TO_FLASH` | `y` | **Already on** — post-mortem written to flash on a field crash. |
| Coredump | `CONFIG_ESP_COREDUMP_DATA_FORMAT_ELF` / `_CHECK_BOOT` | `y` / `y` | ELF payload, boot-time integrity check. |
| Task WDT | `CONFIG_ESP_TASK_WDT_EN` / `_INIT` / `_PANIC` / `_TIMEOUT_S` | `y` / `y` / `y` / `5` | Catches a starved/hung task (pairs with N2's `esp_task_wdt` subscription); panic-reset at 5 s. |
| Int WDT | `CONFIG_ESP_INT_WDT` / `_TIMEOUT_MS` | `y` / `300` | Catches an ISR/critical section blocking too long. |
| Bootloader WDT | `CONFIG_BOOTLOADER_WDT_ENABLE` / `_TIME_MS` | `y` / `9000` | Covers the pre-app boot window. |

**Partition:** the active `default_16MB.csv` already contains a `coredump`
partition (`data, coredump, 0xFF0000, 0x10000` = 64 KB) — verified present in
every installed framework-arduinoespressif32 version. Flash coredump therefore
already has somewhere to write; **no partition change is needed or made.**

> **Correction to the prior lane premise.** The N2b-bundle note assumed coredump
> was "disabled at framework default" and would need enabling (+ a partition).
> That was wrong: coredump-to-flash is **already enabled** and the partition
> **already exists**. The gate's job is therefore to **lock that they stay on**,
> not to turn them on. No enablement, no partition/layout decision.

## 3. The gate (host-only, no device)

`tests/test_build_config_policy_static.py` + `scripts/regression-harness/golden/oracle_build_config_policy.py`:

- **Authoritative source, in priority order:** `.pio/build/k1_hardware/sdkconfig`
  (the real app build output) → else
  `$PLATFORMIO_CORE_DIR/packages/framework-arduinoespressif32-libs/esp32s3/sdkconfig`
  (the prebuilt-libs source governing the app). If **neither** is locatable the
  test **SKIPS LOUD** — it never treats an absent source as "no drift".
- **`test_resolved_policy_matches_golden`** — live resolved values must equal the
  golden; any mismatch fails with a per-key drift report.
- **`test_coredump_partition_present`** — the active partition table must carry a
  `coredump` partition.
- **`test_drift_gate_bites` (Gate-Fα)** — the anti-theatre proof: the comparison
  provably FAILS on a mutated golden (disabled coredump, off-by-one brownout
  level, absent key). A perpetually-green gate cannot masquerade as "no drift".
- **`test_no_inert_sdkconfig_defaults_vehicle`** — fails if a future change adds a
  root `sdkconfig.defaults` (inert here) — keeps the theatre out by construction.

This lane uses **no LOCK→FIX firmware split** because it changes no firmware and
no binary — there is no behaviour delta to game. The anti-gaming guarantee is the
Gate-Fα drift proof above.

## 4. How to change a value deliberately (future)

1. **Document the intent** here (which key, old→new, why).
2. **Update `GOLDEN_POLICY`** in the oracle so the gate tracks the new intent.
3. If the change must be **enforced into the binary** (not just tracked), it
   requires pioarduino `custom_sdkconfig` → a **from-source rebuild** → treat as
   a **behaviour-changing lane** with a device-proof gate (NOT behaviour-neutral).
   Brownout-threshold / WDT-timeout changes are **not** to be made "by vibes".

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-27 | agent:claude-opus | Created (Lane B, narrowed). Documents the resolved brownout/coredump/WDT policy, the framework=arduino "sdkconfig.defaults is inert" mechanism (verified in arduino.py), the coredump-already-on + partition-already-present correction, and the host drift-gate (skip-loud + Gate-Fα). Zero firmware/binary change. |
