---
abstract: >-
  Session canon for 2026-08-07→08-09 Deck16 B1/B2 close, Mirror purge, Core-0
  silent_scale / STANDBY_DIMMING strike, uncommanded-PRISM haunt, latency map≠RTT,
  layout16 false MAIN approval, exclusive-port soak contention, and first-contact
  device-absence stop. Immune memory so agents never replay this trial-and-error tax.
status: active_canon
date: 2026-08-09
architecture: K1_DECK16_TAB5_BLE_R1
branch: feat/ap-advice-phase0-im69d-gain8
head_at_handover: db300db
skill: k1-deck16-session-discipline
related_skills:
  - k1-vj-session-discipline
  - tab5-hosted-ble-debug
  - spectrasynq-ui-precode-optical-gate
guardrails: .cursor/rules/tab5-deck16-guardrails.mdc
handover: _scratch/deck16_session_handover_20260809/HANDOVER.md
thinking_models:
  - systems
  - map-territory
  - ooda
  - steel-manning
  - red-team
  - archetypes
  - model-router
  - model-combination
authority_claim_block: |
  DECK16_B1_B2_CORE_FUNCTIONAL_PASS=PASS
  EXTENDED_RECOVERY_HARDENING=PASS
  STANDBY_DIMMING=STRUCK
  PRODUCTION_READY=NO
  MERGE_OR_PROMOTION=HOLD
---

# Session Canon — Deck16 BLE Backend × Haunt × Latency × Authority (2026-08-09)

**Reader:** every future agent on Tab5↔bench-K1 Deck16 BLE, identity hashes,
deck_state pending TX, full-map harnesses, C6 soaks, dark-fade / silent_scale,
MAIN glass authority, or Mirror/STANDBY surfaces.

**Purpose:** not a diary. This is the **immune memory** of a multi-day backend +
glass session that burned wall-clock on map≠territory latency, hash archaeology,
self-certified MAIN layouts, Core-1-only dark-fade patches, haunt pending TX,
and parallel lanes murdering exclusive soaks. Violating the HARD FAIL table is a
**process incident**.

**On-disk evidence beats memory.** Primary pointer:
[`_scratch/deck16_session_handover_20260809/HANDOVER.md`](../../_scratch/deck16_session_handover_20260809/HANDOVER.md).
Live hashes: read headers / `docs/protocol/protocol-map-hashes.json` — never a
stale brief.

**Mandatory skill before Deck16 BLE / map / soak / MAIN / dark-fade work:**
[`k1-deck16-session-discipline`](../../.claude/skills/k1-deck16-session-discipline/SKILL.md).

---

## 0. One-line map of the session

| Thread | Outcome | Status |
|--------|---------|--------|
| **A. B1→B2 + recovery R1–R4** | Identity + CC14 + HELLO/SNAPSHOT/DELTA; gap/stale/overflow/MTU | **PASS** — CLOSED architecture |
| **B. Latency T0/T1/T2** | Real ~56 ms p50; ~401 ms was host poll artefact | **PASS** instrumented; do not re-cite 401 as RTT |
| **C. Layout 16/16 protocol** | Paths looped; then Mirror purge invalidated two cells | Protocol-only; **NOT MAIN approval** |
| **D. MAIN glass authority** | Agent self-PASS → audit FAIL → over-delete grid → Captain restore | Tier-1 4-box MAIN; 16-grid **encoder-reserved** |
| **E. Dark fade / STANDBY** | Core-0 pin + full STANDBY_DIMMING strike | **STRUCK**; Core-1-only patch superseded |
| **F. Mirror purge** | All BLE/Deck Mirror surfaces gone; digests moved | **PASS**; live = 68 controls |
| **G. Uncommanded PRISM haunt** | `gTxDirty` survived disconnect → auto-TX on next ARMED | Code fixed; **anti-haunt soak OWED** |
| **H. full71** | 40 PASS / 27 FAIL / 4 SKIP | **PAUSED** until anti-haunt |
| **I. C6 ≥4 h soak** | Contention kill-9, not radio | **OPEN**; exclusive window required |
| **J. First-contact 2026-08-09** | Bench present; Tab5 absent; alien MAC on port | **STOP** — no substitute device |

