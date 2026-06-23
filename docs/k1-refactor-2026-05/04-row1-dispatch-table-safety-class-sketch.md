---
abstract: "Phase-0 SKETCH for Row 1 (serial_menu.h, 186-arm strcmp dispatch). Defines the 4-class safety taxonomy (SAFE / ARM-REQUIRED / FORBIDDEN-FROM-SINGLE-BYTE / TYPED-ONLY), the proposed dispatch-table row schema (name → handler → safety_class → flags), a grounded classification of the destructive command set + the single-byte hotkey set, and a CANDIDATE behaviour-delta list of the points where current behaviour must change to be safe. Source-verified against serial_menu.h @ 00a0fcb. This is a Phase-0 sketch per Captain ratification (02-SPLIT-JUSTIFICATION-MATRIX Row 1): taxonomy + candidate delta list now; the exact full 186-row classification + signed delta list happen at the Row 1 gate. NO Row 1 execution — no serial_menu.h edits in this artefact."
---

# Row 1 — Dispatch-Table Safety-Class Sketch (Phase 0)

| Field | Value |
|---|---|
| Date | 2026-05-25 |
| Status | **SKETCH — Phase 0 deliverable; D5 + D6 RULED by Captain 2026-05-25.** Taxonomy + delta list. Full 186-row classification + signed delta list remain the Row 1-gate deliverable. |
| Scope | `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h` (2823 LOC, 187 strcmp/strncmp arms) |
| Authority | `02-SPLIT-JUSTIFICATION-MATRIX.md` Row 1 (RATIFIED 2026-05-25): "safety-class taxonomy + candidate behaviour delta list **sketched in Phase 0** (before Row 1 execution); final exact delta list signed off at Row 1 gate." |
| Source anchor | serial_menu.h @ `00a0fcb` |
| Precedent | N/Y arm/confirm gate (commit `9423ea0`); the `N`-as-single-keystroke `start_noise_cal` blocker (`docs/forensics/2026-05-24-hotkeys-prefreeze-review.md`) |
| Non-goal | This artefact changes **no code**. Row 1 execution (build the table, classify all 186, replace the strcmp loop, differential gate) is a later, separately-gated step. |

> **Why Row 1 exists (02-MATRIX C1).** The 186-strcmp chain in `serial_menu.h` is the surface where *every* dangerous-action command is wired, and it carries **no safety-class metadata**. An agent or human adding a command has no structural way to know whether it needs an arm/confirm gate. The N/Y precedent codified the *pattern* for one command; the dispatch surface does not *enforce* it. Row 1 = targeted extraction of the strcmp chain into a static dispatch table — one row per command, `name → handler → safety_class` — so the safety contract is structural, not tribal.

---

## 1. Safety-class taxonomy (4 classes)

Each command row is assigned exactly one class. The class fixes **which input surfaces may reach the handler** and **what gate must pass first**.

| Class | Definition | Allowed input surface | Gate required | Examples (candidate) |
|---|---|---|---|---|
| **SAFE** | Read-only, or a trivially reversible in-RAM/config toggle/adjust. No destructive or precondition-dependent side effect. | Single-byte hotkey **and** typed | None — fires immediately | `;` status, `h` help, `chip_id`, `get_num_modes`, mode/brightness/colour toggles (`1`–`6`, `[` `]`, `i/o/p/j/k/l/q/w/e/r/t`), parameter *reads* |
| **ARM-REQUIRED** | Correct only under an **external precondition the firmware cannot verify itself** (e.g. acoustic silence). Must be explicitly armed, then confirmed inside a short window. | Single-byte confirm allowed **only as the confirm half** of an arm pair; arm step is its own command | **Timed arm/confirm window:** `arm` → `confirm` within `SERIAL_NOISE_CAL_ARM_WINDOW_MS` (5 s). Confirm fails closed if not armed. **This window is reserved for silence-dependent cal only.** | the `N`(arm)→`Y`(confirm) cal pair — **sole calibration trigger** (typed `start_noise_cal` dropped, Captain D5) |
| **FORBIDDEN-FROM-SINGLE-BYTE** | Destructive or irreversible: deletes persisted state, or cannot be undone from the same session. | **Typed only** — must NEVER be reachable from a single keystroke. | **Typed confirmation token:** the command is inert unless its argument is exactly `CONFIRM` (e.g. `factory_reset CONFIRM`). **Not** a timed arm window (Captain D6: tokens are more auditable and not tripped by stray serial input). Never bound to any `serial_hotkey_is_immediate` key. | `factory_reset`, `restore_defaults`, `clear_noise_cal` |
| **TYPED-ONLY** | Not destructive, but must not be a one-keystroke action: parameterised setters, disruptive-but-recoverable actions, or anything that persists config. | Typed only (carries an argument or is intentionally non-hotkey) | None beyond being typed; `persists` rows write config | parameterised `set …`/`get …` arms, `reset`/`reboot` (disruptive, recoverable), `identify` |

