# Colour Lab — Web Serial control instrument

`tools/colourlab/index.html` is the desktop-first K1 Colour Lab Workbench for
the `K1_COLOUR_LAB_V1` serial surface. It has no build step, framework,
backend or wireless path. The production surface loads three distinct
authorities:

- `colourlab-core.js` — wire protocol, queue, state, exact K1 Paint/LUT model;
- `colourlab-authoring.js` — tested RGB, shortest-arc HSV and OKLCH authoring,
  rich-draft compilation and output policy;
- `colourlab-workbench.js` — local-first interaction and Web Serial wiring.

The Workbench layout was cleared by the 2026-08-28 T0 optical gate before
production writes. The exact 43-role evidence pack and independent PASS are in
`_scratch/colourlab_workbench_r0_20260828/OPTICAL_GATE_RECEIPT.md`.

The screen preview is an **exact Colour Lab code-path preview through the
source-modelled stages**. It is not a physical or colorimetric match, and
it is not a claim about the whole firmware pipeline.

The permanent SpectraSynq product rule is fail-closed: no full hue wheel,
rainbow, spectrum sweep or wheel-spanning palette is selectable, rendered,
sent, saved or exported. Legacy `PAINT: mode=ramp` replies are recognised only
to trigger priority `paint=off`; they are never reproduced by this surface.

---

## 1. Firmware/UI contract (frozen from source)

Every claim below carries a file reference. The UI must not invent
commands, clamps, or replies this contract does not describe.

### 1.1 Wire framing

- A `:` byte enters command mode; subsequent bytes up to newline form the
  command (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp` around the `:`
  latch).
- Commands are `name=data` or bare `name`. The client writes
  `:{command}\n` or `:{command}={data}\n` at **115200 baud**.
- **The wire is the envelope, not a bare `PAINT:` line.** Success replies
  are wrapped by `tx_begin` / `tx_end`
  (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_tx.cpp:27-40`):

```
sbr{{
<payload>
}}
```

- Errors go through `bad_command` (`serial_tx.cpp:47-58`):

```
sberr[[
Bad command: <type>
]]
```

or, when `command_data` is non-empty:

```
sberr[[
Bad command: <type>=<data>
]]
```

- Colour Lab success printers call `tx_begin()` then the payload then
  `tx_end()` (`k1_colour_lab.cpp:113-130`, `:134-152`, `:397-399`).
- A failed `tune_save` prints **an error envelope first**, then a
  **success envelope** containing `TUNE_SAVE: fail`
  (`k1_colour_lab.cpp:389-395`).
- A failed `tune_gain` / `tune_gamma` / `tune_reset` prints only
  `bad_command` — **no `TUNE:` line follows**.
- On a bench build without `K1_LOOK_LIB_V1`, `tune_gain` / `tune_gamma` /
  `tune_reset` / `tune_save` are `bad_command` (`k1_colour_lab.cpp:403-407`).
  **`tune_status` is outside that gate** and still prints `TUNE:` with
  `type=na`. Hide Tune *mutations* when the device profile says
  `slot15_supported: false`. Hydration may still read `tune_status`.
  That reply is still not LUT knowledge.

The parser must accept framed and (for chatter robustness) unframed
payload lines. Envelope markers are framing, not Colour Lab events.

### 1.2 Reply payloads (inside the envelope)

Printed by `k1_colour_lab_print_paint` / `k1_colour_lab_print_tune`
(`k1_colour_lab.cpp:101-153`):

```
PAINT: mode=<off|solid|ramp|stops|card> target=<primary|secondary|both> rgb=R,G,B s=S.SSS v=V.VVV stops=N
TUNE: gain=R.RRR,G.GGG,B.BBB gamma=G.GGG slot=15 type=<N|na>
TUNE_SAVE: ok
TUNE_SAVE: fail
```

- `mode` and `target` are **words**, not enum numbers.
- Floats print with 3 decimal places (Arduino `print(x, 3)`).
- `type` is the current slot-15 look-table type as an unsigned integer
  when `K1_LOOK_LIB_V1` is compiled in (`2` = `K1_LOOK_RGB_1D_256`), else
  the literal `na`.

Profiling replies (not Colour Lab dispatch):

```
<8 hex chip id>          (:chip_id → print_chip_id, utilities.h:25-38, wrapped)
BUILD: version=… git=… epoch=… env=…     (:build, serial_menu.cpp:2243-2266)
LOOK: slot=N type=NAME sec=inherit|N env=<env>   (:look_status, serial_typed_dispatch.cpp:1063-1081)
```