```text
DECK16_B1_B2_CORE_FUNCTIONAL_PASS=PASS
EXTENDED_RECOVERY_HARDENING=PASS
STANDBY_DIMMING=STRUCK
PRODUCTION_READY=NO
MERGE_OR_PROMOTION=HOLD
```

Do **not** upgrade any line without a new on-disk receipt.

---

## 1. Complete lessons inventory

### 1.1 Failures (paid for in wall-clock / silicon / NVS)

| ID | Failure | What it cost | Correct stance |
|----|---------|--------------|----------------|
| **F-1** | Trusted **stale protocol digests** from earlier briefs after Mirror purge | Hours chasing hash reject / wrong control counts | Read **live** headers + `protocol-map-hashes.json`. Archaeology digests are labelled below |
| **F-2** | Cited **~401 ms** as BLE wire RTT | False latency crisis; wrong optimisation target | On-device T0→T2 only. 401 = host poll artefact. ~4301 ms = harness wall time |
| **F-3** | Agent **self-certified** `LAYOUT_V1_16_CELL_MAIN=PASS` | Captain rejection; authority audit; thrash | Captain glass approval ≠ protocol 16/16 pass ≠ layout JSON on disk |
| **F-4** | **Deleted** 16-grid after parameter rejection | Destroyed encoder-reserved HMI infrastructure | Reject **parameter set / form on MAIN**; retain grid behind `DECK_UI_LAYOUT_MAP_DEBUG` |
| **F-5** | Patched dark fade on **Core-1 only** (`LINKED_LIT_PROOF`) | IIR race; silent_scale still dipped | **Core-0 pin** at write site in `i2s_audio.h`; Core-1 is belt-and-braces |
| **F-6** | Left STANDBY_DIMMING as a **re-enableable** product path | Dark fade returns via NVS / UI / serial | STRUCK: factory false, boot force-off, IIR compiled out, no BLE/UI/serial path |
| **F-7** | Reintroduced / left **Mirror** on BLE/Deck after product forbid | Extra controls, hash churn, glass debt | Mirror purged forever from BLE/Deck/soft keys/sheets/CC |
| **F-8** | Ran **full71 blind** (all paths including prism) | NVS `PRISM_COUNT=2.96`; haunt residue | Subset FAIL burn-down only; never re-poison; anti-haunt before resume |
| **F-9** | **`gTxDirty` / pending never cleared** on BLE disconnect | Uncommanded apply on next ARMED — haunted sessions | `deck_state_clear_pending_all` on HELLO + disconnect; soak must prove no auto-TX |
| **F-10** | Blamed **prism_gate** for "prism look" | Wrong root cause | `CONFIG.BULB_OPACITY` drives `render_bulb_cover()` — **not** gated by `prism_off` |
| **F-11** | Ran **C6 soak in parallel** with flash / other port holders | Four soak attempts murdered (longest 645 s) | Exclusive ≥4 h window; port lock file; one lane only |
| **F-12** | Treated **serial drain miss** (`linked=null`) as radio dropout | Dishonest linked ratio in 8-min sample | Separate `dial_ok`/`dial_misses` from `linked`; miss ≠ dropout |
| **F-13** | Assumed **port name** or any Espressif JTAG = Tab5 | First-contact: alien `F0:F5:BD:75:AB:38` on `usbmodem101` | MAC/chip match only; **STOP** if Tab5 absent — never substitute |
| **F-14** | Cited `deck16-layout-v1.json` / arch §P4 as **Captain MAIN** | False ratification | Header says `param_set: NOT_CAPTAIN_APPROVED` |
| **F-15** | Trusted **claude-mem** / stale handoff over receipts | Wrong digests, wrong flash SHAs | On-disk handover + headers win; memory = clues only when DEGRADED |
| **F-16** | `nohup` / Cursor background for multi-hour soak | Process group death / SIGKILL | Double-fork/setsid + exclusive lock; still vulnerable to kill -9 from parallel flash — **don't run parallel** |
| **F-17** | Optimistic / local-send-as-confirmed patterns | False LIVE glass | Single-writer deck_state; confirmed-from-DELTA only |

