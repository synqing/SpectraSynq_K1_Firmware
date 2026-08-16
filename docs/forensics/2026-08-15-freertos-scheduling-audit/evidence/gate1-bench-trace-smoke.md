# Gate 1 bench trace smoke — B489A500

Date: 2026-08-15
Branch: `feat/k1-scheduling-generation-hardening`
Source parent during build: `c68344e1c7ac97e2c63833e1efa20500779faf43` plus the
uncommitted Gate 1 unit recorded by this receipt
Device: B489A500 / USB serial `B4:3A:45:A5:89:B4`
Port used explicitly: `/dev/cu.usbmodem12401`

## Verdict

**RMT completion oracle: BENCH SMOKE PASS.**
**Production Gate 1 baseline: NOT CLOSED — main K1 F887A500 is absent.**
**AP service capacity: RED on both short bench probes; Gate 2 may proceed under the
execution plan's explicit service-overrun rule, but these runs do not replace the main-K1
production baseline or Captain-confirmed real-music leg.**

The bench environment is physically correct for the connected IM69D unit and is separately
allowlisted. It is not labelled production-equivalent.

## Identity and build proof

Live enumeration before upload:

```text
/dev/cu.usbmodem12401 B4:3A:45:A5:89:B4
```

Successful builds:

```text
pio run -e k1_hardware
pio run -e k1_scheduling_trace_dev
pio run -e k1_bench_scheduling_trace_dev
pio run -e k1_bench_scheduling_baseline_probe
```

Guarded bench uploads used only:

```text
pio run -e k1_bench_scheduling_trace_dev -t upload \
  --upload-port /dev/cu.usbmodem12401
pio run -e k1_bench_scheduling_baseline -t upload \
  --upload-port /dev/cu.usbmodem12401
```

The exact dirty-checkout environment name above records the command actually
run. Before the Gate-1 checkpoint it was renamed, without flag or source-filter
changes, to `k1_bench_scheduling_baseline_probe` so the repository's
non-shippable-environment admission rule classifies it correctly.

The main `k1_hardware` binary was built only and was never sent to the bench pinmap.

The trace ELF map contained both required linker-owned symbols:

```text
0x42012ff4 __wrap_rmt_new_tx_channel
0x420130ac __wrap_rmt_transmit
```

The final checkpoint ELF sizes were:

| Environment | text | data | bss | total |
|---|---:|---:|---:|---:|
| `k1_hardware` | 506434 | 194316 | 1261101 | 1961851 |
| `k1_scheduling_trace_dev` | 550246 | 214412 | 1556629 | 2321287 |
| `k1_bench_scheduling_trace_dev` | 545138 | 215132 | 1552829 | 2313099 |
| `k1_bench_scheduling_baseline_probe` | 520166 | 196856 | 1362989 | 2080011 |

The first final-source main-trace link attempt exposed a 1200-byte internal-DRAM
overflow. The repair retained the 64-record ISR ring and reduced only the
duplicate serial-export staging buffer from 64 to 16 records, drained in bounded
chunks. The rebuilt main trace then linked successfully.

### Final-byte identity correction

The live B489A500 capture in this receipt predates the independent review fix to
the CRC seam. Its completion timestamps, GPIO admission, sequence mapping and
drop counters remain valid, but its CRC fields were computed from the
application LED buffers before FastLED scaling/dithering and are therefore
**not admissible as final-byte identity**. The corrected source removes CRCs
from the caller API and computes them inside `__wrap_rmt_transmit` from the
actual 480-byte payload passed to ESP-IDF. A compiled host round-trip proves
that changing those bytes changes the recorded CRC. The bench disconnected
before a corrected device recapture, so device-level final-byte identity stays
`NOT_VERIFIED` and must be recaptured on the next exact-identity window.

## RMT completion capture

The typed sequence was `status -> start -> automatic bounded stop -> status -> dump`.
The trace auto-stopped at the fixed 64-record/channel capacity before overwrite.

```text
channels_ready=1 capture_valid=1 wait_timeout_ms=6
wait_failures=0 pending_failures=0 start_failures=0 stop_failures=0
auto_stops=1 p_complete=64 s_complete=64 p_drops=0 s_drops=0
records=128 p_reaped=64 s_reaped=64
vp_seq=1..64 contiguous; 64 complete primary/secondary pairs
GPIOs: primary=4 secondary=5
payload: 480 bytes/channel; symbols: 3842/channel
```

Measured submit-to-confirmed-completion duration:

| Channel | n | min us | median us | p95 us | p99 us | max us |
|---|---:|---:|---:|---:|---:|---:|
| GPIO 4 / primary | 64 | 4934 | 4936 | 4953.8 | 4955.0 | 4955 |
| GPIO 5 / secondary | 64 | 4915 | 4916 | 4917.0 | 4919.5 | 4922 |

This proves the callback boundary on the bench trace build. It does not prove first visible
photon, the absent production pinmap, or a real-music feature latency.

## Short APCAD service probes

Both captures used the truthful timestamp assumption `1`: I2S read-return is the declared
newest-sample estimate; per-sample hardware timestamps and descriptor residence remain
unknown. Neither run was called silence or music.

| Build | Rows | AP Hz | active work median | p95 | p99 | max | newest-to-publish p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `k1_bench_scheduling_trace_dev` | 102 | 101.61 | 8325 us | 10008 us | 10193 us | 10432 us | 9933 us |
| `k1_bench_scheduling_baseline` | 96 | 95.57 | 9000 us | 11067 us | 11363 us | 11497 us | 10988 us |

Both had:

```text
frame gaps=0
capture-sequence gaps=0
timestamp-order failures=0
I2S failures=0
byte-count failures=0
capture drops=0
```

The nominal arrival period is 7500 us. These short runs therefore reject the proposition
that current AP service demand is sustainably below arrival on this bench. The surprising
ordering between the two short legs also means their delta must not be used as an
instrumentation-cost estimate; longer paired runs on the same fixture are still required.

## Remaining admission blockers

1. Main K1 F887A500 is not connected, so exact production pinmap/runtime proof is absent.
2. Captain-confirmed audible real music has not been supplied in this run.
3. Worst enabled primary/secondary pair plus simultaneous crossfade is not yet frozen and
   captured on the production unit.
4. One-second bench APCAD legs are service-capacity witnesses, not stable distribution
   baselines.
5. Acoustic-to-photon latency remains unmeasured.

No calibration command, microphone-slot mutation, radio enablement, generated audio,
priority change, task extraction, GDFT change, or production upload occurred.

## Final source checkpoint validation

After the independent CRC review, both AP and VP stack-watermark scans were also
rate-limited to one hertz while an audit is active; no scan is evaluated when the audit
is inactive. The final source checkpoint produced:

```text
focused scheduling tests: 26 passed
full host suite:            1142 passed, 1 skipped
production build:           PASS
scheduling trace build:     PASS
Gate 0 trust root:          PASS, 6 files
Gate 0 control:             PASS, 90 checks / 2 records
Gate 0 fault battery:       PASS, 21 / 21 faults rejected
git diff --check:           PASS
```

The skipped test is the repository's existing explicit skip, not a scheduling-gate
deselection or xfail. The corrected device-level final-byte capture remains open as
stated above.
