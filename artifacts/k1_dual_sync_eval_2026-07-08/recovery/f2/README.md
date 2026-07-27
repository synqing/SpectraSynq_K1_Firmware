# F2 evidence contract

F2 is a silicon-isolation battery, not Gate-0. A run uses one immutable
`<run-id>` in both:

- raw evidence: `_scratch/dual_sync_f2_abc_<run-id>/`
- tracked evidence:
  `artifacts/k1_dual_sync_eval_2026-07-08/recovery/f2/<run-id>/`

The guarded uploader supports Cases A and B only. Case C must reuse the exact
Case-B upload manifest and preserved images.

## Required order

1. Captain confirms the physical attestation for the case.
2. Run `run_f2_flash.sh` for A or B.
3. Run `run_f2_abc.sh` for the same case.
4. Do not start B until tracked Case A recursively revalidates as PASS.
5. Do not start C until tracked Cases A and B recursively revalidate as PASS.
6. Case C produces `CAPTAIN_STOP.md` only if its software evidence passes.
   The file remains `decision: PENDING`; it never authorises F3.

Use the explicit ports reported for the matching USB serials:

| Role | Chip | USB serial |
|---|---|---|
| Leader | `F887A500` | `B4:3A:45:A5:87:F8` |
| Follower | `B489A500` | `B4:3A:45:A5:89:B4` |

## Attestation files

Create these only from Captain-confirmed physical state. The controller rejects
files outside `<run-id>/attestations/`, symlinks and field drift.

Case A:

```json
{
  "schema_version": 1,
  "case": "A",
  "confirmed_by": "Captain",
  "gpio_wiring_confirmed": true,
  "common_ground_confirmed": true,
  "logic_voltage": "3V3",
  "k718_state": "irrelevant"
}
```

Case B is identical except `"case": "B"` and `"k718_state": "off"`.

Case C:

```json
{
  "schema_version": 1,
  "case": "C",
  "confirmed_by": "Captain",
  "gpio_wiring_confirmed": true,
  "common_ground_confirmed": true,
  "logic_voltage": "3V3",
  "k718_state": "on",
  "dial_detents_committed": 3,
  "mode_feedback_acceptance": "PENDING"
}
```

During Case C, Captain turns at least three mode detents while the 60-second
capture is active. Software must prove sustained dial link, drained
notify/decode/enqueue/apply counts, stable connection generation and a causal
mode-apply-to-confirmation-write pair. K1's write-without-response does not
prove the K718 displayed the confirmation; Captain resolves that observation
only at the STOP.

## Commands

Set `RUN_ID`, `LEADER_PORT`, `FOLLOWER_PORT` and `FIRMWARE_SHA` explicitly.
Never infer device role from a port number.

Guard-build and flash Case A:

```bash
bash scripts/dual_sync_probe/run_f2_flash.sh \
  --case A \
  --run-id "$RUN_ID" \
  --firmware-sha "$FIRMWARE_SHA" \
  --attestation \
    "artifacts/k1_dual_sync_eval_2026-07-08/recovery/f2/$RUN_ID/attestations/case_A.json" \
  --leader-port "$LEADER_PORT" \
  --follower-port "$FOLLOWER_PORT"
```

Capture Case A:

```bash
bash scripts/dual_sync_probe/run_f2_abc.sh \
  --case A \
  --physical-state sync-only \
  --out-root "_scratch/dual_sync_f2_abc_$RUN_ID" \
  --run-id "$RUN_ID" \
  --leader-port "$LEADER_PORT" \
  --follower-port "$FOLLOWER_PORT" \
  --firmware-sha "$FIRMWARE_SHA" \
  --flash-manifest \
    "artifacts/k1_dual_sync_eval_2026-07-08/recovery/f2/$RUN_ID/uploads/flash_A.json" \
  --attestation \
    "artifacts/k1_dual_sync_eval_2026-07-08/recovery/f2/$RUN_ID/attestations/case_A.json"
```

For B use `--case B`, `--physical-state dial-off`, `flash_B.json` and
`case_B.json`. For C use `--case C`, `--physical-state dial-on`,
the unchanged `flash_B.json` and `case_C.json`; there is no Case-C flash
command.
