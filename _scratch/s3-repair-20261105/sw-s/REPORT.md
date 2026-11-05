# Stream S — settings save

1. Changed artefacts
- Product source unchanged: existing buffered record, retained handle, render park, silence-first and sixty-second fallback retained.
- `source-review.json`, `host.log`: source hashes and focused host verification.
- Main scratch `save-closeout-metrics.json`: exact Python gate arguments, fixture hash, trace hashes and measured event windows.
- Main scratch `queue/s-1.result.json`: OPEN result after three capture approaches.

2. Gates run
- `python3 -m pytest tests/test_k1_persist_park_static.py tests/test_k1_persistence_request_boundary.py -q`: exit0, eight tests; `host.log`.
- Five existing trace captures checked by the recorded `command_argv` in main `save-closeout-metrics.json`. Exit codes appear below; missing complete save spans fail the gate.
- Re-run any row with `python3 -c 'import json,subprocess,sys; r=json.load(open("_scratch/s3-repair-20261105/save-closeout-metrics.json")); sys.exit(subprocess.run(r["captures"][int(sys.argv[1])]["command_argv"]).returncode)' 4` from the main checkout (row4 is true fallback).

3. Measured numbers
- All rows: environment `k1_fe_bench_b489_trace_dev`, revision `ec7c9bc9`, configured processor240 megahertz, flags `repair-trace-preamble.json`; measured on silicon. Microseconds below. These are rolling event windows, not whole-session cadence.
- p99 means99th percentile; nearest-rank calculation. Mean is arithmetic mean. Misses are consecutive intervals above8333microseconds. Recovery includes the first following compliant frame. Signed24-bit counters are differenced modulo2^24.

| Capture | p99 | Mean | Misses | Recovery | Maximum gap | Save duration | Gate exit |
|---|---:|---:|---:|---:|---:|---|---:|
| save-silence-edge | 6016 | 5192.774 | 0 | 0 | 6498 | [] | 1 |
| save-music-fallback | 6044 | 5702.474 | 0 | 0 | 6061 | [] | 1 |
| save-debug-silence-edge | 6066 | 5785.146 | 0 | 0 | 6505 | [] | 1 |
| save-debug-music-fallback | 6041 | 5638.149 | 1 | 2 | 10002 | [3695] | 0 |
| save-line-fallback | 6460 | 5798.373 | 1 | 2 | 9967 | [7592] | 0 |

- True music fallback: observed after60.1377seconds while playback remained active. Save duration7592microseconds: render-park wait4635, single write63, flush2497. The four cadence limits hold inside this captured event window.
- The debug music leg saved after7.2738seconds: a quiet-trigger save during playback, not the sixty-second fallback.

4. Not verified
- **OPEN:** silence-edge capture contains no complete save span; whole-session cadence is unavailable from the rolling buffer.
- Approach1: invalid `:debug=on/off` tokens, no observed save markers or retained spans.
- Approach2: corrected `:debug=true/false`; quiet save marker observed but its span absent; music resumed into a sampled quiet interval and saved early.
- Approach3: noisy line input held silence false; sixty-second fallback and its complete event window captured. This does not supply the missing quiet-save span.
- Sector erase is not observable through existing exposed counters.
- No additional capture, source change, full-suite run or new tooling.

5. Open decisions
- None for Captain. Preserve the bounded successful fallback evidence, mark section4 OPEN for missing quiet-save/whole-session coverage, continue the lane.