**Class ordering of strictness:** SAFE < TYPED-ONLY < ARM-REQUIRED < FORBIDDEN-FROM-SINGLE-BYTE. When uncertain, classify **stricter** (fail-safe), mirroring the VP-semantics classifier's "when in doubt, more gating" rule in `03-hardware-gate-package.md §1.5`.

---

## 2. Proposed dispatch-table row schema

Replace the `else if (strcmp(command_buf, "x") == 0)` chain with a static, `const`/`PROGMEM` table of rows:

```c
typedef enum { SC_SAFE, SC_TYPED_ONLY, SC_ARM_REQUIRED, SC_FORBIDDEN_SINGLE_BYTE } safety_class_t;

typedef struct {
  const char*    name;          // command token (typed form)
  char           hotkey;        // single-byte form, or 0 if none
  void         (*handler)(const char* args);
  safety_class_t safety_class;
  uint8_t        flags;         // bitfield, see below
} serial_cmd_row_t;

// flags
#define CMD_PERSISTS        (1<<0)  // writes config (save_config_delayed)
#define CMD_IRREVERSIBLE    (1<<1)  // deletes persisted state / no in-session undo
#define CMD_NEEDS_SILENCE   (1<<2)  // correctness depends on acoustic silence
#define CMD_DISRUPTIVE      (1<<3)  // reboots / interrupts the show
```

