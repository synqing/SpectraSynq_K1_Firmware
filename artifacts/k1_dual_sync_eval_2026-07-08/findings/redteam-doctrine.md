---
abstract: "Red-team (doctrine/product-truth lens) attack on the dual-K1 sync DRAFT v0.1. Verdict: SOUND_WITH_FIXES. No Captain-ratified decision is quietly reopened (IM73D, Model C, PEND/CONF, dual-channel doctrine all safe; F1/F2 correctly surfaced). Four MAJOR wounds: Phase-0 'bench units only' is a false plurality (second device is Captain's primary 1401 under per-device flash authorisation); AGC/cal adoption is unspecified against per-device cal truth and the SWEET_SPOT-poisoning precedent; the 71-control contract in widened mode is undefined (mirror toggle, follower-local inputs, cal-path mirroring, K718 dial binding); the radio-isolation guard is token-blind to new sync source until Phase 4."
---

# Red-Team — Doctrine / Product-Truth Lens (dual-K1 sync DRAFT v0.1)

Reviewer stance: adversarial. Every attack below was checked against real
source or registry text this session; citations are file:line actually read.

## Steel-man honesty (what the draft gets RIGHT — verified, not assumed)

1. **No quiet reopening of Captain-ratified decisions.** IM73D production mic
   decision untouched (leader-mic uses IM73D as-is). K718 Model C picker and
   PEND/CONF ban untouched (no on-screen status text is proposed; K1→dial
   feedback stays the existing CC 0x20/0x21 confirm path). The WiFi/UF2
   conflict is surfaced as fork F2, not smuggled — that is the correct shape.
