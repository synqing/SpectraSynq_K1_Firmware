---
name: dsp-performance-profiling
description: Use when DSP implementation is signal-verified and needs real-time viability confirmation - measures execution time against latency budget, detects heap allocations in audio path, reports deadline miss rate, and compares algorithm variants
---

# DSP Performance Profiling

## Overview

A function that is signal-correct but misses deadlines is a bug. Performance profiling is mandatory for any code that runs in the audio callback or render loop.

**Core principle:** Measure, do not estimate. The difference between "should be fast enough" and "is fast enough" is an audible glitch.

## The Iron Law

```
NO DSP CODE IN REAL-TIME PATH WITHOUT PROFILING EVIDENCE
```

If you have not measured execution time against the latency budget, you cannot claim the code meets real-time constraints.

## When to Use

**Always after:**
- Implementing any function called from the audio callback
- Implementing any function called from the render loop
- Changing FFT size, buffer size, or overlap ratio
- Changing filter order or topology
- Changing algorithm (e.g. replacing FIR with IIR)
- Porting from float to fixed-point (to verify the fixed-point version is actually faster)

**Do not skip when:**
- "It is a simple function" -- simple functions called 44100 times per second add up
- "Same algorithm, different parameters" -- parameters change cache behaviour
- "Only added one line" -- one allocation in the wrong place is a deadline miss

## Budget Calculation

```
callback_budget_us = (buffer_size / sample_rate) * 1_000_000

Examples:
  256 samples @ 44100 Hz = 5804 us (5.8 ms)
  512 samples @ 44100 Hz = 11610 us (11.6 ms)
  128 samples @ 48000 Hz = 2667 us (2.7 ms)
  1024 samples @ 44100 Hz = 23220 us (23.2 ms)

Safety margin: Target 80% of budget maximum.
  256 @ 44100: target <= 4643 us
```

**The 80% rule:** Never consume more than 80% of the callback budget. The remaining 20% absorbs OS scheduling jitter, cache cold-starts, and interrupt latency.

## Profiling Protocol

### 1. Measure Execution Time

```python
import time
import numpy as np

def profile_dsp_function(func, input_signal, iterations=1000):
    """Measure DSP function execution time.

    Returns dict with mean, p50, p95, p99, max in microseconds.
    First 10 iterations are discarded (warmup).
    """
    warmup = 10
    times = []
    for i in range(iterations + warmup):
        start = time.perf_counter_ns()
        func(input_signal)
        elapsed_ns = time.perf_counter_ns() - start
        if i >= warmup:
            times.append(elapsed_ns / 1000.0)  # Convert to us

    times = np.array(times)
    return {
        "mean_us": float(np.mean(times)),
        "p50_us": float(np.percentile(times, 50)),
        "p95_us": float(np.percentile(times, 95)),
        "p99_us": float(np.percentile(times, 99)),
        "max_us": float(np.max(times)),
        "stddev_us": float(np.std(times)),
        "iterations": iterations,
    }
```

For C/C++ (embedded), use cycle-accurate timers:

```c
// ESP32 example
uint32_t start = esp_timer_get_time();  // microseconds
process_audio(buffer, size);
uint32_t elapsed = esp_timer_get_time() - start;
// Log to histogram
```

### 2. Check for Heap Allocations

**Zero allocations is the target.** Any allocation in the audio callback or render loop is a bug.

Platform-specific approaches:

```python
# Python: Use tracemalloc
import tracemalloc
tracemalloc.start()
snapshot_before = tracemalloc.take_snapshot()
func(input_signal)
snapshot_after = tracemalloc.take_snapshot()
stats = snapshot_after.compare_to(snapshot_before, 'lineno')
assert len(stats) == 0, f"Allocations detected: {stats}"
```

```c
// C/C++: Override malloc, count calls
static int malloc_count = 0;
void* counting_malloc(size_t size) {
    malloc_count++;
    return real_malloc(size);
}
// After processing:
assert(malloc_count == 0);
```

### 3. Measure Deadline Miss Rate

```python
def measure_deadline_compliance(func, input_signal, budget_us, duration_s, sample_rate, buffer_size):
    """Simulate real-time processing and count deadline misses."""
    n_callbacks = int(duration_s * sample_rate / buffer_size)
    miss_count = 0
    miss_times = []

    for i in range(n_callbacks):
        start = time.perf_counter_ns()
        func(input_signal)
        elapsed_us = (time.perf_counter_ns() - start) / 1000.0
        if elapsed_us > budget_us:
            miss_count += 1
            miss_times.append((i, elapsed_us))

    return {
        "total_callbacks": n_callbacks,
        "miss_count": miss_count,
        "miss_rate": miss_count / n_callbacks,
        "worst_misses": sorted(miss_times, key=lambda x: -x[1])[:10],
    }
```

### 4. A/B Algorithm Comparison

When comparing two implementations of the same function:

```python
def compare_algorithms(func_a, func_b, input_signal, iterations=1000):
    """Compare two algorithm variants on same input."""
    profile_a = profile_dsp_function(func_a, input_signal, iterations)
    profile_b = profile_dsp_function(func_b, input_signal, iterations)

    speedup = profile_a["mean_us"] / profile_b["mean_us"]
    return {
        "a": profile_a,
        "b": profile_b,
        "speedup_b_over_a": speedup,
        "verdict": "B is faster" if speedup > 1.0 else "A is faster",
    }
```

## Report Format

Every profiling run produces a report:

```
DSP Performance Report
======================
Function: process_fft_1024
Date: 2026-03-18
Platform: {{PLATFORM}}
Buffer: 256 samples @ 44100 Hz
Budget: 5804 us (80% target: 4643 us)

Execution Time:
  Mean:   312 us  (5.4% of budget)  PASS
  P95:    487 us  (8.4% of budget)  PASS
  P99:    623 us  (10.7% of budget) PASS
  Max:    891 us  (15.3% of budget) PASS

Deadline Compliance (60s simulation):
  Callbacks: 10,335
  Misses: 0
  Miss rate: 0.00%  PASS

Heap Allocations: 0  PASS

Verdict: PASS - within budget with 84.6% headroom
```

## Pass/Fail Criteria

| Metric | Pass | Fail |
|--------|------|------|
| P99 execution time | <= 80% of callback budget | > 80% of callback budget |
| Deadline miss rate | 0% over 60s simulation | Any miss |
| Heap allocations in RT path | 0 | Any |
| Regression vs previous | <= 10% slower | > 10% slower without justification |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Measuring with debug/unoptimised build | Always profile release/optimised build |
| No warmup iterations | Discard first 10+ iterations (cache cold) |
| Using wall clock (`time.time`) | Use `perf_counter_ns` or cycle counter |
| Profiling on dev machine, deploying to embedded | Profile on target hardware |
| Measuring once | Measure 1000+ iterations, report percentiles |
| "Mean is within budget" | P99 matters more than mean for real-time |

## Red Flags -- STOP

- "It should be fast enough" -- measure it
- "Only 5% of budget, no need to profile" -- profile anyway, it takes 2 minutes
- "Will optimise later" -- optimise now; late optimisation means redesign
- P95 within budget but P99 is not -- you have a tail latency problem
- Mean is fine but deadline miss rate > 0 -- investigate the outliers

## Integration

**Called after:** `/signal-processing-verification` (signal correctness confirmed)
**Called before:** `/requesting-code-review` (profiling results inform review)
**Uses:** `/dsp-test-fixtures` for benchmark input signals
