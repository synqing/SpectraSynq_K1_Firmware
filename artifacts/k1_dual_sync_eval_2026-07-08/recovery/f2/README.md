# F2 provenance-split hardware execution

F2 is a silicon-isolation battery, not Gate-0. The only authorised order is:

```text
ports_pre_A → flash A → capture A → flash B → capture B
            → capture C1 → controlled reset → capture C2 → Captain STOP
```

F3 is not authorised.

## Present gate

```text
FIRMWARE_SOURCE_SHA=a58203183208a4db7fcc7a30d060e6db14673ab1
IMAGE_SET_STATUS=BLOCKED
F2_HARDWARE_EXECUTION=NO_GO
F3_AUTHORISED=false
```

The tracked image-set ledger is
[`image-set-a582031.json`](image-set-a582031.json). The reviewed dual-role
leader and follower images are preserved and match. The reviewed sync-only
leader image is missing. Three bounded reproductions failed to match its
reviewed BIN and ELF identities. No controller may write hardware until the
original reviewed artefact is recovered or Captain separately authorises a new
complete frozen image set.

## Identity model

These identities are distinct and must never be inferred from one another:

```bash
HOST_EXECUTION_SHA="$(git rev-parse HEAD)"
FIRMWARE_SOURCE_SHA="a58203183208a4db7fcc7a30d060e6db14673ab1"
```

- `HOST_EXECUTION_SHA` identifies the committed controller, tests and
  authority documents.
- `FIRMWARE_SOURCE_SHA` identifies the reviewed firmware on both K1s.
- Device `:build` must report `a582031…`.
- Device `:image_id` must equal the reviewed application/ELF SHA-256.
- Device `:runtime_id` supplies a per-boot nonce.
- Ports are observations. USB serial and chip ID are identity.

Every controller requires:

```text
--host-execution-sha
--firmware-source-sha
--image-set-manifest
--ports-manifest
--run-root
```

The host SHA must equal the clean committed HEAD. It remains constant for the
whole run. The firmware SHA must equal the ready image-set manifest and may
not be replaced by host HEAD.

After the image ledger becomes READY, create the run without manual ports:

```bash
HOST_EXECUTION_SHA="$(git rev-parse HEAD)"
FIRMWARE_SOURCE_SHA="a58203183208a4db7fcc7a30d060e6db14673ab1"
RUN_ID="<UTC_RUN_ID>"
RUN_ROOT="_scratch/dual_sync_f2_abc_${RUN_ID}"
IMAGE_SET="artifacts/k1_dual_sync_eval_2026-07-08/recovery/f2/image-set-a582031.json"

bash scripts/dual_sync_probe/run_f2_create.sh \
  --host-execution-sha "$HOST_EXECUTION_SHA" \
  --firmware-source-sha "$FIRMWARE_SOURCE_SHA" \
  --image-set-manifest "$IMAGE_SET" \
  --run-root "$RUN_ROOT"
```

Subsequent commands consume the generated prior port manifest directly. The
entry points are `run_f2_flash.sh`, `run_f2_abc.sh`,
`run_f2_reboot.sh` and `run_f2_finalise.sh`; their `--help` output is the
executable interface contract.

## Run roots

One immutable run ID has:

```text
_scratch/dual_sync_f2_abc_<run-id>/
artifacts/k1_dual_sync_eval_2026-07-08/recovery/f2/<run-id>/
```

Controllers refuse overwrite, symlink escape, ambiguous USB identities,
manifest-chain drift and changed prior evidence.

## Port chain

The resolver binds by USB serial and then proves chip identity:

| Role | Chip | USB serial |
|---|---|---|
| Leader | `F887A500` | `B4:3A:45:A5:87:F8` |
| Follower | `B489A500` | `B4:3A:45:A5:89:B4` |

It writes:

```text
runtime/ports_pre_A.json
runtime/ports_A.json
runtime/ports_B.json
runtime/ports_C1.json
runtime/ports_C2.json
```

Each file records host SHA, firmware SHA, creation time, both USB/chip/port
bindings and the prior manifest SHA-256. Manual port-variable substitution is
forbidden.

## Exact-image writer

`run_f2_flash.sh` supports A and B only. It:

1. validates the complete READY image set;
2. consumes the prior port manifest;
3. runs the positive target guard and a negative cross-target control;
4. reads back and hashes the partition table on every target;
5. verifies BIN and ELF hashes immediately before writing;
6. invokes pinned `tool-esptoolpy@4.8.9` directly;
7. writes only the application BIN at `0x10000`;
8. never builds, erases, or writes the bootloader, partition table or NVS;
9. rebinds by USB serial without consuming the boot stream;
10. captures the post-write startup path, including leader advertising,
    follower scan/UUID discovery and a fresh two-role link snapshot;