### 1.2 Problems resolved (with evidence packs)

| Problem | Resolution | Receipt |
|---------|------------|---------|
| B1 identity + map/layout admission + CC14 | Productised | `_scratch/deck16_backend_b1b2_20260808/` |
| B2 HELLO/SNAPSHOT/DELTA → deck_state | Single-writer facade | same |
| Recovery gap / stale-confirmed / overflow@32 / MTU23 | R1–R4 PASS | same / INTEGRATION_RECEIPT |
| Wire latency high (real) | Conn interval 50→30 ms + immediate DELTA when queue empty | `_scratch/deck16_latency_map_c6_20260809/LATENCY_RECEIPT.md` |
| Dark fade in quiet | Core-0 `silent_scale=silent_scale_last=1.0f` unconditional | `_scratch/k1_bench_dark_fade_20260809/PERMANENT_FIX_RECEIPT.md` |
| STANDBY_DIMMING as product | STRUCK entirely | `STANDBY_DIMMING_STRUCK.md` |
| Mirror on BLE/Deck | Full purge; 68 controls; digests moved | `_scratch/mirror_purge_ble_20260809/PURGE_RECEIPT.md` |
| Uncommanded PRISM TX | `deck_state_clear_pending_all` HELLO+disconnect | `_scratch/deck16_uncommanded_prism_20260809/PACK_NOTE.md` |
| False MAIN 16-param set | Tier-1 4-box; grid encoder-reserved | `_scratch/deck16_layout16_authority_audit_20260809/` |
| Precision Bay chrome | DEAD / DEPRECATED — no revival | Captain pivot + UI canons |

### 1.3 Insights (keep forever)

1. **Hash gates admit compatibility, they do not anti-spoof** — and they **move** whenever the map/layout set changes. Always re-read live digests after a purge.
2. **Host metrics are maps; silicon stamps are territory.** Prefer same-clock device T0/T1/T2 over host poll RTT.
3. **Protocol pass ≠ product MAIN.** Driving 16 paths over BLE does not approve those 16 for glass.
4. **Reject the parameter set, not the geometry** when Captain forbids MAIN content but keeps encoder infrastructure.
5. **Pin at the writer (Core-0), not the reader (Core-1)** for silence/dim scale races.
6. **Pending TX state is session-scoped.** Disconnect without clear = haunt. Treat dirty flags as security-adjacent for NVS-writing controls.
7. **Harnesses write NVS.** Blind full-map runs are production hazards, not "just tests".
8. **"Prism look" ≠ prism_count.** Bulb opacity / cover render can fake the visual without prism gate.
9. **Radio health claims require exclusive USB/serial ownership.** Parallel flash lanes invalidate soak science.
10. **Absent peer = STOP.** An unknown Espressif serial is not Tab5. Do not invent a substitute lane.

### 1.4 Still open (do not claim PASS)

| Item | Gate |
|------|------|
| Anti-haunt disconnect/reconnect soak | No auto-TX, no pending_active without touch |
| K1 reboot VP-defaults check | `PRISM_COUNT` / bulb / profile defaults after reboot |
| full71 27 FAIL burn-down | After anti-haunt; subsets only; drop mirror rows |
| C6 `bar_4h_met==true` | Exclusive ≥4 h; `hard_fail==false` |
| Optical MEASURED / role-ladder pack | Before next UI **commit** (waiver post_condition) |
| Encoders | Deferred LAST by Captain — do not start |
| PRODUCTION_READY / MERGE | **HOLD** until Captain |

---

## 2. HARD FAIL table (do not re-learn)

Continuity: Aug-07 IM69D/HCI canons own **HF-1…HF-13**. This session owns **HF-14…HF-28**.