**Runtime enforcement (single chokepoint, replaces 186 hand-written arms):**
- Single-byte path (`serial_hotkey_is_immediate` / `serial_handle_hotkey`) may dispatch a row **only if** `row.hotkey != 0` **and** `row.safety_class ∈ {SAFE, ARM-REQUIRED-confirm-leg}`. A `FORBIDDEN-FROM-SINGLE-BYTE` row with a non-zero `hotkey` is a **compile-time/boot-time assertion failure** — the structural guarantee.
- `ARM-REQUIRED` rows dispatch only while `serial_*_arm_active()` (generalised from today's `serial_noise_cal_arm_*`) is true — the timed window, reserved for silence-dependent cal; else skipped with the standard `ARM first` message.
- `FORBIDDEN-FROM-SINGLE-BYTE` rows dispatch only when the parsed argument is exactly `CONFIRM` (Captain D6 — typed token, **not** the arm window); a bare command prints a usage line and does nothing. A boot/compile assertion guarantees these rows carry no `hotkey`.
- The table is the single source of truth for `serial_print_hotkey_help`, `serial_print_hotkey_status`, and the existing help dumps — they iterate the table instead of duplicating the command list.

This is the C1 resolution: adding a command = adding a row with a class. There is no path to wire a destructive command without choosing a class, and no path to bind a destructive class to a keystroke.

---

## 3. Grounded classification (source-verified subset)

Full 186-row classification is the **Row 1 gate** deliverable. Phase 0 fixes the destructive set and the single-byte set, which are the safety-load-bearing rows.

### 3a. Destructive / precondition-dependent commands (the load-bearing rows)

| Command (token) | Handler (serial_menu.h) | Current behaviour | Proposed class |
|---|---|---|---|
| `start_noise_cal` | `:1153` → `ack(); noise_transition_queued = true;` | **Typed form fires immediately, no silence gate, no arm.** | **DROP (D5)** — typed command removed; `N`→`Y` is the sole cal trigger. Retain only with a documented hard lab-automation reason, and then **ARM-REQUIRED**, never immediate. |
| `N` / `Y` (hotkey cal) | `:837 serial_arm_noise_cal()` / `:840 serial_confirm_noise_cal()` | Already gated: `N` arms, `Y` confirms within 5 s, confirm fails closed if not armed (`:546`). | `N`=arm step (SAFE); `Y`=ARM-REQUIRED confirm leg. **Already correct — becomes the reference row.** |
| `clear_noise_cal` | `:1161` → `ack(); clear_noise_cal();` | Deletes stored cal immediately on typed command. | **FORBIDDEN-FROM-SINGLE-BYTE** (+ `CMD_IRREVERSIBLE`); confirm `clear_noise_cal CONFIRM` (D6) |
| `factory_reset` | `:1119` → `ack(); factory_reset();` | Deletes ALL config incl. cal, reboots — immediately. | **FORBIDDEN-FROM-SINGLE-BYTE** (+ `CMD_IRREVERSIBLE | CMD_DISRUPTIVE`); confirm `factory_reset CONFIRM` (D6) |
| `restore_defaults` | `:1127` → `ack(); restore_defaults();` | Deletes config, reboots — immediately. | **FORBIDDEN-FROM-SINGLE-BYTE** (+ `CMD_IRREVERSIBLE | CMD_DISRUPTIVE`); confirm `restore_defaults CONFIRM` (D6) |
| `reset` | `:1111` → `ack(); reboot();` | Reboots immediately. Not data-destructive. | **TYPED-ONLY** (+ `CMD_DISRUPTIVE`) |

### 3b. Single-byte hotkey set (source-verified, `serial_hotkey_is_immediate :773`)

Immediate keys: `space h ; N Y [ ] 1 2 3 4 5 6 i I o O p P j J k K l L q Q w W e E r R t T , . / a s d f`.
- **All map to SAFE toggles/adjusts/reads** (mode cycle, colour/brightness toggles, target select, status/help) **except** `N`/`Y` (the cal arm/confirm pair).
- **Invariant to preserve:** no immediate key reaches a `CMD_IRREVERSIBLE` handler today. The table must make this a structural guarantee (§2), not a coincidence.
- Several immediate toggles call `save_config_delayed()` (`:867,909,915,921,927`) → tag `CMD_PERSISTS`, but they remain SAFE (reversible).

### 3c. The remaining ~175 arms (bucketed; full classification at Row 1 gate)

- **Parameter setters** (`set …` style, carry an argument, call `save_config_delayed`) → **TYPED-ONLY** + `CMD_PERSISTS`.
- **Parameter / state reads** (`chip_id :1135`, `get_num_modes :1169`, dumps, status) → **SAFE**.
- **Harness/debug surfaces** (`dump_raw`, legacy `ap_stream=on|off`, structured `ap_capture=<ms>`, `vp_probe`, legacy `vp_out_test`, `frame_dump` — flag-gated per `03-…§1.1` where applicable) → mostly **TYPED-ONLY**; note `dump_raw` already has its own arm (`:1464`) — fold into the generalised arm-state. Calibration-adjacent legs inherit **ARM-REQUIRED** if they assume silence.

---

## 4. CANDIDATE behaviour-delta list (Captain signs the final list at Row 1 gate)

These are the points where **current behaviour must change** to satisfy the taxonomy. Everything not listed must be **behaviour-preserving** (verified by the differential test, §5).

| # | Delta | From → To | Risk if unaddressed |
|---|---|---|---|
| **D1** | `start_noise_cal` (typed) — the ungated cal trigger — is **removed** (resolved by D5); `N`→`Y` remains the sole, silence-gated path. | immediate-fire typed command → **deleted** | **The Stage-7 poisoning class.** Removal is cleaner than gating: no typed path can fire cal at all. |
| **D2** | `factory_reset`, `restore_defaults`, `clear_noise_cal` gain a confirm gate and are asserted unreachable from any keystroke. | `ack()`+immediate execute → FORBIDDEN-FROM-SINGLE-BYTE + arm/confirm (or typed confirmation token) | One stray keystroke / pasted byte can wipe config or cal with no undo. |
| **D3** | Generalise the noise-cal arm machinery (`serial_noise_cal_arm_*`, `:525–552`) into a class-driven arm-state any ARM-REQUIRED / FORBIDDEN row can require; fold `dump_raw`'s ad-hoc arm (`:1464`) into it. | one bespoke arm flag → one shared arm primitive | Per-command bespoke gates drift; a new destructive command silently ships ungated (the C1 failure mode). |
| **D4** | Help/status output (`serial_print_hotkey_help :661`, `…status :721`, help dumps `:1023–1033`) iterate the table instead of hand-maintained `println`s. | duplicated literal lists → table-derived | Help text already drifts from real commands; a safety-class column in help makes the contract visible to operators. |
| **D5** ✅ RULED (Captain 2026-05-25) | **Drop typed `start_noise_cal`.** Default = `N`/`Y`-only, gated by explicit Captain silence confirmation. Retain the typed form ONLY if a hard lab-automation reason is documented — and then it must be `ARM-REQUIRED`, never immediate. | typed command → deleted (default) | Removes the ungated cal surface entirely; smallest attack surface. |
| **D6** ✅ RULED (Captain 2026-05-25) | **Typed confirmation tokens** for the destructive trio: `factory_reset CONFIRM`, `restore_defaults CONFIRM`, `clear_noise_cal CONFIRM`. **No** shared timed arm window for these. The timed window stays exclusively for silence-dependent cal (ARM-REQUIRED). | bare command → usage line; `<cmd> CONFIRM` → execute | Tokens are auditable in logs and not tripped by accidental serial input. |

**Behaviour-preserving (NOT deltas):** all SAFE toggles/reads, the existing N/Y semantics, the 5 s arm window value, ack/tx framing, and the exact set of recognised command tokens. The table replaces *dispatch mechanism*, not *command vocabulary* — except where a delta above is explicitly signed off.

---

## 5. Row 1 equivalence requirement (carried from 02-MATRIX / HANDOFF item D)

The strcmp→table swap must be proven behaviour-preserving:
- A **differential test fires every one of the 186 commands** (and each immediate hotkey) and checks the handler invoked + observable effect against the pre-split build. (HANDOFF-to-k1-rooted-session.md item D: strcmp prefix-match ordering can differ from table lookup — this is the named migration risk.)
- The test must encode the delta list (§4) as the *expected* differences; every other command must match exactly.
- This runs under the Row 1 hardware-harness gate (`03-hardware-gate-package.md §1.6`), AP-semantics where a command touches audio/cal state.

---

## 6. Hand-off to Row 1 execution (when authorised)

1. Captain reviews this taxonomy + signs the §4 delta list (resolving D5/D6).
2. Build the differential test that fires all 186 commands (§5) against the current single-TU build — *before* any restructuring.
3. Extract the strcmp chain → `const` dispatch table with the §2 schema; add the boot/compile-time assertion that no FORBIDDEN row carries a hotkey.
4. Generalise the arm-state (D3); apply D1/D2 gates.
5. Differential test must pass with exactly the signed deltas; Row 1 hardware gate per cadence.

**No part of steps 1–5 runs in this Phase-0 artefact.**

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-25 | claude-code (Opus 4.7) | Captain rulings folded in: **D5** — drop typed `start_noise_cal` (N/Y-only default; ARM-REQUIRED if retained for documented lab-automation). **D6** — destructive trio (`factory_reset`/`restore_defaults`/`clear_noise_cal`) confirmed via typed `CONFIRM` token, NOT a timed arm window. Updated taxonomy (FORBIDDEN gate = typed token; ARM-REQUIRED window reserved for silence-dependent cal), §2 runtime enforcement, §3a classifications, §4 D1/D5/D6 (D1 now resolved by removal), and status. |
| 2026-05-25 | claude-code (Opus 4.7) | Created. Row 1 dispatch-table safety-class **sketch** (Phase 0, task #12). 4-class taxonomy (SAFE / ARM-REQUIRED / FORBIDDEN-FROM-SINGLE-BYTE / TYPED-ONLY); dispatch-table row schema + structural enforcement; source-verified classification of the destructive set (`start_noise_cal`, `factory_reset`, `restore_defaults`, `clear_noise_cal`, `reset`) and the single-byte hotkey set (serial_menu.h @ 00a0fcb); candidate behaviour-delta list D1–D6 with the typed-`start_noise_cal`-bypass (D1) as the load-bearing fix; equivalence/differential-test requirement. No code changed. Awaiting Captain review of taxonomy + delta list at Row 1 gate. |
