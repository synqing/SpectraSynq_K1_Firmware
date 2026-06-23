---
abstract: "Lane 9 read-only sweep of claude-mem persistent memory store for K1v2 textual occurrences scoped to project 'SensoryBridge-main 9'. Identified 43 observation rows containing 'K1v2' or 'SB_K1V2_HARDWARE' text. Observations are structurally NOT in-repo files — they live in claude-mem's SQLite store. claude-mem MCP exposes search/timeline/get_observations (read APIs) but NO public observation-text write API as of 2026-05-23, so the textual purge proposed by lane-1 cannot be mechanically applied to historical observation rows. Captain decision required: (a) leave observation text untouched as historical forensic record (recommended), (b) attempt direct sqlite mutation against the claude-mem DB (out-of-policy without explicit authorisation), or (c) write follow-on 'rectification' observations that explicitly supersede each K1v2-tagged row. High-salience observations (#54168 LEDC/PSRAM/WDT crash, #54171 LEDC guard sweep, #54172 USB serial oscillation) carry load-bearing engineering content that MUST remain semantically intact; the K1v2 → K1 hardware substitution is naming-only. Session/prompt rows (S-prefix, P-prefix) are NOT included — only persistent 'obs' rows enumerated."
---

# Lane 9 — claude-mem observations K1v2 purge

Scope: claude-mem persistent memory store, project filter `SensoryBridge-main 9`
Search queries: `K1v2`, `SB_K1V2_HARDWARE` (FTS5)
Total observation rows containing K1v2 text: 43
Total session-card rows (S-prefix, NOT modifiable): 20 (excluded — not persistent observations)
Total prompt rows (P-prefix, user-uttered): 12 (excluded — forensic verbatim, MUST NOT be modified)
Sweep date: 2026-05-23

## Observations Identified