| ID | HARD FAIL | Why we paid | Correct stance |
|----|-----------|-------------|----------------|
| **HF-14** | Cite stale digests (`78fb9af9…`/`b60819a4…` or `d30c4fef…`/`cb549042…`) as live | Mirror purge moved every digest | Live (at 2026-08-09 Mirror purge): **68** controls, registry MD5 `9b5db3fbb17438367adeaceb541db03b`, layout SHA `f8e40f6b1ba7b115bb5e9f7310ac69636e0a10c8e478f7584dd1d5547b941510` — **re-verify on disk before quoting** |
| **HF-15** | Cite **~401 ms** (or ~4301 ms) as BLE apply / wire RTT | Host poll / harness wall artefacts | Quote only on-device T0→T2 (`LATENCY_RECEIPT`) |
| **HF-16** | Treat `deck16-layout-v1.json`, `LAYOUT_CELLS.md`, arch §P4, or agent `LAYOUT_V1_16_CELL_MAIN=PASS` as Captain MAIN approval | Self-certification | MAIN = Tier-1 4-box until Captain + encoders |
| **HF-17** | Delete or permanently disable the 16-grid / `deck_ui_layout_map` | Over-correction | Keep behind `DECK_UI_LAYOUT_MAP_DEBUG` default 0 |
| **HF-18** | Put chroma / saturation / mirror / `secondary.enabled` / `prism_count` on MAIN glass | Banned / banished / Tier-2 | Soft-key sheets only after Captain sheet lock; secondary always live |
| **HF-19** | Re-enable **STANDBY_DIMMING** via UI/map/serial/NVS/build flag | Dark fade returns | Keep struck; NVS field may exist as forced 0 |
| **HF-20** | Weaken / remove Core-0 **silent_scale pin** | Dark fade returns under quiet | Any K1 flash must contain `i2s_audio.h` pin |
| **HF-21** | Reintroduce **MIRROR** to BLE/Deck (any synonym or stub) | Product forbid + hash churn | `CONFIG.MIRROR_ENABLED` internal only; USB bring-up only |
| **HF-22** | Resume full71 / map harness without **anti-haunt proof** | NVS poison + ghost TX | Verify `deck_state_clear_pending_all` + disconnect soak first |
| **HF-23** | Blind re-run **all** map paths after a FAIL matrix | PRISM incident | Burn down **FAIL subset only**; keep silence SKIPs skipped |
| **HF-24** | Run multi-hour soak **while any other lane flashes / holds ports** | Four dead soaks | Exclusive window + `_scratch/C6_SOAK_PORT_LOCK.json`; ask Captain A XOR B |
| **HF-25** | Claim radio dropout from **`linked=null` dial misses** | Dishonest sample | dial_miss ≠ unlink |
| **HF-26** | Substitute an unknown USB serial for Tab5 / bench | Wrong silicon | Match MAC `30:ED:A0:E0:C1:A0` (Tab5) / chip `B489A500` (bench); else STOP |
| **HF-27** | Flash C6 / main K1 `F887A500` / SoftAP / erase / commit without Captain | Hard bans held all session | Never |
| **HF-28** | Reopen B1→B2 architecture / optimistic ack_tx / Precision Bay | Closed / DEPRECATED | Do not |

### Canon sentences (memorise)

1. **Live digests live in headers — briefs rot the moment a purge lands.**
2. **Host RTT is a map; T0→T2 on-device is the territory.**
3. **Protocol loop PASS is not Captain MAIN approval.**
4. **Pending dirty across disconnect is a haunt — clear or you will ship ghosts.**
5. **Pin silence scale at Core-0; Core-1 patches lie under race.**
6. **Exclusive hardware ownership is a correctness requirement for soak science.**
7. **Absent peer → STOP. Alien Espressif ≠ Tab5.**

---

## 3. Systems / archetypes / map–territory (why the tax happened)

### 3.1 Systems loops

