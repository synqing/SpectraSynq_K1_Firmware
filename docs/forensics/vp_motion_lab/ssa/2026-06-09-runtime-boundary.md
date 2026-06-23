# VPML Runtime Boundary SSA - 2026-06-09

## Verdict

**Boundary classification:** `CURRENT_FAILURE_NOT_VERIFIED`; the strongest classified failure in the checked artefacts is **firmware command availability for the specific `20260609T212727` runtime image**, not baud/CDC transport, runner capture logic, or VPAB frame emission.

**Operational read:** do not send the next slice straight into VPAB frame emission or baud/CDC. The failed `212727` log shows the device was reachable and identified as `F887A500`, but the loaded command surface rejected `vpml` and `vpab` commands. The stated direct 115200 probe and later byte-clean capture then refute a persistent command-surface failure; if a new failure remains after that probe, the next likely host-side boundary is runner invocation/state, not firmware rendering.

## Evidence Table

| Boundary | Evidence | Refutation attempt | Classification |
|---|---|---|---|
| Firmware command availability | `20260609T212727-vpml-intro-bounce-loop-1401.raw.log:30-41` identifies chip `F887A500`, then `:vpml=status` returns `Bad command`; `:vpml=play_builtin,intro_bounce_loop` also returns `Bad command` at `:51-59`. Source shows VPML commands exist only behind `ENABLE_VP_MOTION_LAB`: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:3112-3118`, `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:172-190`. | Direct probe evidence says at 115200 `:chip_id` returned `F887A500`, `:vpml=status` returned inactive status, `play_builtin intro_bounce_loop` returned `active=1`, and status returned `active=1 programme=intro_bounce_loop`. Later `20260609T213624...raw.log:29-33` also shows play/status success. | Historical `212727` failure boundary: **yes**. Current/persistent firmware-command failure: **refuted**. |
| Baud / CDC transport | `212727` got a valid chip identity before command rejection; `20260609T213624...raw.log:1,13-18` identifies the same chip over CDC, and the prompt's direct probe succeeded at 115200. | If baud/CDC were the boundary, chip identity and readable `Bad command` responses would not be reliable. Later 230400 and stated 115200 command exchanges both work. | **Refuted** as highest-confidence boundary. |
| Runner capture logic | `scripts/regression-harness/vpml_run_console.py:243-278` now requires VPML status/play responses and K1DF begin/end before success; `:149-162` turns `Bad command` into an error; `tests/test_vpml_run_console.py:156-184` asserts bad-command transcripts are preserved. | The failed `212727` transcript contains real device `Bad command` responses, not a parser-only failure. The later `213624` artefact proves a capture path can write clean raw/frame/summary files. | Not the checked failure boundary. **Residual suspect only for any new post-probe runner-only failure.** |
| VPAB frame emission | Accepted captures prove emission: `20260609T193511...vpml-summary.json` has `strict_transport_clean=true`, primary/secondary present, mode 250, and `captured=30 dropped=0 overflowed=0`; `20260609T213624...vpml-summary.json` has `captured=32 dropped=0 overflowed=0`. Raw `213624` shows `VPAB_RECORDS: captured=32 dropped=0 ... overflowed=0` and `K1DF_BEGIN` at lines `76-99`. | Failed `193419` had frames but was rejected for `dropped=28 overflowed=1`, proving the gate can reject bad VPAB transport rather than over-accept survivor rows. | **Refuted** for current live-capture failure. |

## Remaining Unknowns

- The direct 115200 probe is prompt-stated evidence, not an on-disk raw artefact read by this SSA.
- The exact flash/image transition between the `212727` bad-command state and the later command-success state is not in the scoped logs.
- Direct 115200 probe did not include a full VPAB start/frames drain; VPAB emission is instead proven by the 230400 clean captures.
- Byte-clean VPML capture is not aesthetic proof; Captain eyes-on visual acceptance remains open.
- `latest-vpml-evidence-page.json` is stale relative to the later `213624` clean capture in the runtime-evidence directory; refreshing it is host-only but out of this SSA write scope.

## Re-run Command

None required for this SSA. Optional host-only follow-up for orchestrator: refresh the VPML evidence page so the `213624` clean capture appears in the latest page model.