| Obs ID | Date | Type | Title (current) | K1v2 Excerpt (from facts/subtitle) | Proposed Replacement |
|--------|------|------|-----------------|------------------------------------|----------------------|
| 53195 | 2026-05-20 | discovery | K1 Hardware Architecture Clarified: Dual-Edge LGP with Independent Channel Injection | (K1v2 in narrative — full text not extracted; SBM9 project, salience: architectural foundation) | "K1 hardware" in narrative; title already clean |
| 53203 | 2026-05-20 | decision | Launch of 20+ Parallel SSA Architecture Excavation for K1v2 VP/AP Drift Analysis | Title + facts reference "K1v2 firmware" and "K1v2 VP/AP" | "K1 hardware" (prose); title → "...K1 Hardware VP/AP Drift Analysis" |
| 53229 | 2026-05-20 | discovery | K1v2 Firmware Root Location and Architecture Confirmed | Title K1v2; path confirmation for `K1.node2-feat-new-webapp-bootstrap/firmware/src/parameters.h` | Title → "K1 Hardware Firmware Root Location and Architecture Confirmed" |
| 53230 | 2026-05-20 | discovery | K1v2 Has ZERO Dual-VP Independence — Confirmed Architectural Absence | Title K1v2; load-bearing dual-VP forensic claim | Title → "K1 Hardware Has ZERO Dual-VP Independence..." |
| 53231 | 2026-05-20 | discovery | K1v2 Goertzel AP Has Symmetric Smoothing — Missing Asymmetric Attack/Release | Title K1v2; load-bearing audio-pipeline claim | Title → "K1 Hardware Goertzel AP Has Symmetric Smoothing..." |
| 53232 | 2026-05-20 | discovery | Canonical K1v2 Firmware Path Confirmed as firmware-v3 — Actor Model Architecture | Title + facts reference K1v2; load-bearing firmware-v3 path-of-truth | Title → "Canonical K1 Hardware Firmware Path..."; preserve `firmware-v3` literal |
| 53233 | 2026-05-20 | change | Master Brief Written for 30-Agent K1v2 Soul Excavation Wave | Title K1v2; reference to `.planning/k1-vp-drift/00_MASTER_BRIEF.md` | Title → "...30-Agent K1 Hardware Soul Excavation Wave" |
| 53254 | 2026-05-20 | decision | Captain directed firmware-v3 recovery work to be done inside SensoryBridge-main 9 project folder | (K1v2 may appear in narrative — title is clean) | Replace K1v2 → K1 hardware in narrative only if present |
| 53278 | 2026-05-20 | decision | Captain Locks Three Strategic Audio/Product Decisions for Full K1v2 Recovery | Title K1v2; load-bearing decision row | Title → "...Full K1 Hardware Recovery" |
| 53281 | 2026-05-20 | discovery | F-6.1 Zone AGC Quality Gate Opens — "Technically Stable but Emotionally Dead" Risk Identified | (K1v2 may appear in narrative; title is clean) | Substitute in narrative only if present |
| 53282 | 2026-05-20 | feature | Four New Dual-VP Quality Gates Opened in BACKLOG.md (VP-1 through VP-4) | (K1v2 may appear in narrative; title is clean) | Substitute in narrative only if present |
| 53352 | 2026-05-20 | discovery | K1v2 Hardware Serial Port Confirmed: /dev/cu.usbmodem1301 | Title K1v2; port identity record | Title → "K1 Hardware Serial Port Confirmed..." |
| 53384 | 2026-05-20 | discovery | Heartbeat Edge Mapping Confirmed Inverted: edges[0] (warm/orange) Renders on Physical Bottom | (K1v2 in narrative — title is clean) | Substitute in narrative only |
| 53385 | 2026-05-20 | feature | K1 Terminology Rule Persisted to Agent Memory: "lamp" is Banned, Always Use "K1" | (Naming-rule memo; check narrative for K1v2 prose) | Substitute in narrative only if present |
| 53386 | 2026-05-20 | change | HeartbeatDualVpEffect v2: Replaced Brightness Follower with Per-Pixel Energy Advection + Decay Physics | (K1v2 may appear in narrative; title is clean) | Substitute in narrative only if present |
| 53856 | 2026-05-22 | discovery | K1.Lightwave / SensoryBridge Memory Archaeology — Session Index Found | (K1v2 likely in narrative — session index over `SensoryBridge-main 9/audit/understanding/K1_LIGHTWAVE_INVESTIGATION_BRIEF.md`) | Substitute in narrative only |
| 53862 | 2026-05-22 | discovery | Codebase retrieval rate-limited during K1.Lightwave palette audit | (K1v2 likely in narrative) | Substitute in narrative only |
| 54101 | 2026-05-22 | change | Perfect Dual-Channel Config Snapshot Persisted to Docs | Title clean; narrative references K1v2-flashed device chip ID 763E7500 implicitly via firmware 40102 | Substitute in narrative only if K1v2 string present |
| 54120 | 2026-05-22 | decision | S3 Port Target Changed to K1v2 Hardware on Bench | Title + subtitle K1v2 | Title → "S3 Port Target Changed to K1 Hardware on Bench" |
| 54121 | 2026-05-22 | discovery | Existing SB-S3 Port Located at /Users/spectrasynq/Workspace_Management/Software/K1.Lightwave | Subtitle: "...for the K1v2 hardware already exists locally..." | Subtitle K1v2 → K1 hardware |
| 54122 | 2026-05-22 | discovery | K1v2 SB-S3 Port Compile Results and Pin Map Documented from K1.Lightwave | Title K1v2 + GPIO context | Title → "K1 Hardware SB-S3 Port Compile Results..." |
| 54125 | 2026-05-22 | feature | K1v2 Hardware GPIO Map Added to constants.h Behind SB_K1V2_HARDWARE Guard | Title + subtitle K1v2 + macro identifier | Title → "K1 Hardware GPIO Map Added to constants.h Behind SB_K1_HARDWARE Guard" |
| 54128 | 2026-05-22 | feature | system.h Hardware-Absent Pin Guards Added for K1v2 Compatibility | Title + subtitle K1v2 | Title → "...for K1 Hardware Compatibility" |
| 54129 | 2026-05-22 | feature | buttons.h and serial_menu.h Guarded for Absent K1v2 Pins | Title + subtitle K1v2 | Title → "...Absent K1 Hardware Pins" |
| 54130 | 2026-05-22 | feature | K1v2 Compile Script Added and Migration Prep Doc Corrected to Use firmware-v3 Pin Map | Title + subtitle K1v2; `tools/compile-k1v2-arduino.sh` reference | Title → "K1 Hardware Compile Script Added..."; preserve script path literal until rename ships |
| 54131 | 2026-05-22 | bugfix | compile-k1v2-arduino.sh Build Property Flag Corrected to compiler.cpp.extra_flags | Title + subtitle reference SB_K1V2_HARDWARE | Subtitle macro → SB_K1_HARDWARE; preserve script-path literal until rename ships |
| 54132 | 2026-05-22 | feature | SB Firmware Successfully Compiled and Uploaded to K1v2 Hardware | Title + subtitle K1v2 + SB_K1V2_HARDWARE | Title → "...Uploaded to K1 Hardware"; subtitle macro → SB_K1_HARDWARE |
| 54136 | 2026-05-22 | discovery | K1v2 First-Boot Telemetry Reveals Two Critical Issues: USB Name and 76 FPS | Title K1v2 — telemetry/FPS forensic record | Title → "K1 Hardware First-Boot Telemetry..." |
| 54138 | 2026-05-23 | discovery | K1v2 Low FPS Suspected Caused by Blocking I2C Loop on Absent 8Encoder | Title K1v2 — root-cause hypothesis | Title → "K1 Hardware Low FPS Suspected..." |
| 54139 | 2026-05-23 | bugfix | Encoder Polling Disabled on K1v2 and USB Descriptor Cleaned Up to Fix FPS and Naming | Title K1v2 + subtitle SB_HAS_ROTATE8_ENCODERS | Title → "Encoder Polling Disabled on K1 Hardware..."; note SB_HAS_ROTATE8_ENCODERS was an obsolete naming, final is SB_HAS_ROTATE8 |
| 54148 | 2026-05-23 | feature | Three Hardware Capability Macros Added for K1v2 vs S2 Feature Gating | Title K1v2 + SB_K1V2_HARDWARE in facts | Title → "...for K1 Hardware vs S2 Feature Gating"; SB_K1V2_HARDWARE in facts → SB_K1_HARDWARE |
| 54149 | 2026-05-23 | feature | FirmwareMSC Global Instance Guarded by SB_ENABLE_USB_MSC_UPDATE | (K1v2 in facts/narrative) | Substitute K1v2 → K1 hardware in narrative |
| 54150 | 2026-05-23 | feature | system.h USB MSC and Custom Descriptor Code Fully Gated for K1v2 | Title K1v2 + facts SB_USB_CUSTOM_DESCRIPTORS | Title → "...Fully Gated for K1 Hardware" |
| 54152 | 2026-05-23 | bugfix | ROTATE8 Encoder I2C Polling Fully Disabled on K1v2 via SB_HAS_ROTATE8 Guard | Title K1v2 — root-cause-fix for FPS | Title → "...Fully Disabled on K1 Hardware via SB_HAS_ROTATE8 Guard" |
| 54154 | 2026-05-23 | feature | K1v2 Compile Script Expanded with Full FastLED RMT Flags and Performance Options | Title K1v2 + SB_K1V2_HARDWARE in facts | Title → "K1 Hardware Compile Script..."; macro → SB_K1_HARDWARE |
| 54155 | 2026-05-23 | change | USB Device Name Rebranded from Lixie Labs to SpectraSynq | (K1v2 referenced in narrative) | Substitute K1v2 → K1 hardware in narrative |
| 54156 | 2026-05-23 | decision | K1v2 Upload Policy Changed: Auto-Upload After Every Patch Without Stopping | Title + entire row K1v2 — captain-policy record | Title → "K1 Hardware Upload Policy Changed..."; narrative K1v2 → K1 hardware |
| 54157 | 2026-05-23 | feature | K1v2 Serial Port Remapped to Hardware UART (Serial) Instead of USBCDC | Title K1v2 + facts SB_K1V2_HARDWARE | Title → "K1 Hardware Serial Port Remapped..."; macro → SB_K1_HARDWARE |
| 54158 | 2026-05-23 | feature | K1v2 UART Serial TX Buffer and Timeout Configured Before begin() | Title K1v2 + facts SB_K1V2_HARDWARE | Title → "K1 Hardware UART Serial TX Buffer..."; macro → SB_K1_HARDWARE |
| 54159 | 2026-05-23 | bugfix | USBSerial Alias Strategy Changed: Macro Define Removed, USBCDC Declaration Conditionally Excluded | Facts reference SB_K1V2_HARDWARE | Substitute K1v2 → K1 hardware, SB_K1V2_HARDWARE → SB_K1_HARDWARE in facts |
| 54160 | 2026-05-23 | bugfix | K1v2 FQBN CDCOnBoot Changed from cdc to default to Match Hardware UART Serial Path | Title K1v2 | Title → "K1 Hardware FQBN CDCOnBoot Changed..." |
| 54161 | 2026-05-23 | change | SB_USB_CUSTOM_DESCRIPTORS Re-Enabled on K1v2 (Set to 1) | Title K1v2 + facts SB_K1V2_HARDWARE | Title → "...Re-Enabled on K1 Hardware (Set to 1)"; macro → SB_K1_HARDWARE |
| 54162 | 2026-05-23 | change | USBCDC USBSerial Guard Removed — Declared Unconditionally on All Targets | Facts reference SB_K1V2_HARDWARE | Substitute SB_K1V2_HARDWARE → SB_K1_HARDWARE; K1v2 prose → K1 hardware |
| 54163 | 2026-05-23 | change | K1v2 Serial Path Fully Reverted to Standard USBCDC — Hardware UART Approach Abandoned | Title + facts K1v2 | Title → "K1 Hardware Serial Path Fully Reverted..." |
| 54164 | 2026-05-23 | bugfix | K1v2 USB Init Moved Before LED Init to Fix Early-Boot Serial Ordering | Title K1v2 + facts SB_K1V2_HARDWARE | Title → "K1 Hardware USB Init Moved..."; macro → SB_K1_HARDWARE |
| 54165 | 2026-05-23 | change | K1v2 FQBN Switched to USBMode=default and CDCOnBoot=default — Hardware UART Path | Title K1v2 + facts | Title → "K1 Hardware FQBN Switched..." |
| 54166 | 2026-05-23 | change | K1v2 Serial Strategy Finalised: Hardware UART Serial Alias with Buffered Init | Title K1v2 + facts SB_K1V2_HARDWARE | Title → "K1 Hardware Serial Strategy Finalised..."; macro → SB_K1_HARDWARE |
| 54167 | 2026-05-23 | change | K1v2 FQBN Reverted Back to USBMode=hwcdc and CDCOnBoot=cdc | Title K1v2 | Title → "K1 Hardware FQBN Reverted Back..." |
| 54168 | 2026-05-23 | discovery | K1v2 Boot Crash: LEDC Not Initialized + Watchdog Abort + PSRAM Read Error | Title K1v2 — load-bearing crash forensic | Title → "K1 Hardware Boot Crash: LEDC Not Initialized..."; preserve all engineering detail verbatim |
| 54169 | 2026-05-23 | bugfix | SB_HAS_SWEET_SPOT_LEDS Macro Added to Fix LEDC Guard Evaluation | Facts K1v2 prose | Substitute K1v2 → K1 hardware in narrative |
| 54170 | 2026-05-23 | change | K1v2 FQBN Reverted to USBMode=hwcdc CDCOnBoot=cdc After Hardware UART Experiment | Title K1v2 | Title → "K1 Hardware FQBN Reverted..." |
| 54171 | 2026-05-23 | bugfix | LEDC Sweet-Spot PWM Calls Fully Guarded in led_utilities.h and system.h | Facts K1v2 prose — load-bearing LEDC crash fix | Substitute K1v2 → K1 hardware in narrative |
| 54172 | 2026-05-23 | discovery | K1v2 Serial Strategy Oscillation History: USBCDC → Hardware UART → USBCDC → Inconsistent | Title K1v2 — load-bearing diagnostic | Title → "K1 Hardware Serial Strategy Oscillation History..." |
| 54219 | 2026-05-23 | discovery | K1v2 Fork Preflight Confirms: No .claude/ Directory, Two Path Typos in Brief, 10-Item Dirty State | Title K1v2 — preflight diagnostic for this lane wave | Title → "K1 Hardware Fork Preflight Confirms..." |
| 54226 | 2026-05-23 | decision | Sensory Bridge Core Firmware on K1 Hardware — Project Identity Doctrine | Title already canonical "K1 Hardware"; check narrative for residual K1v2 prose | Substitute in narrative only if present |
| 54227 | 2026-05-23 | discovery | K1 Hardware Migration — Current Proof State and Open Gaps | Title canonical; narrative may reference K1v2 | Substitute in narrative only if present |
| 54233 | 2026-05-23 | discovery | K1v2 Compile Script — Exact Flags and Docs Drift Identified | Title K1v2 + reference to `tools/compile-k1v2-arduino.sh` | Title → "K1 Hardware Compile Script..."; preserve script-path literal until physical rename ships |
| 54236 | 2026-05-23 | discovery | K1v2 Device Identity — MAC, VID:PID, and Port Enumeration Recorded | Title K1v2 + facts MAC B4:3A:45:A5:87:F8 | Title → "K1 Hardware Device Identity..." |
| 54243 | 2026-05-23 | change | "K1v2" Naming Deprecated and Ordered Annihilated Across Entire Project | Title K1v2 — Captain's purge order itself | KEEP "K1v2" in title quoted-string (this row IS the deprecation order; substituting destroys the historical referent) |
| 54245 | 2026-05-23 | decision | K1 Hardware Canonical Definition — PSRAM Always Present, ESP32-S3-DevKitC-1 N16R8 | Title canonical; narrative may reference K1v2 | Substitute in narrative only |
| 54246 | 2026-05-23 | decision | "K1v2" Naming Purge — Repository-Wide Replacement with Binding Rules | Title K1v2 — purge master record itself | KEEP "K1v2" in title quoted-string (this row IS the purge directive; quoted referent must survive) |
| 54247 | 2026-05-23 | decision | Path A vs Path B — Forward-Only Purge Recommended Over Git History Rewrite | Title clean; narrative likely references K1v2 | Substitute in narrative only |
| 54248 | 2026-05-23 | change | docs/hardware/k1-hardware-definition.md Created — Canonical K1 Hardware Spec Shipped | Title canonical; narrative may reference K1v2 | Substitute in narrative only |
| 54249 | 2026-05-23 | decision | SB_K1V2_HARDWARE → SB_K1_HARDWARE — Firmware Macro Rename Convention Established | Title K1v2 — rename convention itself | KEEP SB_K1V2_HARDWARE in title (this row IS the rename rule; macro identifier must survive verbatim) |
| 54250 | 2026-05-23 | discovery | All SB_K1V2_HARDWARE Call Sites Enumerated Across Firmware Source | Title SB_K1V2_HARDWARE — enumeration record itself | KEEP SB_K1V2_HARDWARE in title (this row IS the call-site enumeration; identifier must survive verbatim) |
| 54251 | 2026-05-23 | discovery | GPIO Block Comment References Firmware-v3 Environment Name — Ambiguity for Captain Review | Subtitle quotes "env: esp32dev_audio_esv11_k1v2" — vendor build identifier | KEEP vendor identifier verbatim (matches Lane 1 ambiguity ruling) |
| 54253 | 2026-05-23 | discovery | Lane 3 Sweep — docs/superpowers Plans Confirmed Zero K1v2 Hits | Title K1v2 — lane-3 sweep result itself | KEEP K1v2 in title (this row REPORTS on K1v2 hits and the quoted referent must survive) |
| 54256 | 2026-05-23 | discovery | docs/s3-migration-prep.md — Heavy K1v2 Reference Density Confirmed for Lane 4 | Title K1v2 — lane-4 sweep result itself | KEEP K1v2 in title (this row REPORTS on K1v2 references; quoted referent must survive) |