```text
Reinforcing — Haunt:
  map= / UI pending → gTxDirty=1 → disconnect (no clear)
       → next ARMED → auto TX → K1 apply → NVS → "uncommanded" surprise
       → more harness "fixes" without clearing → worse

Reinforcing — Soak murder:
  lane A holds port for soak → lane B needs flash → kill -9 holder
       → soak dies → restart soak → another flash → die again

Balancing (correct) — Latency:
  measure host poll RTT (false high) ──X──► don't optimise that
  measure T0/T1/T2 ──► shorten conn interval + flush DELTA when idle

Fixes that Fail — Dark fade:
  Core-1 force silent_scale ──► looks fixed ──► Core-0 IIR rewrites ──► fades again
  Leverage: pin at Core-0 write site + strike STANDBY_DIMMING product path

Shifting the Burden — MAIN:
  Captain rejects params ──► agent deletes grid (symptom "fix")
  ──► loses encoder infrastructure ──► must restore grid + hide it
  Leverage: separate "what is on MAIN" from "what geometry exists"
```

### 3.2 Map–territory traps

| Map trusted | Territory measured |
|-------------|-------------------|
| Brief MD5/SHA from yesterday | Mirror purge moved digests; 70→68 controls |
| ~401 ms host RTT | ~56 ms device e2e |
| `layout16 PASS` / JSON on disk | No Captain MAIN approval; P7/S8 later blank |
| Core-1 silent_scale patch receipt | Core-0 still wrote dips |
| `linked=null` tick ratio | Serial drain misses under AP spam |
| `usbmodem101` Espressif present | MAC `F0:F5:BD:75:AB:38` ≠ Tab5 |
| prism_off / prism_count gate | BULB_OPACITY cover render |
| full71 PASS count mid-run | Pending haunt + NVS side effects |

### 3.3 OODA for first contact (mandatory order)

1. **Observe:** `pio device list` + pyserial MAC/chip; live header hashes.
2. **Orient:** match bench `B489A500` / Tab5 `30:ED:A0:E0:C1:A0`; classify archaeology digests.
3. **Decide:** if either peer absent → STOP and report; else continue Steps 2–4 of handover.
4. **Act:** dark-fade silicon read → link/admission → anti-haunt → **ask Captain** Lane A XOR B.

### 3.4 Steel-man then kill

| Tempting claim | Strongest form | Kill with |
|----------------|----------------|-----------|
| "401 ms is what operators feel" | Host path includes serial polling delay | Same-clock T0→T2 ~56 ms; 401 vanishes when instrumented on-device |
| "Delete the 16-grid — Captain hated it" | Removes forbidden MAIN params quickly | Captain hated **parameter selection**, not encoder-reserved geometry |
| "Core-1 pin is enough — render owns brightness" | Visual path is where fade is seen | Writer is Core-0; race proven; Core-0 pin is the fix |
| "Soak can share the machine if careful" | Save wall-clock | Four careful attempts still SIGKILL'd — exclusivity is the requirement |
| "Any P4-looking port is Tab5" | Ports drift; JTAG looks identical | MAC match or STOP |

### 3.5 Red-team (how the next agent will lie)

- Quote archaeology hashes from an old INTEGRATION_RECEIPT.
- Call anti-haunt PASS because markers exist in **source** but soak not run.
- Resume full71 "quickly" and re-haunt PRISM into NVS.
- Cite 8-minute soak linked ratio as radio health.
- Flash whatever is on `usbmodem101`.
- Claim PRODUCTION_READY because B1/B2 PASS.
- Treat `deck16-layout-v1.json` as ratified MAIN.
- Re-add Mirror "as reserved stub for later".

If you catch yourself doing any of these, **stop** — you are replaying this canon.

---

## 4. Live identity (verify; do not fossilise blindly)

At Mirror purge flash (2026-08-09 ~07:56–07:58), verified live:

