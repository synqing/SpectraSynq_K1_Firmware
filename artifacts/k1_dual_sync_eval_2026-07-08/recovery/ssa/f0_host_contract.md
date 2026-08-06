# SSA F0 host-contract implementation map

Status: **NOT_VERIFIED** until the implementation and focused command below
pass. Current focused baseline is the legacy boolean oracle, not the amended
contract.

## Existing API and schema changes

| File / current symbol | Required change |
|---|---|
| `scripts/dual_sync_probe/logfmt.py:46-78` (`Clk`, `Health`) | Append compatibility-safe optional fields rather than changing existing positional fields: `Clk.t_local_us: Optional[int] = None`; `Health.role: Optional[str] = None`. Prefer keyed parsing for health because F3 will add counters. Store unknown key/value fields instead of silently discarding them. |
| `logfmt.py:86-138` (`parse_line`) | Try the new grammar before legacy grammar; otherwise the old unanchored `clk` expression will consume a new line and silently discard `t_local_us`. Add typed records for `begin`, `link up`, `link down`, negotiated BLE state, reset/port failure and host segment markers. |
| `logfmt.py:146-188` (`ParsedLog`, `parse_log`) | Add entry metadata containing raw line index and optional shared host-monotonic timestamp. Keep `parse_line(line)` and `parse_log(text)` permissive by default for archived July logs. Add `parse_log(..., strict=False, expected_role=None)` validation; strict mode rejects missing/wrong health roles, untimestamped follower clocks, malformed required events and conflicting roles. Contract errors must reach CLI exit 4. |
| `logfmt.py:171-181` (`_local_anchor`) | Use explicit `Clk.t_local_us` as an anchor. Preserve the interpolation fallback for archived clock lines only. Current correlation interpolates by parsed-record ordinal rather than `ParsedLog` raw-line indexes; change it to consume the stored entry metadata. |
| `logfmt.py:276-299` (`fmt_clk`, `fmt_health`) | Add keyword-only optional arguments. `None` emits legacy grammar for archived-fixture tests; strict synth/F1 emitters always supply timestamp/role. Add formatters for connection and host-segment records. |
| `correlate.py:60-82` (`Correlation`) | Replace the single health aggregate and `stream_expected/loss` with per-role health plus `transport_expected/transport_missing/transport_dup` and `apply_expected/apply_missing/apply_dup`. Export selected-epoch identity, reset/down/reconnect counts and complete GPIO rounds. |
| `correlate.py:119-190` (`correlate`) | Select one coherent post-settle epoch before pairing. Never combine records across `begin`, reset, link-down or sequence reset. Require the final leader/follower active epochs to overlap in shared host time. Keep legacy whole-log correlation only outside strict proof mode. |
| `correlate.py:218-258` (`_stream_integrity`, `_health_aggregate`) | Compare the set of leader TX sequences with follower RX for transport loss, then follower RX with apply for consume loss. A dense-sequence gap or duplicate in the leader log is an evidence-integrity blocker. Aggregate FPS/heap/AP for both roles, dial only from leader, and loss/apply only from follower. |
| `gate_eval.py:56-156` (`evaluate`) | Add `strict_proof`; call a real `link_ready()` first. Return `schema_version`, `overall_status` and derived boolean `overall_pass`. Per gate/subgate returns `status`, never an enum in `pass`. Remove top-level `overall` so stale callers fail loudly; do not duplicate the renamed Gate 3 under two mutable keys. |
| `gate_eval.py:165-247` (`format_summary`, `main`) | Compare `status == "PASS"` exclusively. Exit mapping is `PASS=0`, `FAIL=1`, `BLOCKED=2`, `UNMEASURED=3`, contract/input error `=4`. Resolution after Link Ready is: any measured FAIL → FAIL; else any BLOCKED → BLOCKED; else any required UNMEASURED → UNMEASURED; else PASS. If Link Ready is not PASS, do not score timing gates. |
| `synth.py:36-206` | Emit both roles' health, follower timestamped clock records, link/negotiation events, a common host-time envelope and real RX-without-apply `drop10`. Add disconnect/reconnect/reset controls so tests can prove epochs cannot accumulate. |
| `artifacts/.../probe-log-contract.md:86-112` | Version the grammar. Document permissive legacy versus strict proof mode, host-time envelope, exact connection/negotiation/reset records, role/timestamp additions, transport versus consume loss and the honest Gate-3 name. |