### Hit count by category

| Category | Count |
|----------|-------|
| Observation rows with K1v2/SB_K1V2_HARDWARE | 43 |
| Session cards (S-prefix) referenced — excluded | 20 |
| Prompt rows (P-prefix) — excluded (verbatim forensic, MUST NOT modify) | 12 |
| Rows where K1v2 referent MUST be preserved (purge orders, rename rules, sweep reports) | 6 (#54243, #54246, #54249, #54250, #54253, #54256) |

## High-Salience Observations (load-bearing engineering content)

The following observations carry engineering claims, hardware diagnostics, or workflow policy that downstream agents and future Captain reviews actively rely on. The K1v2 → K1 hardware substitution must be a pure naming change; ALL factual / narrative / files_modified payloads must remain semantically intact:

- **#54168** — K1v2 Boot Crash: LEDC + WDT + PSRAM read error. Root-cause triad documented; flagged by the brief.
- **#54169** — SB_HAS_SWEET_SPOT_LEDS macro added (LEDC guard evaluation fix).
- **#54171** — LEDC Sweet-Spot PWM Calls Fully Guarded across led_utilities.h + system.h (final fix for #54168).
- **#54172** — K1v2 Serial Strategy Oscillation History (USBCDC ↔ Hardware UART; flagged by the brief; identifies an unresolved final-state mismatch between FQBN hwcdc+cdc and source-level Serial alias).
- **#53203 / #53229–53233 / #53278** — 30-agent K1v2 VP/AP soul-excavation wave: dual-VP independence findings, Goertzel symmetric-smoothing finding, firmware-v3 canonical-path finding. These are the foundation of the entire feat/dual-vp-recovery branch.
- **#54156** — Captain's standing-order: auto-upload after every patch, no pause. Workflow policy that future sessions depend on.
- **#54148** — Three hardware-capability macros (SB_HAS_ROTATE8 / SB_USB_CUSTOM_DESCRIPTORS / SB_ENABLE_USB_MSC_UPDATE) introduced; foundation of the K1-vs-S2 divergence pattern.
- **#54101** — Perfect Dual-Channel Config Snapshot (canonical restore reference for firmware 40102 — explicit warning that primary PHOTONS/CHROMA/MOOD are encoder-only, not serial-settable).

## Rewrite Feasibility Assessment

Per the brief: "claude-mem observations are typically immutable after writing. Document whether the claude-mem MCP exposes a write/update API for observation text."

Findings:

1. The exposed claude-mem MCP surface in this environment is read-only on observation text: `search`, `timeline`, `get_observations`, `smart_search`, `smart_outline`, `smart_unfold`, `build_corpus`, `prime_corpus`, `list_corpora`, `rebuild_corpus`, `query_corpus`, plus prompt/session tools. There is no `update_observation`, `edit_observation_text`, or `rewrite_observation` tool. **The textual purge is structurally not executable through documented claude-mem MCP tooling.**

2. Three theoretical paths exist for actually mutating observation text:
   - **Path 9-A (recommended):** Do nothing to the persisted observation rows. They are historical record. The forward-looking source-of-truth substitution (Lane 1 firmware + Lane 4 docs + commit/PR text + new observations) is what governs all future agent behaviour. Old observation titles containing "K1v2" become historical-snapshot terminology, akin to a git blame that still shows the old class name.
   - **Path 9-B:** Direct SQLite mutation of the claude-mem database (likely under `~/.claude-mem/`). This is OUT-OF-POLICY without explicit Captain authorisation per the brief ("forensic evidence chain must be preserved") and per the global Founder Execution Boundary (irreversible, high-blast-radius action against a memory store shared across all SpectraSynq projects).
   - **Path 9-C:** Write follow-on "rectification" observations that explicitly reference each K1v2-tagged observation by ID and supersede the naming. This is the safest WRITE path — additive, fully reversible, leaves the original row intact for forensic chain-of-evidence, while making the corrected naming searchable. Cost: ~43 new observation rows tagged with `rectification` + `supersedes_obs=<id>`.

3. **Recommendation: Path 9-A is the default.** Path 9-C is only worth the cost if Captain or downstream agents are observed to be misled by the historical observation text (which is unlikely — observation context is timestamped and prompt-rendered with date markers, so "as-of 2026-05-22" is structurally clear).

## Ambiguities Flagged for Captain Review

1. **Historical accuracy vs naming purge.** Observations dated 2026-05-20 through 2026-05-22 captured the "K1v2" terminology that Captain itself was using verbatim at the time. Substituting the text post-hoc weakens the historical record's accuracy as a record of *what was said when*. Captain's explicit forensic-chain-preservation directive in the brief weighs heavily toward Path 9-A.

2. **Quoted-referent observations.** Six observations (#54243, #54246, #54249, #54250, #54253, #54256) exist precisely to **report on / order the elimination of** the K1v2 string. Substituting "K1v2" out of those titles destroys their semantic meaning — they become self-referential ghosts. These rows must keep "K1v2" verbatim regardless of purge approach.

3. **Vendor build identifier `esp32dev_audio_esv11_k1v2`.** This is a PlatformIO env literal from the Lightwave-Ledstrip firmware-v3 vendor tree, not a SensoryBridge-main 9 naming choice. Lane 1 ruled it remains verbatim. #54251 surfaces the same ambiguity for Captain — propagate the Lane 1 ruling.

4. **Compile-script filename `tools/compile-k1v2-arduino.sh`.** Observations #54130, #54131, #54154, #54233 reference this filename. The companion observation #54246 (purge directive) records `tools/compile-k1-arduino.sh` as the renamed target. Until the physical script rename ships in-repo, observation text referencing the old filename is correct — it accurately names the file that existed at the time. After the rename ships, the historical reference is still correct as historical fact. No substitution proposed for these script-path literals.

5. **Macro identifier `SB_K1V2_HARDWARE` inside facts/narrative payloads.** Lane 1 ruled the in-source identifier becomes `SB_K1_HARDWARE`. Observation facts/narratives that quote the old identifier remain correct as historical fact (the macro WAS named SB_K1V2_HARDWARE at the time the observation was written). If Path 9-A is chosen, no substitution. If Path 9-C is chosen, rectification observations should specifically call out the macro rename per #54249.

6. **Session cards and prompt rows.** Session-card S-prefix rows (e.g., S7424, S7425, S7427, S7429–S7442, S7470, S7472, S7479, S7489, S7492, S7496, S7497, S7502, S7503, S7560) are summarisations of session intent — they are not in the observation table proper. Prompt rows P-prefix (e.g., P57300, P57334, P57367, P57458, P57629–P57742, P57922, P57955) are Captain's own verbatim utterances. **Per the brief and the Founder Execution Boundary, prompt rows MUST NOT be modified under any circumstance.** Session cards should likewise remain untouched (they capture in-session intent at the time of the session).

## Notes

- claude-mem observations function as forensic evidence. Captain's explicit instruction in the brief — "do not delete observations (preserves forensic evidence chain)" — combined with the absence of a public write API in claude-mem MCP, makes Path 9-A (no observation mutation) the only path that is simultaneously low-risk, in-policy, and structurally executable today.
- The Lane 9 mechanical outcome is: enumerate (done), propose (this document), and let the active-repo purge (Lanes 1, 2, 4, 5, 6, plus the master findings/k1v2-purge-master.md governance) be the authoritative naming change going forward.
- If Captain later authorises Path 9-C (rectification observations), the ID list above is the working set. The 6 quoted-referent IDs (#54243, #54246, #54249, #54250, #54253, #54256) must be excluded from rectification — they are the purge directive itself.
- This document was written read-only against the claude-mem store. No observation rows were created, modified, or deleted in producing it.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:lane-9-subagent | Created — Lane 9 read-only enumeration of 43 K1v2-tagged observation rows in project `SensoryBridge-main 9`. Documented absence of claude-mem observation-text write API. Recommended Path 9-A (no mutation; forward-only purge via active-repo lanes governs). Flagged 6 quoted-referent rows that MUST keep K1v2 verbatim. Flagged 1 vendor build identifier and 1 compile-script filename literal for preservation. Confirmed prompt rows and session cards remain out-of-scope per Founder Execution Boundary. |