- `:chip_id` prints **eight uppercase hex digits only** inside the
  envelope — no `CHIP ID:` prefix (`cmd_chip_id` at
  `serial_menu.cpp:2497-2500`). `dump_info` adds the prefix; this
  instrument does not use `dump_info`.
- `LOOK: env=` is **hardcoded from the compile flag**
  (`K1_LOOK_LIB_WS2812_V1` → `k1_bench_im69d_led150`, else
  `k1_main_rpl_im69d`). It is not `K1_BUILD_ENV`.

### 1.3 Command matrix

All Colour Lab parsing is `k1_colour_lab_dispatch`
(`k1_colour_lab.cpp:251-411`). All 11 names are on the serial
`manual_commands` allowlist. None are on the wireless allowlist.

| # | Command | Data / clamp | Effect | Reply |
|---|---------|--------------|--------|-------|
| 1 | `paint` | Firmware accepts `off\|solid\|ramp\|stops\|card`; the product Workbench permits `off\|solid\|stops\|card` only and treats a reported `ramp` as a recovery condition | Sets paint mode | `PAINT:` |
| 2 | `paint_target` | `primary\|secondary\|both` | Sets target mask | `PAINT:` |
| 3 | `paint_rgb` | `R,G,B`, each 0–255 integer, strict `%d,%d,%d` **no trailing characters** | Solid-mode colour only | `PAINT:` |
| 4 | `paint_sv` | Firmware protocol fact only; the product Workbench never emits it because geometric hue-wheel Ramp is prohibited | Ramp-mode S/V only | `PAINT:` |
| 5 | `paint_stops` | 1–8 `R,G,B` triples joined by `;`; **`strlen(data) < 159`** (`parse_stops` rejects `>= 159`, `k1_colour_lab.cpp:186-195`); n==1 also copies stop 0 into `rgb` | Sets stops table | `PAINT:` |
| 6 | `paint_status` | bare | none (read) | `PAINT:` |
| 7 | `tune_gain` | `R,G,B` floats, each finite 0.0–2.0 | Live slot-15 LUT regen | `TUNE:` |
| 8 | `tune_gamma` | one float, finite 0.20–4.00 | Live LUT regen | `TUNE:` |
| 9 | `tune_reset` | bare | Identity live. **Does not persist. Does not restore last-saved.** | `TUNE:` |
| 10 | `tune_save` | bare | Persist slot-15 LUT | `TUNE_SAVE: ok/fail` |
| 11 | `tune_status` | bare | none (read). **Does not make the effective LUT known.** | `TUNE:` |

Profiling commands the instrument also emits:

| Command | Reply family |
|---------|--------------|
| `chip_id` | 8 hex |
| `build` | `BUILD:` |
| `look_status` | `LOOK:` |

Numeric-parse notes:

- `parse_u8_triple` / `parse_sv` / gain / gamma use a trailing `%c`
  sentinel: **any trailing character (including whitespace) rejects**.
- Worst-case 8 stops of `255,255,255` = 95 characters — always legal.

### 1.4 Paint semantics

From `k1_colour_lab_pixel` (`k1_colour_lab.h:147-202`):

- **`r,g,b` is used only by Solid. `s,v` is used only by Ramp.** They are
  independent fields. No combined HSV picker.
- **Solid:** every pixel = `rgb/255`.
- **Ramp:** pixel `i` of `n` = geometric HSV of `h = i/n` (h=0 when n≤1).
- **Stops:** uniformly distributed. `t = i/(n-1)` across `stop_n-1`
  segments. No positionable stops.
- **Card:** `region = (i*17)/n`; regions 0–12 = greys
  `{0,1,16,32,64,96,128,160,192,224,240,254,255}`, 13 = red, 14 = green,
  15 = blue, 16 = gold `(255,140,0)`.
- **Off:** the paint lane writes nothing; the normal lightshow shows
  through.

Boot defaults (`k1_colour_lab.h:63-72`): mode=off, target=both,
rgb=(140,140,140), s=1.0, v=0.55, stops empty.

### 1.5 Render pipeline and Both-target scale

- Paint applies after brightness / `scale_to_strip` on the targeted
  channel(s).
- When target is **both** and `K1_WS2816_LEVER2_V1` is compiled, each
  float channel is multiplied by `K1_COLOUR_LAB_BOTH_SCALE = 0.30` after
  pixel math and before the SQ15x16 write (`k1_colour_lab.cpp:80-86`).
  **Show this scale only when the device profile enables it.** Bench
  led150 does not compile Lever-2 — do not show Both-scale there.
- Lever-2 emit: float → `SQ15x16` (trunc toward zero at 1/65536) →
  `u16 = (raw*65535) >> 16` (`k1_lever2_emit.h`).