Recommended new strict records (exact token order belongs in the tracked
contract before F1 emits them):

```text
[k1_sync] clk role=follower t_local_us=<u64> est_offset_us=<i64> rtt_us=<u32> n=<u32>
[k1_sync] health role=<leader|follower> fps=<f> heap_min=<u32> ap_p95_us=<u32> dial_linked=<0|1> loss=<u32> dup=<u32>
[k1_sync] link up role=<leader|follower> epoch=<u32> handle=<u16> mtu=<u16>
[k1_sync] link down role=<leader|follower> epoch=<u32> reason=<i32>
[k1_sync] negotiated role=<leader|follower> epoch=<u32> interval_units=<u16> latency=<u16> mtu=<u16> phy_tx=<u8> phy_rx=<u8>
[sync_host] segment name=<token> phase=<start|end> t_host_us=<u64>
```

The capture helper must prefix serial lines from both devices from one shared
`monotonic_ns()` origin. Independent per-port origins cannot prove that the
selected leader and follower epochs overlap.

## Compatibility and fail-closed hazards

1. New `Clk` must parse before legacy `Clk`; the current regex is not
   end-anchored and otherwise drops the new timestamp without error.
2. Do not insert `role` into the middle of the existing `Health` dataclass
   constructor. Current tests and archived callers use six positional fields.
3. Parsing `rst:` as a reset event changes the current noise-count assertion:
   update the noise fixture to distinguish recognised reset evidence from
   skipped garbage.
4. Current scratch runners use `v["overall"]` and a generic bracket-stripper
   (`run_gate0.sh:122-141`). They must abort as deprecated. Feeding raw
   host-prefixed logs directly to `parse_log` is safer than stripping every
   leading bracketed token.
5. No tracked caller exists outside `tests/test_dual_sync_oracle.py`, but JSON
   consumers need `schema_version=2`; deliberately removing `overall` makes an
   old caller fail rather than treating `"BLOCKED"` as truthy.
6. Link Ready must count follower clock *records/samples* unambiguously. Use at
   least 10 timestamped estimator records; do not interpret the firmware's
   cumulative `n` field as ten emitted observations.
7. A `drop10` fixture must preserve RX and omit apply. The legacy synth drops
   both, which tests radio loss rather than the real firmware fault.

## Runner behaviour

- Put serial/capture logic in injectable Python (`capture.py`); keep
  `run_gate0_segments.sh` a thin argument/exit wrapper.
- Open outputs with exclusive creation, keep both ports open for the whole
  run, send faults to the follower only, and require fresh exact
  `SYNC_FAULT: <mode>` plus `[k1_sync] fault=<mode>` acknowledgements after the
  segment marker.
- F0 accepts only `off,delay5,delay20,drop10`; reject `clockoff`.
  `restored` is a label whose command token is `off`.
- Always attempt acknowledged `off` restoration on success, failure, signal or
  timeout. Preserve raw logs and write verdict/INDEX atomically.
- Under `set -euo pipefail`, bracket the evaluator call with `set +e`/captured
  `$?`/`set -e`, accept only codes 0-3 as verdicts, and treat 4 or any unknown
  code as a runner contract failure. The final Gate-0 runner exits zero only
  when all required statuses are explicitly PASS; the F0 plumbing runner is
  labelled `NOT_GATE0` and must never translate a non-PASS verdict to PASS.

## Required focused tests

Extend `tests/test_dual_sync_oracle.py` with: permissive old grammar; strict
wrong/missing role and missing clock timestamp; all four CLI exits plus input
error; summary/JSON string-truthiness regression; empty/health-only; coherent
synthetic link; disconnected-epoch accumulation; sequence reset; both-role
health; AP=0 unmeasured; leader-only dial; zero transport expected; separate
TX→RX and RX→apply loss; silicon-shaped drop10; unsupported token; stale/missing
ACK; non-overwrite; restored→off; and cleanup restoration after injected
failure.

Minimal re-run:

```bash
python3 -m pytest -p no:cacheprovider tests/test_dual_sync_oracle.py -q
```

CLI smoke after fixtures exist:

```bash
python3 -m scripts.dual_sync_probe.gate_eval --strict-proof --summary tests/fixtures/dual_sync/leader_clean.log tests/fixtures/dual_sync/follower_clean.log
```
