---
abstract: "Lane handover for N2b boot-loop guard (production-readiness Wave 2). Wave 1 (N1 config-integrity #13, N2 I2S+watchdog #14, N3 token-scrub #15) is MERGED to main (c9bcdc8). The boot-loop decision core is host-PROVEN (7/7, clang -Wall -Wextra); the ESP/RTC shell integration + on-device crash fault-injection remain. Carries the CTO mandate (merge #15 → fresh N2b lane → device-proof → DRAFT PR), the required guards, the 12-step device-proof acceptance, the stop-conditions, the proven decision-core source, the exact integration anchors, item-2's UNPROVEN-defect deferral, and D4 (decided, for N4). Read before any N2b firmware/boot-path work."
---

# N2b Boot-Loop Guard — Lane Handover

> **One line:** the decision core is proven off-device; what remains is **boot-path RTC surgery + on-device crash fault-injection** — done wrong it turns a recovery feature into a boot brick. Go slow, prove on silicon, DRAFT-PR only.

## 0. Repo / environment (verify live before acting — SSA)

- **FORK (all work):** `/Users/spectrasynq/SpectraSynq_K1_Firmware`. **`main = c9bcdc8`** (PR #15 merge; N1+N2+N3 in).
- **DECOY — NEVER touch/read/build:** `/Users/spectrasynq/SensoryBridge-main 9`. cwd-guard every action (`git -C <fork> rev-parse --show-toplevel`).
- **Concurrent lane hazard:** `lane/remoted-ble-midi-phase-f` (a BLE-MIDI lane) is **active in the MAIN checkout** and switches its branch. It **has N1, lacks N2** (forked at the N2 LOCK) → it must rebase onto N2+N2b later. **Work N2b in a dedicated git worktree** (this lane is in `/Users/spectrasynq/SpectraSynq_K1_Firmware-n2b`, branch `feat/n2b-bootloop-guard`, already reset onto fresh `main`). Never fight the main checkout for a branch.
- **GitHub:** `synqing/SpectraSynq_K1_Firmware`. `gh` resolves repo from cwd → pass `-R synqing/SpectraSynq_K1_Firmware` when cwd is the decoy. Agent opens **DRAFT** PRs only; Captain merges.

## 1. Program state

| Lane | Status |
|---|---|
| **N1** config-integrity + anti-brick (CRC header, MIGRATE, defaults-fallback) | ✅ merged **#13**, host + device proven |
| **N2** I2S bounded read + task watchdog (freeze-fix) | ✅ merged **#14**, host + device proven (TWDT catches hung loopTask) |
| **N3** wireless-token scrub + Finding-B precondition gate | ✅ merged **#15** |
| **N2b** boot-loop guard | ⏳ **THIS LANE** — decision core proven; integration + device-proof remain |
| **N4** manufacturing/provisioning | next; **D4 DECIDED** (see §9) |
| item-2 `led_thread_halt` freeze | ⛔ **UNPROVEN production defect — deferred, no code** (§8) |

## 2. The CTO mandate (authoritative — Captain-issued)

Sequence: **merge #15 (done) → refresh N2b on clean main (done) → ESP/RTC wiring as a focused LOCK→FIX lane → device fault-injection → DRAFT PR.** Keep it boring; do not let item-2 or unrelated cleanup hitchhike onto a boot-path safety feature.

**N2b scope (do ONLY this):** integrate the ESP/RTC shell around the already-host-proven decision core. **No** led_thread_halt, **no** AP/VP/render/effect changes, **no** config migration, **no** destructive safe-mode writes, **no** unrelated file touched.

## 3. The decision core — HOST-PROVEN (drop in verbatim during the FIX)

`SPECTRASYNQ_K1_FIRMWARE/system/k1_bootloop_guard.h` (already on disk in the `-n2b` worktree, untracked — it belongs in the **FIX** commit, not the LOCK). The pure core compiled clean under `clang -Wall -Wextra` and passed **7/7**:

```
S1 garbage-magic seeds to 0 (RTC garbage can't trip safe mode)
S2 clean power-on clears the streak
S3 crash1→1 / crash2→2 / crash3→3 NORMAL ; crash4→4 SAFE_MODE (trips exactly at threshold) ; crash5→stays SAFE_MODE
S4 mark_stable clears the streak ; post-stable crash restarts from 1
S5 non-crash reset (intentional reboot) leaves count unchanged
S6 at-threshold + benign reset stays SAFE_MODE
S7 power-on overrides a crash flag → seed 0
```

Core shape (`k1_bootloop_eval(state*, is_poweron, is_crash, threshold) -> {NORMAL|SAFE_MODE}` + `k1_bootloop_mark_stable`). **DESIGN DELTA the CTO requires:** the RTC record currently has `magic` only — **add a `version` field** (magic+version validity guard; a CRC is optional for a 2-field struct). The ESP shell (`#if defined(ESP_PLATFORM)`): `RTC_NOINIT_ATTR K1BootloopState` (declare/define the actual var **in the .ino**, not the header — header-defined globals multiply across TUs), `esp_reset_reason()`, and `k1_bootloop_reason_is_crash()` (PANIC | TASK_WDT | INT_WDT | WDT | BROWNOUT = crash; **ESP_RST_SW / POWERON / DEEPSLEEP / USB / JTAG = benign**). The pure scenarios above become the host-compile oracle's golden.

## 4. Exact integration anchors (ground-truthed; re-verify line numbers — files churn)

- **Boot-count increment:** very top of `setup()` — `SPECTRASYNQ_K1_FIRMWARE.ino:601` (right after `void setup() {`, **before** the line-602 `heap_caps_malloc`, which can crash). Cache `esp_reset_reason()` once. Set a regular global `bool k1_boot_safe_mode` (declare in `globals.h`, define in `globals_config.cpp`).
- **Safe-mode entry (NON-DESTRUCTIVE):** `persistence/bridge_fs.h` `load_config()` **definition at :128**. Add, under the flag, at the top: `if (k1_boot_safe_mode) { memcpy(&CONFIG,&CONFIG_DEFAULTS,sizeof(CONFIG)); <serial log>; unlock_leds(); return; }`. This skips the persisted blob and boots compiled defaults **in RAM only**. **The file is NEVER deleted and defaults are NEVER written back to flash** (CTO stop-condition). Reuses N1's `CONFIG_DEFAULTS`. (Boot chain: `setup()` → `init_system()` `.ino:611` → `init_fs()` `system.h:419` → `load_config()` `bridge_fs.h:128`.)
- **Stable-clear:** `loop()` opens `.ino:730`; `uint32_t t_now` (ms-since-boot) is computed at `.ino:735` (just after N2's `feedLoopWDT()`). After it: `static bool marked; if(!marked && t_now > K1_BOOTLOOP_STABLE_MS){ k1_bootloop_mark_stable(&rtc); marked=true; }`. **Clear only after meaningful uptime (≥10 s), never on the first tick** (CTO).
- **Visible boot log:** house style is `USBSerial.println("TOKEN: key=val ...")` (e.g. `RUNTIME_TIMING_GUARD` at `.ino:667-690`). Emit `BOOT_LOOP_GUARD: reset_reason=<...> fail_count=<n> safe_mode=<0|1>` after the guard runs in setup, and a `stable_clear` line when the streak clears.
- **Flag:** `-DK1_BOOTLOOP_GUARD_V1` in `[env:k1_hardware]` build_flags (with the `SB_*_V2` group ~:88-102) **and** `[env:k1_bench_reference]` (bench inherits via `extends`; N2's flag did — confirm via `compile_commands`/strings, not on paper). **Single-symbol revert.** **OFF ⇒ byte-identical to pre-N2b** (CTO stop-condition).
- Reset-reason decode already exists at `serial/serial_menu.h:2107` (`cmd_reset_reason`, command only — not read at boot). No `RTC_NOINIT_ATTR` exists anywhere yet (this is the first).

## 5. Required implementation guards (CTO — all mandatory)

```
K1_BOOTLOOP_GUARD_V1 gated; default production behaviour unchanged until promoted
RTC record validity guard: magic + version (or CRC) — garbage RTC CANNOT trip safe mode
clean power-on / brownout / cold boot clears the streak
intentional reboot (ESP_RST_SW) does NOT count as a crash
crash reset (PANIC/TASK_WDT/INT_WDT/BROWNOUT) increments the streak
safe mode trips EXACTLY at threshold (4)
safe mode = CONFIG_DEFAULTS as a NON-PERSISTENT runtime fallback ONLY (never written to flash)
mark_stable clears ONLY after meaningful uptime (≥10 s), not the first loop tick
visible boot log: reset_reason, streak, safe_mode, stable_clear
manual recovery path exists if the guard misbehaves (the OFF flag + serial reset_reason)
```
**The single most important one:** *CONFIG_DEFAULTS is a runtime fallback, never persisted.* Safe mode protects the device; it must not erase user config.

## 6. Gates (host + the two-commit shape)

- **Two-commit LOCK→FIX** (anti-gaming, as N1/N2): **LOCK** = a characterization test (zero firmware source) asserting the pre-N2b reality (setup has no RTC boot-counter; no `K1_BOOTLOOP_GUARD_V1`; no `RTC_NOINIT_ATTR`) — GREEN now. **FIX** = the header + integration + the host-compile oracle + flip the characterization to the fixed-state invariants.
- **Host-compile oracle** (pattern: `scripts/regression-harness/golden/oracle_bridge_fs_codec.py` — N1's): compile `k1_bootloop_guard.h`'s pure core + a driver feeding the **7 scenarios** → golden in `tests/golden/`, registered in `harness_selftest.ORACLE_MODULES`, MANIFEST line appended, Gate-Fα teeth (flip the threshold compare / the magic check / the is_crash gate). This is the host gate that pins the decision logic.
- `pio run -e k1_hardware` **and** `-e k1_bench_reference` must build. **`pio` building is NOT proof** (CTO) — device fault-injection is.
- Full `pytest tests/` green (≈577+ on this base). Commit via `git commit -F -` (zsh backtick gotcha).

## 7. DEVICE-PROOF acceptance — REQUIRED (CTO 12-step; no "seems stable")

```
1.  Flash guarded build (main K1, chip F887A500; identity-verify first).
2.  Normal boot does NOT enter safe mode.
3.  Force crash #1 → no safe mode.
4.  Force crash #2 → no safe mode.
5.  Force crash #3 → no safe mode.
6.  Force crash #4 → safe mode enters EXACTLY at threshold.
7.  Confirm safe-mode config path is non-destructive (config file intact; defaults in RAM only).
8.  Let stable uptime pass → mark_stable clears the streak.
9.  Reboot again → normal mode restored.
10. Intentional reboot does NOT increment the crash streak.
11. Power-cycle clears/overrides the crash streak.
12. Registry row updated (docs/hardware/device-build-registry.md, deployed-state table).
```
**Fault-injection design (throwaway, reverted after — like N2's):** trigger the crash via a temp flag, ideally **tied to the persisted-config path** so safe-mode (which skips it) demonstrably **breaks the loop** at the threshold (proves recovery end-to-end), or a controlled `if (fail_count < N) abort();` placed AFTER the guard increment. Capture serial transcripts for the threshold, stable-clear, intentional-reboot, and power-cycle legs. Confirm the config file is intact afterward (non-destructive).

## 8. Item-2 `led_thread_halt` — UNPROVEN production defect (DEFERRED, no code)

The Cowork session proposed a "one-line WDT-feed move." **Ground-truth correction:** the park barrier that could freeze (`led_thread.while(true)` ~`.ino:1037-1049`) is under `#ifdef K1_EFFECT_FRAMEWORK_V1` — **compiled OUT of production `k1_hardware`.** So the "stuck halt freezes prod" premise is unverified. **Minimum proof before any code:**
```
production build has led_thread_halt compiled in AND something in prod can SET it
the freeze path is reachable WITHOUT K1_EFFECT_FRAMEWORK_V1
the proposed feed-move changes a REAL shipping failure mode
```
Until all hold: classify **UNPROVEN production defect — no code change.** Do not let it ride N2b.

## 9. N4 (next lane) — D4 DECIDED (reversible defaults)

Per-unit manufacturing/provisioning. **D4 = Scheme B:** serial `K1-<SKU>-<YYWW>-<NNNN>`, single SKU code `K1` until a 2nd product exists, **random per-unit control token**, schema-versioned identity record — all **reversible defaults** (free to change until the first unit is provisioned). **D1 folds into N4:** the per-unit token kills the static `"k1-tab5"` (still hardcoded twice — `platformio.ini` wireless env after N3, and the `#ifndef` fallback `sb_k1_wireless.cpp:37`). N4 is NOT meeting-blocked. Q1-Q5 (SKU breadth, sequential-vs-random, allocator owner, physical marking, regulatory IDs) only refine the SKU string before first production.

## 10. Inherited discipline (binding)

- **Device:** identity by **chip-ID before every write** — main K1 `F887A500` = `k1_hardware` ONLY (currently on `/dev/tty.usbmodem1101`, MAC `b4:3a:45:a5:87:f8`; ports scramble — verify, don't trust port names); bench `B489A500` = `k1_bench_reference` ONLY, **never cross-flash** (different GPIO). Standing Captain flash auth for the main K1 (2026-06-19 + 2026-06-26 unrestricted). `k1_upload_guard.py` is the MAC backstop, not the first check. Update the device-build-registry deployed-state row after every flash. Never auto-fire `noise_cal`.
- **Flash gotchas:** piped/redirected `pio … -t upload` silently no-ops (needs a pty). `script -q` flaked once here (`tcgetattr/ioctl on socket`) → **use a `python pty.spawn(["pio","run","-e","k1_hardware","-t","upload","--upload-port","/dev/tty.usbmodem1101"])` wrapper** (proven this session). Build (no pty) and upload (pty) separately. Device I/O via Bash needs `dangerouslyDisableSandbox:true`. 75 s soak + crash-marker scan after every flash.
- **Agent never:** force-pushes main, marks-ready/merges PRs, pushes tags, flashes without per-session auth + chip-ID guard, bundles two flags/lanes per PR, or lets the serial-decomposition program become the headline.
- **Founder boundary:** execute autonomously; escalate only material strategic / irreversible / Captain-decision items. Decision-grade reporting (no log dumps).

## 11. Stop conditions (CTO — any one halts N2b)

```
safe mode writes defaults to flash | reset reasons ambiguous | RTC validity cannot be proven
device stuck entering safe mode | mark_stable can clear too early | production behaviour changes while flag OFF
any unrelated file touched
```

## 12. Recommended first actions

1. cwd-guard the `-n2b` worktree; `git -C … rev-parse --abbrev-ref HEAD` == `feat/n2b-bootloop-guard`, base == `c9bcdc8`.
2. Re-verify §4 anchors live (line numbers drift). Confirm `RTC_NOINIT_ATTR` still absent; confirm the load_config def line.
3. Write the **LOCK** (characterization test, zero source) → commit.
4. Add the version field to the core; write the **FIX** (header + 4 integration points + flag + host-compile oracle pinning the 7 scenarios) → host gates green (`pytest`, both `pio` envs) → commit.
5. Device fault-injection (the 12-step) on the main K1 → transcripts → registry row.
6. DRAFT PR (`-R synqing/SpectraSynq_K1_Firmware`), no merge.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-27 | agent:claude-opus | Created at lane handoff: N2b boot-loop guard — decision core host-proven, integration + device-proof remaining; folds the CTO mandate, guards, 12-step device-proof, stop-conditions, proven core, integration anchors, item-2 deferral, D4. Base refreshed onto post-#15 main (c9bcdc8). |