- The LUT shapes output only when **slot 15 is the active look** for that
  channel. Application is `k1_look_lerp_1d` (`k1_look.h:165-192`):
  input 0 → 0, ≥65535 → 65535; otherwise binary search on `x[i]=i*257`
  and half-up interpolate.

Host curve authority is **Python f64** (`tests/colour_lab.py`), not C
`float`:

```
x[i] = i * 257
identity (gain==1 && gamma==1): y[i] = i * 257
else: y[0] = 0
      y[i] = sat_u16(gain * 65535 * (i/255)^(1/gamma))
sat_u16: y<=0 → 0; y>=65535 → 65535; else floor(y + 0.5)
```

### 1.6 Effective-LUT knowledge (not the hydrated TUNE: line)

`s_tune` boots identity and is **never recovered from the saved LUT
file**. After reboot, `tune_status` reports `gain=1,1,1 gamma=1.000`
even if slot 15 holds a saved non-identity curve.

Therefore:

| Fact | Meaning |
|------|---------|
| Hydrated `TUNE:` | Reported RAM tune fields. **Not** LUT knowledge. **Not** a session baseline. |
| `slot15Content: unknown` | Default at connect and after reconnect. |
| `slot15Content: known-this-session` | Set only after a successful `tune_gain` / `tune_gamma` / `tune_reset` this session. |
| `sessionBaseline` | First known-this-session values. Absent until then. |
| Persistence `saved` | Saved **this session** only. |
| Revert Session | Unavailable until a known baseline exists. Until then the action is **Set Identity**. |

While slot-15 content **or** the relevant active look is unknown, the
preview label is:

> Pre-LUT stimulus preview — effective hardware correction unknown.

Views, once knowledge exists:

- **Device Effective** — slot 15 is the active look on that channel and
  slot-15 content is known-this-session.
- **Simulate Known Session Tune** — local model of the known session
  curve. Not a pre/post toggle that pretends to know unread hardware.

### 1.7 Device capability profiles (source-frozen)

Profiling (`:chip_id`, `:build`, `:look_status`) runs **before** Ready.
LED counts come from this table, never a hard-coded 160.

| Env (`LOOK: env=` / chip) | LEDs | Both-scale | Slot 15 / Tune | Look backend |
|---------------------------|------|------------|----------------|--------------|
| `k1_main_rpl_im69d` (`9087A500`) | 160 / 160 | yes, ×0.30 (`K1_WS2816_LEVER2_V1`) | yes (`K1_LOOK_LIB_V1`) | WS2816 u16 |
| `k1_bench_im69d_led150` (`B489A500`) | 150 / 150 | **no** | **no** — hide Tune | WS2812 u8 (slots 0–7; not modelled as Colour Lab slot 15) |

Unknown chip / env → **Unverified Device Profile**: controls may work;
**no exact-parity claim**.

Registry: `docs/hardware/device-build-registry.md`. Re-check live
identities before device verify. Silicon notes in `.claude/handoff.md`
may be stale.

### 1.8 Not modelled

Brightness / `scale_to_strip` parameters, WS2812 8-bit looks, compiled
looks other than a known session slot-15 RGB_1D_256, and any packer
stage whose live parameters this UI cannot read.

### 1.9 Concurrency / Stop Output

- Serial publishes into a double buffer; Core 1 latches once per frame.
  A `PAINT:` payload confirms accept + publish.
- One in-flight command. Gain / gamma / S/V may supersede **unsent**
  queued items.
- **Stop Output** (`:paint=off`) and Disconnect's `paint=off` are the
  only priority class: discard queued mutations, jump the queue, short
  safety timeout (~800 ms), re-query `paint_status` on confirm, surface
  **output state unknown** on timeout.
- **Disconnect is not Stop Output.** Paint-active Disconnect must wait
  for a **this-turn** `PAINT: mode=off` accept (or the safety timeout /
  write failure) **before** cancelling the reader, releasing the writer,
  or closing the port. Acceptable outcomes: confirmed Paint Off then
  close; or timeout/failure, close while reporting device output unknown.
  A previously confirmed `paint=off` is **not** a safe-shutdown claim.
- `beforeunload` warns if paint is confirmed active.
- **Save / reboot leave-state.** A verification Save can permanently
  alter slot 15. The hardware receipt must record pre-test persisted
  state only to the extent it is knowable (`tune_status` / boot `TUNE:`
  is not LUT knowledge), the exact curve saved in the test, the reboot
  result, and the state intentionally left. Do not write "restored"
  unless a known-this-session snapshot was actually rewritten. Hardware
  PASS must not leave a verification curve on either product unit.

---

## 2. Using the instrument