| Field | Value |
|-------|-------|
| control count | **68** |
| `ble_midi_registry_md5` | `9b5db3fbb17438367adeaceb541db03b` |
| `deck16_layout_sha256` | `f8e40f6b1ba7b115bb5e9f7310ac69636e0a10c8e478f7584dd1d5547b941510` |
| `k1-ble-midi-map.json` sha | `2d1121bd5d1a54421b4b35ead62ba91bfba3a709c8259d35b166f25a6dc148ff` |
| Tab5 firmware sha (latest) | `4ce305b61fcad0b408e2a8425e7c8d57b5b270d75e655c50fdbd4e58b7d4d596` |
| Bench K1 firmware sha (latest) | `f59e5374be7c7c24c0a9a0b6e7503623f86c5d008b1772212754431c1fe6ef46` |

**Archaeology only (never cite as current):**

- `78fb9af9…` + layout `b60819a4…` — B1→B2 era
- `d30c4fef…` + layout `cb549042…` — STANDBY_DIMMING-strike era (70 controls)

**Devices (identity ≠ port):**

| Role | MAC / chip | Env | Ban |
|------|------------|-----|-----|
| Bench K1 | `b4:3a:45:a5:89:b4` / `B489A500` | `k1_bench_im69d_ble` | only this for Deck16 link |
| Tab5 P4 | `30:ed:a0:e0:c1:a0` | `tab5_p4` | required peer |
| Tab5 C6 | hosted HCI IF=4 | — | **never reflash this lane** |
| Main K1 | `b4:3a:45:a5:87:f8` / `F887A500` | `k1_hardware` | **DO NOT TOUCH** |

---

## 5. Evidence index (receipts)

| Pack | Why |
|------|-----|
| `_scratch/deck16_session_handover_20260809/` | Master handover + FIRST_CONTACT_PROMPT |
| `_scratch/deck16_backend_b1b2_20260808/` | B1/B2 + CAPTAIN_PIVOT |
| `_scratch/deck16_latency_map_c6_20260809/` | Latency + C6 soak |
| `_scratch/mirror_purge_ble_20260809/` | Live digests / flash SHAs |
| `_scratch/k1_bench_dark_fade_20260809/` | Core-0 pin + STANDBY strike (**not** LINKED_LIT_PROOF) |
| `_scratch/deck16_uncommanded_prism_20260809/` | Haunt root cause |
| `_scratch/deck16_full71_map_20260809/` | 40/27/4 matrix |
| `_scratch/deck16_layout16_authority_audit_20260809/` | MAIN authority |
| `_scratch/deck16_replacement_ui_20260809/` | Tier-1 MAIN (waiver optical owed) |
| `docs/architecture/TAB5_DECK16_SESSION_CANON_2026-08-07.md` | HCI / K718 / earlier Tab5 canon |
| `docs/canon/SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md` | HF-1…13 |
| `docs/canon/SESSION_CANON_2026-08-09_ui_precode_optical_gate.md` | UI optical gate |

**Superseded (history only):**  
`_scratch/k1_bench_dark_fade_20260809/LINKED_LIT_PROOF.md`,  
agent self-signed MAIN layout PASS, pre-Mirror full71 mirror rows.

---

## 6. Encoding surfaces (so this sticks)

| Surface | Role |
|---------|------|
| This file | Canonical immune memory |
| `.claude/skills/k1-deck16-session-discipline/` (+ `.cursor` / `.codex`) | HARD FAIL checklist agents must run |
| `.cursor/rules/tab5-deck16-guardrails.mdc` | Always-on forbids when editing Tab5/protocol/network |
| `scripts/agent/deck16-first-contact-gate.sh` | Machine-check Step 1 identity + live hash echo |
| `docs/spec-index.md` | Routing so agents find this before acting |
| Handover FIRST_CONTACT_PROMPT | Human paste for cold starts |

---

## 7. Relation to other canons

- **Does not replace** Aug-07 IM69D/HCI HF-1…13 — load both when both domains apply.
- **Does not replace** UI optical gate canon — glass craft still needs MEASURED receipts.
- **Architecture docs** describe intended design; **this file** records what burned us when maps lied.

---

*Built under systems + map–territory + OODA + steel-man + red-team + archetypes (Fixes That Fail, Shifting the Burden, Escalation on shared ports). Choose legacy over liability.*