2. **Dual-channel doctrine claim verified accurate.** `K1BufferView.h:5-11`
   really does document the deliberate per-strip view ("NOT one contiguous 320
   array … never a unified 320 span"); the plan's seam-centred mirror-split
   across two DEVICES does not re-unify one device's two channels, and §7
   explicitly protects this.
3. **Forks F1–F4 are genuinely Captain-grade**, not chore escalation: F1 =
   production radio stance (launch/product), F2 = boundary of a ratified
   decision, F3 = doctrine-protected channel scope, F4 = visual decision under
   the standing HTML-mockup rule. No dashboard/lookup chores are escalated.
4. **The lane is honest about the launch path**: §4.5/§7 declare this
   post-launch-class, decision-value-only, no implementation in-lane.
5. **Instrumentation pattern for Phase 0 matches precedent**: probe envs
   gated by `#ifdef` TU guards + `build_src_filter` (`sb_k1_wireless.cpp:1`,
   `platformio.ini:44,353-365`), MabuTrace confined to non-shippable envs —
   consistent with the Developer Instrumentation Boundary. (But see Attack 4
   on the artefact guard's token blindness.)

## Attacks (most severe first)

### A1 · MAJOR — Phase 0's "bench units only" is a false plurality; the second device is Captain's primary

`docs/hardware/device-build-registry.md` §1: exactly **two** K1 units exist —
**12201** (bench K1v2, `B489A500`) and **1401** (main K1, "Captain's
primary", `F887A500`). There is no second bench K1. A two-device transport
bake-off and the two-device k1_motion_probe therefore MUST flash Captain's
primary unit. The registry carries a standing rule: "**Never flash any device
without Captain's per-device instruction** (2026-06-11)", with the only
standing authorisation scoped to the K1↔Tab5 phase — not this lane. Aggravating
context the plan ignores: the bench bus currently hosts an **unregistered 4th
ESP32-S3** and a **Tab5 P4** on scrambled ports (registry 2026-06-19/21
tables), and a wrong-env flash already produced the 2026-07-07 dark-output
incident. Also, `k1_upload_guard.py` only accepts registered env↔chip pairs, so
each `k1_sync_probe` variant (one per GPIO map: 4/5 bench, 6/7 main) must be
registered in the guard before any flash — the `k1_bench_reference_harness`
episode (2026-06-21) is the exact precedent to copy.

**Failure scenario:** Phase 0 kicks off "bench-only", an agent flashes 1401
with a probe build without per-device authorisation (rule violation, and 1401
is currently on a temporary eyes-on build per the registry — a probe flash
destroys that state), or flashes the unregistered S3/Tab5 on a drifted port.

**Fix:** Phase 0 preconditions must state: (a) devices = 12201 + 1401
explicitly, (b) Captain per-device flash authorisation for 1401 is a named
precondition (fold into F1 or the Phase-0 kickoff), (c) probe env pair
registered in `k1_upload_guard.py` before first flash, (d) registry
deployed-state + restore-baseline plan for 1401 recorded.

### A2 · MAJOR — "Follower adopts leader AGC/brightness" is unspecified against per-device cal truth and the cal-poisoning precedent

Plan §2: "AGC/brightness scalars: follower adopts leader values." The lane's
own evidence says per-device cal baselines "would be wrong, not sync" to copy
(`findings/control-surface.md` §(c)4): `CONFIG.DC_OFFSET`,
`SWEET_SPOT_MIN/MAX_LEVEL` and `noise_samples[80]` are per-device, PERSISTED,
and mutated via `save_config_delayed()`. The repo carries a live scar for
exactly this class: the 2026-05-24 incident that poisoned
`SWEET_SPOT_MIN_LEVEL` (281 → 745) and produced the load-bearing calibration
policy. The plan does not distinguish (i) RAM-only AGC state
(`agc_envelope`, `agc_noise_floor`, `globals.h:704-706`) from (ii) persisted
cal-derived CONFIG fields, nor does it state that adoption is RAM-only and
non-persisting, nor that the follower's OWN AGC/cal state is preserved and
restored on link-loss fallback to its own mic (plan §2 failure stance). It is
also unclear why AGC adoption is needed at all if the follower renders from
leader-processed features — the streamed features already carry leader gain;
if adoption is only for local brightness scaling, say precisely which scalars.

**Failure scenario:** adopted leader values leak into the follower's persisted
CONFIG (5 s debounced save fires on any facade setter path), silently
overwriting the follower's own room/mic cal; on link loss the follower falls
back to its own mic with the leader's gain — wrong output AND a poisoned
persistent cal, repeating the 2026-05-24 incident by architecture.

**Fix:** Phase 1 protocol spec must classify every streamed scalar as
RAM-only-adopt / never-adopt (all `CONFIG` cal fields = never-adopt), assert
in the host harness that sync application never triggers `save_config_delayed`
for cal fields, and specify own-state restore on fallback. The silence-gated
`start_noise_cal` policy remains untouched by sync (no auto-fire path).

### A3 · MAJOR — The 71-control contract in widened mode is undefined; one-way mirror ignores follower-local inputs and the dial-binding question

Plan §2 says only "control mirror through `sb_k1_control_apply()` (the 71-path
facade)". Unresolved, all doctrine-adjacent:

1. **Path semantics in widened mode.** The widened geometry FORCES mirror off
   and flips the left unit. The 71 paths include `primary.mirror`
   (`CONFIG.MIRROR_ENABLED`), `REVERSE_ORDER`, `secondary.*`, and
   `calibration.noise.arm/confirm`. Blanket mirroring breaks geometry (a
   mirrored mirror-toggle re-mirrors both halves), and mirroring cal commands
   auto-fires noise-cal on the follower as a side effect of a leader action —
   a decision the plan never makes (defensible in a shared silence window,
   but it must be DECIDED, and the cal-silence gate is never waived).
   A per-path transform table (mirror / transform / leader-only / blocked)
   is required, not implied.
2. **Follower-local inputs are un-mirrored back-channels.** The follower still
   has its own GPIO mode button (long-press toggles MIRROR_ENABLED,
   `persistence/buttons.h:53`), encoders, serial hotkeys — five input
   surfaces mutating the same globals (`findings/control-surface.md` §(b)).
   One press on the follower desynchronises control state with no recovery
   path in the plan. Decide: block, forward-to-leader, or accept-and-resync.
3. **Dial binding.** The K718 is one peripheral; K1s are centrals. The plan
   implies leader-only dial ownership but never states it, and the
   K718-accepts-two-centrals question is explicitly unproven
   (`findings/wireless-inventory.md` §(c)). What happens if the dial binds
   the follower — role handoff, rejection, or leadership follows the dial?
   This is the "who does the dial control" product question and it is absent.

**Fix:** Phase 1 must deliver the widened-mode control contract table (71
rows), the follower-local-input stance, and the dial-binding rule; the host
harness asserts them.

### A4 · MAJOR — Radio-isolation guard is token-blind to the new sync surface until Phase 4

`scripts/ble_midi/guard_k1_radio_isolation.py` enforces isolation by a FIXED
token list (config + artefact) that is entirely BLE-Remoted-specific
(`SB_K1_BLE_REMOTED`, `ble_remoted_central.cpp`, `NimBLE`, Remoted UUIDs…).
New sync source — a GATT sync TU, and especially an ESP-NOW TU which shares
zero tokens with that list — is INVISIBLE to the guard. The plan defers guard
updates to Phase 4 ("guards updated … semantics"), but sync source lands in
the tree at Phase 1 and radio probe envs at Phase 0. Between Phase 1 and
Phase 4 the only isolation is `build_src_filter` + `#ifdef` discipline, with
the artefact-scan backstop absent for the new tokens.

**Failure scenario:** a sync define is accidentally added to a production
env's build_flags (or a src_filter edit pulls the TU in); the guard runs,
finds none of its BLE-Remoted tokens, and passes a radio-bearing production
binary — precisely the class of leak the guard exists to catch, silently
green.

**Fix:** extending the guard token list (config defines + artefact strings
for the sync TU and, if built, ESP-NOW symbols like `esp_now_init`) is a
Phase-0/Phase-1 deliverable shipped WITH the first sync source, not a
Phase-4 productionisation item.

### A5 · MINOR — Asymmetric transport framing risks biasing the bake-off

"BLE custom GATT … aligns with UF2 ('BLE-MIDI is the control surface')"
overstates: UF2 (handover 2026-06-30:15) ratified BLE-MIDI as the K718
CONTROL surface; it did not ratify BLE-anything as an approved radio class
for a net-new K1↔K1 stream. Conversely, "ESP-NOW … same radio, not a WiFi
network" understates: ESP-NOW requires initialising the esp_wifi driver
(the WiFi stack UF2 dropped), which is exactly why F2 exists. Neither
transport is UF2-covered; both sit under F1. Symmetrise the framing so
Phase 0 is decided on measured numbers, not inherited wording. (The plan's
substance — measure both, gate hard — is right; only the framing tilts.)

### A6 · MINOR — Launch-path scheduling and the launch-lock reference

The plan honestly labels this post-launch-class, but the phases read
ready-to-execute and Phase 0 is "~bench-week class" of bench time plus two
Captain eyes-on gates (Phases 2–3). State explicitly that STARTING Phase 0 is
itself a Captain scheduling decision against K1 → FE → Kickstarter (fold into
F1's presentation). Separately, Phase 4's "launch-lock review" cites locks
this repo does not contain — `docs/LAUNCH_LOCKS.yaml` lives in the
landing-page workspace per the Decision Authority Firewall; no launch-lock
file exists in this firmware repo (verified by search). Name the actual
Tier-0 document Phase 4 will re-read, or the review step is theatre.

## Missed considerations (not attacks, gaps the plan should absorb)

- `factory_reset()` deletes config + cal (`bridge_fs.h:86-126`); the sync-role
  LittleFS file's reset behaviour is raised in the evidence
  (`findings/control-surface.md` §(d)) but undecided in the plan.
- The registry's unregistered 4th ESP32-S3 on the bench bus is a live
  wrong-target hazard for any two-device lane; Phase 0 should identify it or
  fence it before multi-device flashing.
- SmartDirector autonomy (`scene.smart=auto`) on the follower is another
  divergence source (independent mode-switch decisions,
  `sb_k1_control_facade.cpp:211-223`); the plan's control mirror covers
  director SETTINGS but not director DECISIONS — widened mode likely needs
  follower-director suppression, unstated.

## Verdict

**SOUND_WITH_FIXES.** No KILL: the architecture (leader features, mirror-split,
phased gates, Captain forks) survives this lens, and the draft is unusually
clean on ratified-decision fidelity. The wounds are specification gaps —
device/authorisation preconditions (A1), cal/AGC adoption semantics (A2), the
widened-mode control contract (A3), and guard timing (A4) — each fixable
inside the existing phase structure without changing the recommendation.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (red-team, doctrine lens) | Created — adversarial doctrine/product-truth review of DRAFT v0.1: 4 MAJOR, 2 MINOR attacks; steel-man confirmations; verdict SOUND_WITH_FIXES. |
