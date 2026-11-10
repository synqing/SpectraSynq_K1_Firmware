// PlaybackEngine — real-time ShowBundle → CDC FeatureFrame streamer.
// Uses drift-corrected setTimeout scheduling (proven pattern from intent_cdc_stream.js).
// v0.3: device-tier param_curves emitted as K1CT PARAM_SET alongside PRSM frames.
// Zero external dependencies — Node built-ins only.

import { evalFrameAtTime, evalParamCurvesAtTime, hasParamSlopeEdge, tickTimeUs, tickCount, curveEndUs } from "./vm.js";
import { makePrsmPacket, makeK1ctParamSet, writeCdcPort } from "./cdc.js";

const STATUS_INTERVAL = 10;       // emit onStatus every N frames (~12/sec at 120 Hz)
const PARAM_BASE_INTERVAL = 12;   // base: evaluate param_curves every 12 ticks (~10Hz at 120Hz)
const PARAM_BURST_INTERVAL = 2;   // burst: every 2 ticks (~60Hz at 120Hz) during steep slopes
const BURST_WINDOW_TICKS = 36;    // sustain burst for 36 ticks (~300ms at 120Hz) after edge detect
const SLOPE_LOOKAHEAD_US = 100000; // 100ms lookahead for slope detection
const SLOPE_THRESHOLD_U16 = 3000;  // u16 delta over lookahead that triggers burst

/**
 * @typedef {Object} PlaybackStatus
 * @property {'stopped'|'playing'} state
 * @property {number} seq       - frames sent
 * @property {number} t_us      - current timeline position
 * @property {number} elapsed_ms - wall-clock ms since play started
 * @property {number} total_ms  - total duration in ms
 * @property {number} paramSets - K1CT PARAM_SET frames sent
 * @property {string|null} error
 */

export class PlaybackEngine {
  #bundle;
  #hz;
  #fd;
  #onStatus;
  #state = "stopped";
  #seq = 0;
  #tick = 0;
  #totalTicks = 0;
  #wallStart = 0;
  #bundleStart = 0;
  #timer = null;
  #lastTUs = 0;

  // param_curves state
  #hasParamCurves = false;
  #lastParamValues = new Map(); // hex_id → last sent u16 value
  #paramSetCount = 0;
  #burstTicksRemaining = 0; // edge-burst countdown (ticks until back to base rate)
  #lastChangedIds = [];      // hex IDs changed in most recent param eval
  #consecutiveWriteErrors = 0; // error resilience: skip frames on transient errors
  #droppedFrames = 0;
  #curveEnd = 0; // latest keypoint t_us across all curves