1. From `tools/colourlab`, run `python3 -m http.server 8767 --bind 127.0.0.1`,
   then open `http://127.0.0.1:8767/index.html` in Chrome or Edge.
2. **Connect** → pick the K1 USB CDC port. Profiling
   (`chip_id` / `build` / `look_status`) then hydration
   (`paint_status` / `tune_status`) run before controls enable.
   `tune_status` does **not** unlock Revert Session or Device Effective.
3. Source: choose an authorised product source or bounded diagnostic, target
   and values locally. **Test on device** sends one ordered source command sequence;
   controls never write merely because they changed.
4. Tune: edit gain and gamma as one local draft. **Apply tune** sends gain then
   gamma and clears the submitted draft only after both are confirmed. Edits made
   during the sequence remain drafted. **Save slot 15** is
   separate persistence.
5. Preview: compare Primary and Secondary as two permanent, independently
   resolved rows. **LED values** and the **Diffusion model** draw the same
   cached frames; one persistent LED selector reads both rows through the
   exact frame inspector. Output equality and Preview-basis equality remain
   separate facts. Preview is read-only: Test belongs to Source and Apply/Save
   belong to Tune.
6. Workbench: edit a rich positional palette, compare real RGB/OKLCH/HSV paths,
   and compile visibly to at most eight uniformly distributed RGB Paint stops.
   Device Safety and Product Colour Policy are independent gates.
7. **Stop Output** is always visible and uses the priority path.
8. Session disclosure: implementation boundary and TX/RX evidence.

State discipline: draft drives local preview; confirmed values change
only on a matching reply; a timeout never promotes a draft; reconnect
resets LUT knowledge and re-profiles.

---

## 3. Files

```
tools/colourlab/index.html                    production Workbench entry point
tools/colourlab/workbench.html                byte-identical greenfield parity twin
tools/colourlab/colourlab-core.js             shipped parse/serialise/paint/LUT/state
tools/colourlab/colourlab-authoring.js        authoring maths, compiler and two policy gates
tools/colourlab/colourlab-workbench.js        local-first UI and Web Serial command sequences
tools/colourlab/README.md                     this contract
tools/colourlab/VERIFICATION.md               stamps: identity vs hardware PASS
tools/colourlab/screenshots/workbench-r1.1/   thirteen browser/a11y/state stills, not device proof
tools/colourlab/verify_workbench.py           safe headless browser/state gate
tests/colourlab_node.py                       spawn node, require core, JSON in/out
tests/test_colourlab_static.py                allowlist / clamp / static gates
tests/test_colourlab_protocol.py              executes shipped parser on fixtures
tests/test_colourlab_preview_parity.py        Python expected vs Node core
tests/test_colourlab_state.py                 knowledge / queue / profile transitions
tests/test_colourlab_authoring.py             colour maths, compiler and policy gates
tests/test_colourlab_workbench_static.py      greenfield wiring/no-rainbow/a11y contract
tests/generate_colourlab_fixtures.py          regenerate render vectors
tests/fixtures/colourlab_replies.json         serial reply cases
tests/fixtures/colourlab_render_vectors.json  golden renders
```

Tests must **execute** `colourlab-core.js` via Node. A Python replica of
the shipped JS is not a gate.

Fixtures now include framed `sbr{{` / `sberr[[` cases (inner-payload cases
remain for chatter robustness) and render suites at **n=160 and n=150**.
`tests/generate_colourlab_fixtures.py --n 160` / `--n 150` emit one suite
or both (default both).

---

## 4. Ship path

Already on disk: the production-routed greenfield Workbench, exact K1 core model,
tested authoring maths, local-first command-sequence wiring, separate safety/policy
gates, 90 passing Colour Lab tests, and a clean thirteen-still browser/a11y/responsive
and adversarial evidence run.

Remaining:

1. **Agent** — freeze the exact browser slice through the real pre-commit gate,
   commit it on `lane/colourlab-bench`, and push that branch. Do not merge it.
2. **Agent** — establish `9087A500` and `B489A500`
   (`DEVICE_IDENTITY_VERIFIED`), then run the load-bearing programme
   in `VERIFICATION.md` on both units. `:rtrace_dump` only after the
   running build proves the command. No flash is authorised by this programme.
3. **Agent** — write `COLOUR_LAB_WEB_UI_HARDWARE_PASS` only when that
   programme passes, commit and push the resulting evidence, then request the
   merge to `main`. Identity-in-the-file is not enough.

The lane closes on `COLOUR_LAB_WEB_UI_HARDWARE_PASS`. A branch commit is not
that stamp, and the branch must not merge to `main` before it is earned.