11. reads chip/build/image/runtime identity and proves the expected new nonce;
12. writes the next immutable port manifest.

Case B writes only the leader. Its follower image and boot nonce must continue
from Case A.

## Attestations and feedback

C1 and C2 use distinct non-overwriting files:

```text
attestations/case_C1_pre.json
attestations/case_C2_pre.json
feedback/case_C1_feedback.json
feedback/case_C2_feedback.json
```

C1 pre-attestation:

```json
{
  "schema_version": 1,
  "kind": "f2_pre_attestation",
  "case": "C1",
  "scenario": "late_join",
  "captain": "Captain",
  "created_at_utc": "2026-07-28T00:00:00Z",
  "gpio_wiring_confirmed": true,
  "common_ground_confirmed": true,
  "logic_voltage": "3V3",
  "k718_state": "off",
  "four_detent_commitment": true
}
```

C2 uses `"scenario": "controlled_cold_coexistence"`,
`"k718_state": "powered_and_advertising"` and
`"controlled_reboot_authorised": true`.

Post-run feedback:

```json
{
  "schema_version": 1,
  "kind": "f2_post_run_feedback",
  "case": "C1",
  "captain": "Captain",
  "created_at_utc": "2026-07-28T00:02:00Z",
  "pre_attestation_sha256": "<sha256>",
  "k1_mode_changed": true,
  "k718_confirmation_displayed": true,
  "status": "PASS"
}
```

Allowed status is `PASS`, `FAIL` or `UNMEASURED`. PASS requires both physical
observations true. UNMEASURED requires both values null. A missing observation
cannot become PASS.

## Ordered cases

### A — SyncLink-only baseline

Flash follower `k1_sync_probe_bench`, then leader
`k1_sync_probe_main_sync_only`. Require exact identities, checked advertising,
scan/discovery/connect, Link Ready PASS, at least 300 TX/RX/apply, ten clocks
per role, follower clock-estimate evidence, ten GPIO rounds, negotiated BLE
evidence and no reset/reconnect loop.

Non-PASS A closes the run.

### B — Dual-role leader, K718 off

Recursively revalidate A. Require the follower application and boot nonce
unchanged. Flash only the leader with `k1_sync_probe_main`, keep K718 off and
require Link Ready PASS plus active stable Remoted scanning with no dial
traffic.

Non-PASS B closes the run.

### C1 — K718 late join

Use the continuing Case-B boots with no flash or reset. Start with K718 off,
establish the Case-B SyncLink session, then power/link K718. Require Link Ready
PASS, sustained dial link, no reconnect/reset loop and four distinct causal
mode changes. Create feedback only after capture.

C1 alone proves only that K718 can join an established SyncLink session.

### C2 — Cold coexistence

Keep K718 powered and advertising. The controlled reboot controller consumes
C1 evidence, the Case-B flash manifest and C2 pre-attestation. It opens both
serial streams, sends typed `:reset`, records both `SBOK` acknowledgements,
rebinds automatically and requires unchanged application/source/environment
identity plus a new boot nonce on both devices. It writes
`runtime/reboot_C2.json` and `runtime/ports_C2.json`.

Before any post-reset identity query can consume boot diagnostics, the
controller captures both startup streams and requires leader advertising,
follower scan start, UUID discovery and fresh linked snapshots from both
roles. The subsequent minimum-60-second case capture requires Link Ready PASS,
Remoted, sustained dial link and another four causal detents. Only C2 can
support the broad cold-start coexistence claim.

## Status and STOP

The finaliser keeps these results separate:

```text
case_A_software_status=PASS|FAIL|BLOCKED
case_B_software_status=PASS|FAIL|BLOCKED
case_C1_software_status=PASS|FAIL|BLOCKED
case_C2_software_status=PASS|FAIL|BLOCKED
case_C1_physical_feedback=PASS|FAIL|UNMEASURED
case_C2_physical_feedback=PASS|FAIL|UNMEASURED
f2_evidence_collection=COMPLETE|INCOMPLETE
f2_acceptance=PASS|REJECTED|PENDING
f3_authorised=false
```

It recursively inventories raw and tracked evidence, revalidates the final
port chain, writes immutable `F2_STATUS.json`, `CAPTAIN_STOP.md` and
`CAPTAIN_STOP.sha256`, and never edits them later. Captain’s later decision is
a separate non-overwriting `CAPTAIN_DECISION.json`.

## Stop conditions

Stop immediately on an incomplete image set, changed host HEAD, dirty tracked
controller input, app/partition/source mismatch, USB/chip ambiguity, manual
port substitution, unexpected A→B follower reset, any B→C1 reset, asymmetric
C2 reboot, evidence mutation, normal PlatformIO upload, erase, cross-flash,
`start_noise_cal`, ESP-NOW, M2, Gate-0 or any F3 work.