  /**
   * @param {Object} opts
   * @param {Object} opts.bundle  - normalised ShowBundle
   * @param {number} opts.hz      - playback rate (1..1000)
   * @param {number} opts.fd      - open CDC port file descriptor
   * @param {function(PlaybackStatus):void} opts.onStatus - status callback
   */
  constructor({ bundle, hz, fd, onStatus }) {
    this.#bundle = bundle;
    this.#hz = hz;
    this.#fd = fd;
    this.#onStatus = onStatus ?? (() => {});
    this.#totalTicks = tickCount(bundle.duration_us, hz);
    this.#curveEnd = curveEndUs(bundle);

    // v0.3: precheck device-tier param_curves availability.
    this.#hasParamCurves = (
      bundle.version === "0.3" &&
      bundle.device_profile !== "none" &&
      bundle.param_curves &&
      Object.keys(bundle.param_curves).length > 0
    );
  }

  get state() { return this.#state; }
  get position() { return this.#lastTUs; }
  get seq() { return this.#seq; }
  get paramSetCount() { return this.#paramSetCount; }

  /**
   * Begin playback from a timeline position (microseconds).
   */
  play(startTUs = 0) {
    if (this.#state === "playing") this.stop();

    // Find the first tick at or after startTUs.
    const startTick = Math.max(0, Math.ceil(
      Number(BigInt(startTUs) * BigInt(this.#hz) / 1000000n)
    ));

    this.#tick = startTick;
    this.#seq = 0;
    this.#paramSetCount = 0;
    this.#lastParamValues.clear();
    this.#burstTicksRemaining = 0;
    this.#bundleStart = startTUs;
    this.#wallStart = performance.now();
    this.#state = "playing";
    this.#emitStatus();
    this.#scheduleNext();
  }

  /**
   * Stop playback.
   */
  stop() {
    if (this.#timer !== null) {
      clearTimeout(this.#timer);
      this.#timer = null;
    }
    if (this.#state !== "stopped") {
      this.#state = "stopped";
      this.#emitStatus();
    }
  }

  /**
   * Seek to a new timeline position mid-playback.
   * No-op if not playing. Seq continues incrementing (no reset).
   * Emits one immediate frame at the new position so the device snaps instantly.
   */
  seek(t_us) {
    if (this.#state !== "playing") return;

    // Cancel pending tick.
    if (this.#timer !== null) {
      clearTimeout(this.#timer);
      this.#timer = null;
    }

    // Recompute tick position (same BigInt formula as play()).
    this.#tick = Math.max(0, Math.ceil(
      Number(BigInt(t_us) * BigInt(this.#hz) / 1000000n)
    ));
    this.#bundleStart = t_us;
    this.#wallStart = performance.now();

    // Force param re-evaluation at new position.
    this.#lastParamValues.clear();
    this.#burstTicksRemaining = 0;

    // Emit one immediate frame so the device snaps to the new position.
    const seekT = tickTimeUs(this.#tick, this.#hz);
    if (seekT < this.#bundle.duration_us) {
      try {
        const frame = evalFrameAtTime(this.#bundle, seekT);
        const pkt = makePrsmPacket({
          hz: this.#hz,
          seq: this.#seq,
          t_us: frame.t_us,
          prim8_u16: frame.prim8_u16,
        });
        writeCdcPort(this.#fd, pkt);
        this.#seq++;
        this.#consecutiveWriteErrors = 0;

        if (this.#hasParamCurves) {
          this.#emitParamUpdates(seekT);
        }
      } catch (err) {
        if (err.code === "ENXIO") {
          this.#state = "stopped";
          this.#emitStatus(`Device lost: ${err.message}`);
          return;
        }
        // Transient seek error — continue anyway, next tick will retry.
        this.#droppedFrames++;
      }
    }

    this.#lastTUs = seekT;
    this.#emitStatus();
    this.#scheduleNext();
  }

  /**
   * Clean up. Call when discarding the engine.
   */
  destroy() {
    this.stop();
  }

  // -------------------------------------------------------------------------
  // Internal
  // -------------------------------------------------------------------------

  #scheduleNext() {
    if (this.#state !== "playing") return;

    const t_us = tickTimeUs(this.#tick, this.#hz);

    // Past end of bundle — stop.
    if (t_us >= this.#bundle.duration_us || this.#tick >= this.#totalTicks) {
      this.#state = "stopped";
      this.#emitStatus();
      return;
    }

    // Drift-corrected delay: how long until this frame should fire?
    const elapsedUs = t_us - this.#bundleStart;
    const targetWall = this.#wallStart + elapsedUs / 1000.0;
    const now = performance.now();
    const delay = Math.max(0, targetWall - now);

    this.#timer = setTimeout(() => {
      this.#timer = null;
      if (this.#state !== "playing") return;

      try {
        // Past curve data: stop sending PRSM frames so the K1's 250ms
        // freshness timeout triggers audio-energy fallback. The engine
        // keeps running for timeline/position tracking.
        const pastCurveEnd = this.#curveEnd > 0 && t_us > this.#curveEnd;

        if (!pastCurveEnd) {
          // PRSM frame (every tick within curve data).
          const frame = evalFrameAtTime(this.#bundle, t_us);
          const pkt = makePrsmPacket({
            hz: this.#hz,
            seq: this.#seq,
            t_us: frame.t_us,
            prim8_u16: frame.prim8_u16,
          });
          writeCdcPort(this.#fd, pkt);
          this.#consecutiveWriteErrors = 0;

          // Device-tier param_curves (adaptive rate: base 10Hz, burst 60Hz near edges).
          if (this.#hasParamCurves) {
            const interval = this.#burstTicksRemaining > 0
              ? PARAM_BURST_INTERVAL
              : PARAM_BASE_INTERVAL;
            if (this.#tick % interval === 0) {
              this.#emitParamUpdates(t_us);
              // Slope detection: check if we're approaching a steep edge.
              if (hasParamSlopeEdge(this.#bundle, t_us, SLOPE_LOOKAHEAD_US, SLOPE_THRESHOLD_U16)) {
                this.#burstTicksRemaining = BURST_WINDOW_TICKS;
              }
            }
            if (this.#burstTicksRemaining > 0) this.#burstTicksRemaining--;
          }
        }
        // pastCurveEnd: no write, no error — engine ticks silently, K1 falls back.
      } catch (err) {
        this.#consecutiveWriteErrors++;
        this.#droppedFrames++;

        // ENXIO = device gone. Fatal — stop immediately.
        if (err.code === "ENXIO") {
          this.#state = "stopped";
          this.#emitStatus(`Device lost: ${err.message}`);
          return;
        }

        // Transient errors (EAGAIN, etc.): skip frame, keep going.
        // Stop only after 10 consecutive failures.
        if (this.#consecutiveWriteErrors >= 10) {
          this.#state = "stopped";
          this.#emitStatus(`${this.#consecutiveWriteErrors} consecutive write errors: ${err.message}`);
          return;
        }
        // Skip this frame, continue to next tick.
      }

      this.#lastTUs = t_us;
      this.#seq++;
      this.#tick++;

      // Emit status periodically.
      if (this.#seq % STATUS_INTERVAL === 0) {
        this.#emitStatus();
      }

      this.#scheduleNext();
    }, delay);
  }

  /**
   * Evaluate param_curves and send K1CT PARAM_SET for changed values.
   * Fire-and-forget: no ACK reading. Changed-value debounce.
   */
  #emitParamUpdates(t_us) {
    const current = evalParamCurvesAtTime(this.#bundle, t_us);
    const changed = [];
    for (const [hexId, value] of current) {
      // Skip universal Prim8 tier (already in PRSM frames).
      const id = parseInt(hexId, 16);
      if (id <= 0x0007) continue;

      const prev = this.#lastParamValues.get(hexId);
      if (prev === value) continue; // unchanged — skip

      const frame = makeK1ctParamSet(id, value);
      writeCdcPort(this.#fd, frame);
      this.#lastParamValues.set(hexId, value);
      this.#paramSetCount++;
      changed.push(hexId);
    }
    this.#lastChangedIds = changed;
  }

  #emitStatus(error = null) {
    const elapsed_ms = performance.now() - this.#wallStart;
    const total_ms = this.#bundle.duration_us / 1000;
    this.#onStatus({
      state: this.#state,
      seq: this.#seq,
      t_us: this.#lastTUs,
      elapsed_ms: Math.round(elapsed_ms),
      total_ms: Math.round(total_ms),
      paramSets: this.#paramSetCount,
      paramBurst: this.#burstTicksRemaining > 0,
      paramChanged: this.#lastChangedIds.slice(),
      paramProfile: this.#hasParamCurves ? (this.#bundle.device_profile || "none") : "none",
      droppedFrames: this.#droppedFrames,
      error,
    });
  }
}
