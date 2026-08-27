/* Colour Lab core — pure parse / serialise / paint / LUT / store / queue.
 *
 * Contract: tools/colourlab/README.md
 * Render authority: tests/colour_lab.py (host replica of k1_colour_lab.h)
 * No DOM. No Web Serial. UMD: module.exports + global.ColourLab.
 */
"use strict";

(function (root, factory) {
  var api = factory();
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  var g = typeof globalThis !== "undefined" ? globalThis
        : typeof global !== "undefined" ? global
        : root;
  if (g) g.ColourLab = api;
}(typeof self !== "undefined" ? self : this, function () {

  var MAX_STOPS = 8;
  var CARD_REGIONS = 17;
  var BOTH_SCALE = 0.30;
  var GAIN_MIN = 0.0;
  var GAIN_MAX = 2.0;
  var GAMMA_MIN = 0.20;
  var GAMMA_MAX = 4.00;
  var RAMP_V = 0.55;
  var DEFAULT_U8 = 140;
  var USER_SLOT = 15;
  var PAINT_STOPS_MAX_CHARS = 158; /* strlen(data) < 159 */
  var SAFETY_TIMEOUT_MS = 800;
  var COMMAND_TIMEOUT_MS = 1500;
  var GREYS = [0, 1, 16, 32, 64, 96, 128, 160, 192, 224, 240, 254, 255];
  var GOLD = [255, 140, 0];
  var PAINT_MODES = ["off", "solid", "ramp", "stops", "card"];
  var PAINT_TARGETS = ["primary", "secondary", "both"];

  var COLOUR_LAB_COMMANDS = [
    "paint", "paint_target", "paint_rgb", "paint_sv", "paint_stops",
    "paint_status", "tune_gain", "tune_gamma", "tune_reset", "tune_save",
    "tune_status",
  ];
  var PROFILING_COMMANDS = ["chip_id", "build", "look_status"];
  var COMMANDS = COLOUR_LAB_COMMANDS.concat(PROFILING_COMMANDS);
  var MUTATION_COMMANDS = {
    paint: true, paint_target: true, paint_rgb: true, paint_sv: true,
    paint_stops: true, tune_gain: true, tune_gamma: true, tune_reset: true,
    tune_save: true,
  };
  var SUPERSESSION_COMMANDS = {
    tune_gain: "gain", tune_gamma: "gamma", paint_sv: "sv",
  };

  /* Source-frozen. LED counts from config_types.h
   * (K1_BENCH_LED150_GPIO39_40_V1 → 150/150; else default 160/160).
   * Both-scale only under K1_WS2816_LEVER2_V1 (k1_main_rpl_im69d).
   * LOOK: env= is hardcoded from K1_LOOK_LIB_WS2812_V1, not K1_BUILD_ENV. */
  var ENV_PROFILES = {
    k1_main_rpl_im69d: {
      env: "k1_main_rpl_im69d",
      chip_id: "9087A500",
      primary_led_count: 160,
      secondary_led_count: 160,
      both_scale_enabled: true,
      both_scale: 0.30,
      slot15_supported: true,
      look_backend: "ws2816_u16",
    },
    k1_bench_im69d_led150: {
      env: "k1_bench_im69d_led150",
      chip_id: "B489A500",
      primary_led_count: 150,
      secondary_led_count: 150,
      both_scale_enabled: false,
      both_scale: null,
      slot15_supported: false,
      look_backend: "ws2812_u8",
    },
  };

  var CONNECTION_STATES = [
    "unsupported", "disconnected", "requesting", "opening",
    "profiling", "hydrating", "ready", "device-lost", "error",
  ];

  var PRE_LUT_LABEL =
    "Pre-LUT stimulus preview — effective hardware correction unknown.";
  var OUTPUT_UNKNOWN = "output state unknown";
  var DISCONNECT_WAIT_MS = 1200;

  function clone(x) {
    return JSON.parse(JSON.stringify(x));
  }

  function hsv(h, s, v) {
    if (!Number.isFinite(h)) h = 0.0;
    if (!Number.isFinite(s)) s = 0.0;
    if (!Number.isFinite(v)) v = 0.0;
    h -= Math.floor(h);
    if (h < 0.0) h += 1.0;
    s = Math.min(1.0, Math.max(0.0, s));
    v = Math.min(1.0, Math.max(0.0, v));
    if (s <= 0.0) return [v, v, v];
    var h6 = h * 6.0;
    var sector = Math.trunc(h6);
    if (sector >= 6) sector = 0;
    var f = h6 - sector;
    var p = v * (1.0 - s);
    var q = v * (1.0 - s * f);
    var t = v * (1.0 - s * (1.0 - f));
    switch (sector) {
      case 0: return [v, t, p];
      case 1: return [q, v, p];
      case 2: return [p, v, t];
      case 3: return [p, q, v];
      case 4: return [t, p, v];
      default: return [v, p, q];
    }
  }

  function region(i, n, nreg) {
    if (nreg == null) nreg = CARD_REGIONS;
    if (n <= 0 || nreg <= 0) return 0;
    return Math.floor((i * nreg) / n);
  }

  function cardRgb(reg) {
    if (reg >= 0 && reg < 13) {
      var g = GREYS[reg] / 255.0;
      return [g, g, g];
    }
    if (reg === 13) return [1.0, 0.0, 0.0];
    if (reg === 14) return [0.0, 1.0, 0.0];
    if (reg === 15) return [0.0, 0.0, 1.0];
    return [GOLD[0] / 255.0, GOLD[1] / 255.0, GOLD[2] / 255.0];
  }

  function pixel(paint, i, n) {
    if (n <= 0) return [0, 0, 0];
    switch (paint.mode) {
      case "solid":
        return [paint.r / 255.0, paint.g / 255.0, paint.b / 255.0];
      case "ramp": {
        var h = (n <= 1) ? 0.0 : i / n;
        return hsv(h, paint.s, paint.v);
      }
      case "stops": {
        var st = paint.stops || [];
        if (st.length === 0) return [0, 0, 0];
        if (st.length === 1 || n <= 1) {
          return [st[0][0] / 255.0, st[0][1] / 255.0, st[0][2] / 255.0];
        }
        var t = i / (n - 1);
        var scaled = t * (st.length - 1);
        var seg = Math.trunc(scaled);
        if (seg >= st.length - 1) seg = st.length - 2;
        if (seg < 0) seg = 0;
        var frac = scaled - seg;
        var a = st[seg];
        var b = st[seg + 1];
        return [
          (a[0] + (b[0] - a[0]) * frac) / 255.0,
          (a[1] + (b[1] - a[1]) * frac) / 255.0,
          (a[2] + (b[2] - a[2]) * frac) / 255.0,
        ];
      }
      case "card":
        return cardRgb(region(i, n, CARD_REGIONS));
      default:
        return [0, 0, 0];
    }
  }

  function sqTruncToU16(f) {
    var raw = Math.trunc(f * 65536.0);
    if (raw <= 0) return 0;
    var v = Math.floor((raw * 65535) / 65536);
    return v > 65535 ? 65535 : v;
  }

  function satU16(y) {
    if (!(y > 0.0)) return 0;
    if (y >= 65535.0) return 65535;
    return Math.floor(y + 0.5);
  }

  function curveU16(i, gain, gamma) {
    if (gain === 1.0 && gamma === 1.0) return i * 257;
    if (i === 0) return 0;
    var y = gain * 65535.0 * Math.pow(i / 255.0, 1.0 / gamma);
    return satU16(y);
  }

  function buildRgb1d(tune) {
    var x = new Array(256);
    var r = new Array(256);
    var g = new Array(256);
    var b = new Array(256);
    for (var i = 0; i < 256; i++) {
      x[i] = i * 257;
      r[i] = curveU16(i, tune.gain_r, tune.gamma);
      g[i] = curveU16(i, tune.gain_g, tune.gamma);
      b[i] = curveU16(i, tune.gain_b, tune.gamma);
    }
    return { x: x, r: r, g: g, b: b };
  }

  function rgb1dValid(nodes) {
    for (var i = 0; i < 256; i++) {
      if (nodes.x[i] !== i * 257) return false;
    }
    var chs = ["r", "g", "b"];
    for (var c = 0; c < chs.length; c++) {
      var ch = chs[c];
      for (var j = 1; j < 256; j++) {
        if (nodes[ch][j] < nodes[ch][j - 1]) return false;
      }
    }
    return true;
  }

  function lutLerp1d(v, xs, ys) {
    if (v === 0) return 0;
    if (v >= 65535) return 65535;
    var lo = 0;
    var hi = 255;
    while (hi - lo > 1) {
      var mid = (lo + hi) >> 1;
      if (xs[mid] <= v) lo = mid;
      else hi = mid;
    }
    var x0 = xs[lo];
    var x1 = xs[hi];
    var y0 = ys[lo];
    var y1 = ys[hi];
    if (x1 <= x0) return y0;
    var num = (y1 - y0) * (v - x0);
    var den = x1 - x0;
    return y0 + Math.floor((num + (den >> 1)) / den);
  }

  function renderChannel(paint, tune, channel, options) {
    options = options || {};
    var n = options.n;
    if (n == null) {
      throw new Error("renderChannel requires options.n from the device profile");
    }
    if (paint.mode === "off") return { pre: null, post: null };
    var targeted = paint.target === "both" || paint.target === channel;
    if (!targeted) return { pre: null, post: null };
    var scale = 1.0;
    if (paint.target === "both" && options.both_scale_enabled) {
      scale = options.both_scale != null ? options.both_scale : BOTH_SCALE;
    }
    var nodes = buildRgb1d(tune || identityTune());
    var pre = new Array(3 * n);
    var post = new Array(3 * n);
    for (var i = 0; i < n; i++) {
      var rgb = pixel(paint, i, n);
      var ur = sqTruncToU16(rgb[0] * scale);
      var ug = sqTruncToU16(rgb[1] * scale);
      var ub = sqTruncToU16(rgb[2] * scale);
      pre[3 * i] = ur;
      pre[3 * i + 1] = ug;
      pre[3 * i + 2] = ub;
      post[3 * i] = lutLerp1d(ur, nodes.x, nodes.r);
      post[3 * i + 1] = lutLerp1d(ug, nodes.x, nodes.g);
      post[3 * i + 2] = lutLerp1d(ub, nodes.x, nodes.b);
    }
    return { pre: pre, post: post };
  }

  function renderBoth(paint, tune, options) {
    return {
      primary: renderChannel(paint, tune, "primary", options),
      secondary: renderChannel(paint, tune, "secondary", options),
    };
  }

  function identityTune() {
    return { gain_r: 1.0, gain_g: 1.0, gain_b: 1.0, gamma: 1.0 };
  }

  function fmtFloat(x) {
    if (!Number.isFinite(x)) throw new Error("non-finite float");
    var r = Math.round(x * 1000) / 1000;
    if (Object.is(r, -0)) r = 0;
    if (Number.isInteger(r)) return String(r);
    return String(r);
  }

  function assertInt255(v, name) {
    if (!Number.isInteger(v) || v < 0 || v > 255) {
      throw new Error(name + " out of range 0-255: " + v);
    }
  }

  function serializeCommand(name, data) {
    if (COMMANDS.indexOf(name) === -1) {
      throw new Error("unknown command: " + name);
    }
    if (data === undefined || data === null || data === "") {
      return ":" + name;
    }
    return ":" + name + "=" + data;
  }

  function serializeWire(name, data) {
    return serializeCommand(name, data) + "\n";
  }

  function paintStopsData(stops) {
    if (!Array.isArray(stops) || stops.length < 1 || stops.length > MAX_STOPS) {
      throw new Error("stops must have 1-" + MAX_STOPS + " entries");
    }
    var parts = stops.map(function (t, i) {
      assertInt255(t[0], "stop" + i + ".r");
      assertInt255(t[1], "stop" + i + ".g");
      assertInt255(t[2], "stop" + i + ".b");
      return t[0] + "," + t[1] + "," + t[2];
    });
    var data = parts.join(";");
    if (data.length > PAINT_STOPS_MAX_CHARS) {
      throw new Error("stops string too long for firmware buffer");
    }
    return data;
  }

  var serialize = {
    paint: function (mode) {
      if (PAINT_MODES.indexOf(mode) === -1) throw new Error("bad mode " + mode);
      return serializeCommand("paint", mode);
    },
    paintTarget: function (t) {
      if (PAINT_TARGETS.indexOf(t) === -1) throw new Error("bad target " + t);
      return serializeCommand("paint_target", t);
    },
    paintRgb: function (r, g, b) {
      assertInt255(r, "r");
      assertInt255(g, "g");
      assertInt255(b, "b");
      return serializeCommand("paint_rgb", r + "," + g + "," + b);
    },
    paintSv: function (s, v) {
      if (!Number.isFinite(s) || s < 0 || s > 1) throw new Error("bad s");
      if (!Number.isFinite(v) || v < 0 || v > 1) throw new Error("bad v");
      return serializeCommand("paint_sv", fmtFloat(s) + "," + fmtFloat(v));
    },
    paintStops: function (stops) {
      return serializeCommand("paint_stops", paintStopsData(stops));
    },
    paintStatus: function () { return serializeCommand("paint_status"); },
    tuneGain: function (r, g, b) {
      if (!Number.isFinite(r) || r < GAIN_MIN || r > GAIN_MAX) {
        throw new Error("gain_r out of range: " + r);
      }
      if (!Number.isFinite(g) || g < GAIN_MIN || g > GAIN_MAX) {
        throw new Error("gain_g out of range: " + g);
      }
      if (!Number.isFinite(b) || b < GAIN_MIN || b > GAIN_MAX) {
        throw new Error("gain_b out of range: " + b);
      }
      return serializeCommand(
        "tune_gain",
        fmtFloat(r) + "," + fmtFloat(g) + "," + fmtFloat(b)
      );
    },
    tuneGamma: function (g) {
      if (!Number.isFinite(g) || g < GAMMA_MIN || g > GAMMA_MAX) {
        throw new Error("gamma out of range: " + g);
      }
      return serializeCommand("tune_gamma", fmtFloat(g));
    },
    tuneReset: function () { return serializeCommand("tune_reset"); },
    tuneSave: function () { return serializeCommand("tune_save"); },
    tuneStatus: function () { return serializeCommand("tune_status"); },
    chipId: function () { return serializeCommand("chip_id"); },
    build: function () { return serializeCommand("build"); },
    lookStatus: function () { return serializeCommand("look_status"); },
    setIdentity: function () { return serializeCommand("tune_reset"); },
    revertSession: function (baseline) {
      return [
        serialize.tuneGain(baseline.gain_r, baseline.gain_g, baseline.gain_b),
        serialize.tuneGamma(baseline.gamma),
      ];
    },
  };

  var RE_PAINT = /^PAINT: mode=(off|solid|ramp|stops|card) target=(primary|secondary|both) rgb=(\d{1,3}),(\d{1,3}),(\d{1,3}) s=(\d+\.?\d*) v=(\d+\.?\d*) stops=(\d{1,2})$/;
  var RE_TUNE = /^TUNE: gain=(\d+\.?\d*),(\d+\.?\d*),(\d+\.?\d*) gamma=(\d+\.?\d*) slot=(\d+) type=(\S+)$/;
  var RE_SAVE = /^TUNE_SAVE: (ok|fail)$/;
  var RE_BAD = /^Bad command: (.*)$/;
  var RE_CHIP = /^[0-9A-F]{8}$/;
  var RE_BUILD = /^BUILD: version=(\S+) git=(\S+) epoch=(\S+) env=(\S+)$/;
  var RE_LOOK = /^LOOK: slot=(\d+) type=(\S+) sec=(inherit|\d+) env=(\S+)$/;

  function isEnvelopeMarker(line) {
    return line === "sbr{{" || line === "sberr[[" || line === "}}" || line === "]]";
  }

  function parseLine(line) {
    var m = RE_PAINT.exec(line);
    if (m) {
      var r = Number(m[3]);
      var g = Number(m[4]);
      var b = Number(m[5]);
      if (r > 255 || g > 255 || b > 255) return { kind: "malformed", line: line };
      return {
        kind: "paint", mode: m[1], target: m[2], r: r, g: g, b: b,
        s: Number(m[6]), v: Number(m[7]), stops: Number(m[8]),
      };
    }
    m = RE_TUNE.exec(line);
    if (m) {
      return {
        kind: "tune",
        gain_r: Number(m[1]), gain_g: Number(m[2]), gain_b: Number(m[3]),
        gamma: Number(m[4]), slot: Number(m[5]), type: m[6],
      };
    }
    m = RE_SAVE.exec(line);
    if (m) return { kind: m[1] === "ok" ? "save_ok" : "save_fail" };
    m = RE_BAD.exec(line);
    if (m) return { kind: "bad_command", command: m[1] };
    if (RE_CHIP.test(line)) return { kind: "chip_id", chip_id: line };
    m = RE_BUILD.exec(line);
    if (m) {
      return {
        kind: "build",
        version: m[1], git: m[2], epoch: m[3], env: m[4],
      };
    }
    if (line === "LOOK: empty") return { kind: "look_empty" };
    m = RE_LOOK.exec(line);
    if (m) {
      return {
        kind: "look",
        slot: Number(m[1]),
        type: m[2],
        sec: m[3] === "inherit" ? "inherit" : Number(m[3]),
        env: m[4],
      };
    }
    if (/^(PAINT:|TUNE:|TUNE_SAVE:|BUILD:|LOOK:|Bad command:)/.test(line)) {
      return { kind: "malformed", line: line };
    }
    return { kind: "chatter", line: line };
  }

  function createLineParser() {
    var buf = "";
    return {
      feed: function (chunk) {
        buf += chunk;
        var events = [];
        for (;;) {
          var cr = buf.indexOf("\r");
          var lf = buf.indexOf("\n");
          var cut;
          var skip;
          if (cr === -1 && lf === -1) break;
          if (cr !== -1 && (lf === -1 || cr < lf)) {
            cut = cr;
            skip = (buf[cr + 1] === "\n") ? 2 : 1;
          } else {
            cut = lf;
            skip = 1;
          }
          var line = buf.slice(0, cut);
          buf = buf.slice(cut + skip);
          if (line.trim().length === 0) continue;
          var trimmed = line.trim();
          if (isEnvelopeMarker(trimmed)) continue;
          events.push(parseLine(trimmed));
        }
        return events;
      },
      pending: function () { return buf; },
    };
  }

  function profileByChip(chip) {
    var keys = Object.keys(ENV_PROFILES);
    for (var i = 0; i < keys.length; i++) {
      if (ENV_PROFILES[keys[i]].chip_id === chip) return ENV_PROFILES[keys[i]];
    }
    return null;
  }

  function resolveDeviceProfile(input) {
    input = input || {};
    var chip = input.chip_id || null;
    var lookEnv = input.look_env || null;
    var buildEnv = input.build_env || null;
    var envKey = lookEnv || buildEnv;
    var byEnv = envKey && ENV_PROFILES[envKey] ? ENV_PROFILES[envKey] : null;
    var byChip = chip ? profileByChip(chip) : null;
    var match = null;
    if (byEnv && byChip && byEnv.env === byChip.env) match = byEnv;
    else if (byChip && (!lookEnv || lookEnv === byChip.env)) match = byChip;
    else if (byEnv && (!chip || chip === byEnv.chip_id)) match = byEnv;

    if (match) {
      return {
        identity_status: "verified",
        chip_id: chip || match.chip_id,
        build_environment: buildEnv || match.env,
        look_env: lookEnv || match.env,
        primary_led_count: match.primary_led_count,
        secondary_led_count: match.secondary_led_count,
        both_scale_enabled: match.both_scale_enabled,
        both_scale: match.both_scale,
        slot15_supported: match.slot15_supported,
        look_backend: match.look_backend,
        env: match.env,
        exact_parity: true,
        active_primary_look: input.active_primary_look != null
          ? input.active_primary_look : "unknown",
        active_secondary_look: input.active_secondary_look != null
          ? input.active_secondary_look : "unknown",
      };
    }
    return {
      identity_status: "unverified",
      chip_id: chip,
      build_environment: buildEnv,
      look_env: lookEnv,
      primary_led_count: input.primary_led_count != null
        ? input.primary_led_count : null,
      secondary_led_count: input.secondary_led_count != null
        ? input.secondary_led_count : null,
      both_scale_enabled: false,
      both_scale: null,
      slot15_supported: null,
      look_backend: null,
      env: envKey || null,
      exact_parity: false,
      active_primary_look: input.active_primary_look != null
        ? input.active_primary_look : "unknown",
      active_secondary_look: input.active_secondary_look != null
        ? input.active_secondary_look : "unknown",
    };
  }

  function emptyKnowledge() {
    return {
      deviceProfile: null,
      confirmed: { paint: null, tune: null },
      confirmedSeq: { paint: 0, tune: 0 },
      draft: { paint: {}, tune: {} },
      pending: null,
      slot15Content: { status: "unknown" },
      sessionBaseline: null,
      persistence: "unknown",
      activeLookPrimary: "unknown",
      activeLookSecondary: "unknown",
      preview: "draft",
      paintMayBeActive: false,
      outputStateUnknown: false,
      lastError: null,
      needsResync: false,
      lastShutdown: null,
    };
  }

  function initialState(supported) {
    var s = emptyKnowledge();
    s.connection = supported ? "disconnected" : "unsupported";
    return s;
  }

  function tuneEquals(a, b) {
    return !!(a && b &&
      a.gain_r === b.gain_r && a.gain_g === b.gain_g &&
      a.gain_b === b.gain_b && a.gamma === b.gamma);
  }

  function maybeReady(s) {
    if (s.connection === "hydrating" && s.confirmed.paint &&
        (s.confirmed.tune || s.hydrateTuneOptional)) {
      s.connection = "ready";
    }
    return s;
  }

  function applyLook(s, look) {
    if (!look) return;
    s.activeLookPrimary = look.slot;
    s.activeLookSecondary = look.sec;
    if (s.deviceProfile) {
      s.deviceProfile.active_primary_look = look.slot;
      s.deviceProfile.active_secondary_look = look.sec;
    }
  }

  function reduce(state, action) {
    var s = clone(state);
    var seq;
    switch (action.type) {
      case "REQUEST_PORT":
        if (s.connection === "unsupported") return s;
        s.connection = "requesting";
        s.lastError = null;
        return s;
      case "PORT_OPENING":
        s.connection = "opening";
        return s;
      case "PORT_OPEN_FAILED":
        s.connection = "error";
        s.lastError = action.error || "port open failed";
        return s;
      case "REQUEST_CANCELLED":
        s.connection = "disconnected";
        return s;
      case "PROFILE_START": {
        var keptConn = "profiling";
        var next = emptyKnowledge();
        next.connection = keptConn;
        next.hydrateTuneOptional = !!action.tuneOptional;
        /* Profiling begins an evidence transaction. Until every required
         * status reply succeeds, physical output state remains unknown even
         * though stale confirmed values are discarded. */
        next.needsResync = true;
        next.outputStateUnknown = true;
        next.paintMayBeActive = s.paintMayBeActive ||
          !!(s.confirmed.paint && s.confirmed.paint.mode !== "off");
        next.lastError = OUTPUT_UNKNOWN;
        return next;
      }
      case "PROFILE_RESOLVED":
        s.deviceProfile = action.profile;
        if (action.look) applyLook(s, action.look);
        if (s.connection === "profiling") s.connection = "hydrating";
        return s;
      case "HYDRATE_START":
        s.connection = "hydrating";
        s.confirmed = { paint: null, tune: null };
        s.confirmedSeq = { paint: 0, tune: 0 };
        s.draft = { paint: {}, tune: {} };
        s.slot15Content = { status: "unknown" };
        s.sessionBaseline = null;
        s.persistence = "unknown";
        s.needsResync = true;
        s.lastError = OUTPUT_UNKNOWN;
        s.outputStateUnknown = true;
        if (action.tuneOptional != null) s.hydrateTuneOptional = !!action.tuneOptional;
        return s;
      case "DEVICE_PAINT":
        seq = action.seq == null ? s.confirmedSeq.paint + 1 : action.seq;
        if (seq < s.confirmedSeq.paint) return s;
        s.confirmedSeq.paint = seq;
        s.confirmed.paint = clone(action.paint);
        s.paintMayBeActive = action.paint.mode !== "off";
        if (action.paint.mode === "off") s.outputStateUnknown = false;
        return maybeReady(s);
      case "DEVICE_TUNE": {
        seq = action.seq == null ? s.confirmedSeq.tune + 1 : action.seq;
        if (seq < s.confirmedSeq.tune) return s;
        s.confirmedSeq.tune = seq;
        var tune = {
          gain_r: action.tune.gain_r,
          gain_g: action.tune.gain_g,
          gain_b: action.tune.gain_b,
          gamma: action.tune.gamma,
        };
        s.confirmed.tune = tune;
        var by = action.established_by;
        var establishes = (
          by === "tune_gain" || by === "tune_gamma" || by === "tune_reset"
        );
        if (establishes) {
          s.slot15Content = {
            status: "known-this-session",
            gain_r: tune.gain_r,
            gain_g: tune.gain_g,
            gain_b: tune.gain_b,
            gamma: tune.gamma,
            established_by: by,
          };
          if (!s.sessionBaseline) s.sessionBaseline = clone(tune);
          if (s.persistence === "saved" || s.persistence === "clean" ||
              s.persistence === "unknown") {
            s.persistence = "dirty";
          }
        }
        /* tune_status never establishes LUT knowledge or a session baseline. */
        return maybeReady(s);
      }
      case "SAVE_START":
        s.persistence = "saving";
        return s;
      case "DEVICE_SAVE_OK":
        if (s.slot15Content.status === "known-this-session") {
          s.slot15Content.established_by = "session_save";
        }
        s.persistence = "saved";
        return s;
      case "DEVICE_SAVE_FAIL":
        s.persistence = "save-failed";
        return s;
      case "DRAFT_PAINT":
        s.draft.paint = Object.assign({}, s.draft.paint, action.values);
        return s;
      case "DRAFT_TUNE":
        s.draft.tune = Object.assign({}, s.draft.tune, action.values);
        return s;
      case "DRAFT_CLEAR_PAINT":
        s.draft.paint = {};
        return s;
      case "DRAFT_CLEAR_TUNE":
        s.draft.tune = {};
        return s;
      case "PENDING":
        s.pending = action.pending || { cmd: action.cmd, expect: action.expect };
        return s;
      case "PENDING_CLEAR":
        s.pending = null;
        return s;
      case "COMMAND_TIMEOUT":
        s.lastError = "timeout: " + (action.command || "");
        s.needsResync = true;
        s.pending = null;
        if (action.priorityStop) {
          s.outputStateUnknown = true;
          s.lastError = OUTPUT_UNKNOWN;
        }
        return s;
      case "COMMAND_REJECTED":
        s.lastError = "rejected: " + (action.command || "");
        s.pending = null;
        return s;
      case "COMMAND_SEQUENCE_PARTIAL":
        s.lastError = "partial " + (action.sequence || "command") +
          " sequence: " + (action.confirmedCount || 0) + " command(s) confirmed";
        s.needsResync = true;
        s.outputStateUnknown = true;
        s.pending = null;
        return s;
      case "OUTPUT_STATE_UNKNOWN":
        s.outputStateUnknown = true;
        s.lastError = OUTPUT_UNKNOWN;
        return s;
      case "RECOVERY_FAILED":
        s.needsResync = true;
        s.outputStateUnknown = true;
        s.lastError = "recovery failed: " + (action.detail || OUTPUT_UNKNOWN);
        return s;
      case "RESYNC_DONE":
        if (!s.confirmed.paint) return s;
        s.needsResync = false;
        s.outputStateUnknown = false;
        s.lastError = null;
        return s;
      case "DEVICE_LOST":
        s.connection = "device-lost";
        s.needsResync = true;
        s.outputStateUnknown = true;
        s.lastError = OUTPUT_UNKNOWN;
        return s;
      case "DISCONNECTED":
        Object.assign(s, emptyKnowledge());
        s.connection = "disconnected";
        s.lastShutdown = action.shutdown || null;
        if (action.paintStopped) s.paintMayBeActive = false;
        else s.paintMayBeActive = !!action.paintMayBeActive;
        if (action.outputUnknown) {
          s.outputStateUnknown = true;
          s.lastError = OUTPUT_UNKNOWN;
        }
        return s;
      case "PARSER_ERROR":
        s.lastError = "parser: " + (action.detail || "");
        s.needsResync = true;
        return s;
      case "LOOK_STATUS":
        applyLook(s, action.look);
        return s;
      default:
        return s;
    }
  }

  function controlsEnabled(state) {
    return state.connection === "ready" && !state.needsResync &&
      !state.outputStateUnknown;
  }

  function identityAction(state) {
    return state.sessionBaseline ? "revert_session" : "set_identity";
  }

  function showTune(profile) {
    return !!(profile && profile.slot15_supported === true);
  }

  function showBothScale(profile) {
    return !!(profile && profile.both_scale_enabled === true);
  }

  function canClaimExactParity(profile) {
    return !!(profile && profile.identity_status === "verified" &&
      profile.exact_parity);
  }

  function resolveEffectiveLook(state, channel) {
    state = state || initialState(true);
    channel = channel === "secondary" ? "secondary" : "primary";
    var reported = channel === "secondary"
      ? state.activeLookSecondary
      : state.activeLookPrimary;

    if (channel === "secondary" && reported === "inherit") {
      var inherited = resolveEffectiveLook(state, "primary");
      return {
        relation: "inherit",
        reported: "inherit",
        effectiveKnown: inherited.effectiveKnown,
        effectiveSlot: inherited.effectiveKnown ? inherited.effectiveSlot : null,
        inheritedFrom: "primary",
      };
    }

    if (reported === "unknown" || reported === "inherit" || reported == null) {
      return {
        relation: "unknown",
        reported: reported == null ? "unknown" : reported,
        effectiveKnown: false,
        effectiveSlot: null,
        inheritedFrom: null,
      };
    }

    return {
      relation: "direct",
      reported: reported,
      effectiveKnown: true,
      effectiveSlot: reported,
      inheritedFrom: null,
    };
  }

  function previewFraming(state, channel, resolvedLook) {
    var slotKnown = state.slot15Content &&
      state.slot15Content.status === "known-this-session";
    var look = resolvedLook || resolveEffectiveLook(state, channel);
    var slot15Knowledge = slotKnown ? "known-this-session" : "unknown";
    if (!look.effectiveKnown || !slotKnown) {
      return {
        kind: "pre_lut",
        label: PRE_LUT_LABEL,
        applyLut: false,
        reason: !look.effectiveKnown ? "effective_look_unknown" : "slot15_unknown",
        lookResolution: look,
        slot15Knowledge: slot15Knowledge,
      };
    }
    if (look.effectiveSlot === USER_SLOT) {
      return {
        kind: "device_effective",
        label: "Device Effective",
        applyLut: true,
        reason: null,
        lookResolution: look,
        slot15Knowledge: slot15Knowledge,
      };
    }
    return {
      kind: "simulate_session",
      label: "Simulate Known Session Tune",
      applyLut: true,
      reason: null,
      lookResolution: look,
      slot15Knowledge: slot15Knowledge,
    };
  }

  /* Resolve one channel's complete Stage truth in one place. Rendering and
   * inspection must consume the returned pixels instead of independently
   * choosing pre/post buffers. Source and transform are deliberately separate:
   * a browser-generated stimulus may still use a locally modelled transform. */
  function stageFrame(input) {
    input = input || {};
    var state = input.state || initialState(true);
    var channel = input.channel === "secondary" ? "secondary" : "primary";
    var lookResolution = resolveEffectiveLook(state, channel);
    var framing = previewFraming(state, channel, lookResolution);
    var stimulus = clone(input.paint);
    var requestedTune = Object.assign({}, identityTune(), input.tune || {});
    var tuneDraft = state.draft && state.draft.tune ? state.draft.tune : {};
    var hasTuneDraft = Object.keys(tuneDraft).length > 0;
    var slotTune = state.slot15Content || {};
    var hasKnownTune = slotTune.status === "known-this-session" &&
      [slotTune.gain_r, slotTune.gain_g, slotTune.gain_b, slotTune.gamma].every(function (value) {
        return typeof value === "number" && Number.isFinite(value);
      });
    var knownTune = hasKnownTune ? {
      gain_r: slotTune.gain_r,
      gain_g: slotTune.gain_g,
      gain_b: slotTune.gain_b,
      gamma: slotTune.gamma,
    } : null;
    /* A device/session claim always renders the exact tune held by state. An
     * arbitrary caller-supplied tune may only drive an explicitly local draft. */
    var tune = !hasTuneDraft && framing.applyLut && knownTune
      ? Object.assign({}, knownTune)
      : requestedTune;
    var framingApplyLut = framing.applyLut && !!knownTune;
    var requestedSimulation = !!input.simulate_draft && !framing.applyLut;
    var applyDraftSimulation = requestedSimulation && hasTuneDraft;
    var applyLut = applyDraftSimulation || (hasTuneDraft && framing.applyLut) || framingApplyLut;
    var selection = applyLut ? "post" : "pre";
    var rendered = renderChannel(stimulus, tune, channel, {
      n: input.n,
      both_scale_enabled: !!input.both_scale_enabled,
      both_scale: input.both_scale,
    });

    /* Paint provenance cannot be promoted from DOM equality. Outside the local
     * fallback, use conservative wording that remains true for confirmed,
     * pending and locally edited control values. */
    var source = input.local_stimulus ? {
      kind: "local_stimulus",
      label: "Local stimulus",
      qualifier: input.source_in_flight
        ? "command sequence in progress · local draft retained"
        : "browser-generated · nothing sent",
    } : {
      kind: "current_paint_controls",
      label: "Current paint controls",
      qualifier: "browser-rendered · device output not claimed",
    };

    var transform;
    var simulation = false;
    if (hasTuneDraft && applyLut) {
      simulation = true;
      transform = {
        kind: "local_draft_simulated",
        label: "Local draft simulated",
        qualifier: framing.kind === "device_effective"
          ? "browser LUT · device confirmation may be partial or pending"
          : framing.kind === "simulate_session"
            ? "unsent browser LUT · active device look is not modelled"
            : "unsent browser LUT · not device state",
      };
    } else if (framing.kind === "device_effective" && framingApplyLut) {
      transform = {
        kind: "device_confirmed_tune",
        label: "Device-confirmed tune",
        qualifier: "browser parity model · LUT nodes not read back",
      };
    } else if (framing.kind === "simulate_session" && framingApplyLut) {
      simulation = true;
      transform = {
        kind: "known_session_simulated",
        label: "Known session tune simulated",
        qualifier: "browser parity model · active device look is not modelled",
      };
    } else {
      transform = {
        kind: "reference_pre_lut",
        label: "Reference / pre-LUT",
        qualifier: framing.reason === "slot15_unknown"
          ? "slot-15 contents unknown · no correction applied"
          : "active look unknown · no correction applied",
      };
    }

    var targeted = !!(rendered.pre || rendered.post);
    var bothScaleApplied = targeted && stimulus && stimulus.target === "both" &&
      !!input.both_scale_enabled;
    source.pattern = stimulus ? stimulus.mode : null;
    source.target = stimulus ? stimulus.target : null;
    source.applied = targeted;

    return {
      channel: channel,
      n: input.n,
      stimulus: stimulus,
      tune: selection === "post" ? tune : null,
      source: source,
      transform: transform,
      framingKind: framing.kind,
      framingReason: framing.reason,
      lookResolution: lookResolution,
      slot15Knowledge: framing.slot15Knowledge,
      renderContext: {
        bothScaleApplied: bothScaleApplied,
        bothScale: bothScaleApplied
          ? (input.both_scale != null ? input.both_scale : BOTH_SCALE)
          : 1.0,
      },
      simulationAvailable: !framingApplyLut,
      simulation: simulation,
      selection: selection,
      pixels: selection === "post" ? rendered.post : rendered.pre,
      label: "Source: " + source.label + " · Transform: " + transform.label,
      qualifier: source.qualifier + " · " + transform.qualifier,
    };
  }

  var STAGE_BASIS_REASON_ORDER = [
    "source_provenance", "source_pattern", "source_targeting",
    "correction_provenance", "preview_selection", "look_relationship",
    "effective_look", "slot15_knowledge", "applied_tune", "render_scale",
  ];

  function sameJson(a, b) {
    return JSON.stringify(a) === JSON.stringify(b);
  }

  function compareStageOutput(primary, secondary) {
    if (!primary || !secondary || !primary.pixels || !secondary.pixels) {
      return {
        status: "unavailable",
        primaryLedCount: primary ? primary.n : null,
        secondaryLedCount: secondary ? secondary.n : null,
        sharedLedCount: 0,
        differingLedCount: 0,
        unmatchedLedCount: 0,
        firstDifferingLed: null,
        reasons: ["frame_unavailable"],
      };
    }

    var shared = Math.min(primary.n, secondary.n);
    var differing = 0;
    var first = null;
    for (var led = 0; led < shared; led++) {
      var offset = led * 3;
      if (primary.pixels[offset] !== secondary.pixels[offset] ||
          primary.pixels[offset + 1] !== secondary.pixels[offset + 1] ||
          primary.pixels[offset + 2] !== secondary.pixels[offset + 2]) {
        differing++;
        if (first == null) first = led;
      }
    }

    var unmatched = Math.abs(primary.n - secondary.n);
    var reasons = [];
    if (unmatched) reasons.push("led_count");
    if (differing) reasons.push("pixel_values");
    return {
      status: reasons.length ? "differ" : "match",
      primaryLedCount: primary.n,
      secondaryLedCount: secondary.n,
      sharedLedCount: shared,
      differingLedCount: differing,
      unmatchedLedCount: unmatched,
      firstDifferingLed: first,
      reasons: reasons,
    };
  }

  function stageBasisReasons(primary, secondary) {
    var checks = {
      source_provenance: primary.source.kind !== secondary.source.kind,
      source_pattern: !sameJson(primary.stimulus, secondary.stimulus),
      source_targeting: primary.source.applied !== secondary.source.applied ||
        primary.source.target !== secondary.source.target,
      correction_provenance: primary.transform.kind !== secondary.transform.kind,
      preview_selection: primary.selection !== secondary.selection ||
        primary.simulation !== secondary.simulation,
      look_relationship: primary.lookResolution.relation !== secondary.lookResolution.relation,
      effective_look: primary.lookResolution.effectiveKnown !== secondary.lookResolution.effectiveKnown ||
        primary.lookResolution.effectiveSlot !== secondary.lookResolution.effectiveSlot,
      slot15_knowledge: primary.slot15Knowledge !== secondary.slot15Knowledge,
      applied_tune: !sameJson(primary.tune, secondary.tune),
      render_scale: !sameJson(primary.renderContext, secondary.renderContext),
    };
    return STAGE_BASIS_REASON_ORDER.filter(function (reason) { return checks[reason]; });
  }

  function compareStageFrames(primary, secondary) {
    var output = compareStageOutput(primary, secondary);
    if (!primary || !secondary) {
      return {
        output: output,
        basis: { status: "unavailable", reasons: ["frame_unavailable"] },
      };
    }
    var reasons = stageBasisReasons(primary, secondary);
    return {
      output: output,
      basis: { status: reasons.length ? "differ" : "match", reasons: reasons },
    };
  }

  function inspectStageFrame(frame, selectedLed) {
    if (!frame || !frame.pixels) return { kind: "unavailable" };
    if (!Number.isInteger(selectedLed) || selectedLed < 0) return { kind: "invalid" };
    if (selectedLed >= frame.n) return { kind: "not_present", n: frame.n };
    var offset = selectedLed * 3;
    var rgb16 = frame.pixels.slice(offset, offset + 3);
    return {
      kind: "value",
      rgb16: rgb16,
      rgb8: rgb16.map(function (value) { return value >> 8; }),
    };
  }

  function isMutationCommand(cmd) {
    return !!MUTATION_COMMANDS[cmd];
  }

  function expectFor(cmd) {
    if (cmd === "tune_save") return "save";
    if (cmd.indexOf("tune") === 0) return "tune";
    if (cmd === "chip_id") return "chip_id";
    if (cmd === "build") return "build";
    if (cmd === "look_status") return "look";
    return "paint";
  }

  function createCommandQueue(opts) {
    opts = opts || {};
    var sendFn = opts.send;
    var timeoutMs = opts.timeoutMs == null ? COMMAND_TIMEOUT_MS : opts.timeoutMs;
    var safetyTimeoutMs = opts.safetyTimeoutMs == null
      ? SAFETY_TIMEOUT_MS : opts.safetyTimeoutMs;
    var onSettle = opts.onSettle || function () {};
    var now = opts.now || function () { return Date.now(); };
    var setTimer = opts.setTimer || setTimeout;
    var clearTimer = opts.clearTimer || clearTimeout;
    var autoRequery = opts.autoRequery !== false;

    var queue = [];
    var inFlight = null;
    var nextId = 1;

    function armTimer(entry) {
      var ms = entry.priority ? safetyTimeoutMs : timeoutMs;
      entry.timer = setTimer(function () {
        if (inFlight === entry) {
          inFlight = null;
          onSettle({
            id: entry.id,
            cmd: entry.cmd,
            line: entry.line,
            outcome: "timeout",
            priority: !!entry.priority,
            warning: entry.priority ? OUTPUT_UNKNOWN : null,
          });
          pump();
        }
      }, ms);
    }

    function afterSend(entry, err) {
      if (inFlight !== entry) return;
      entry.writeCompleted = true;
      if (err) {
        inFlight = null;
        onSettle({
          id: entry.id, cmd: entry.cmd, line: entry.line,
          outcome: "write-error", error: String(err), priority: !!entry.priority,
        });
        pump();
        return;
      }
      if (entry.supersededAfterWrite) {
        inFlight = null;
        onSettle({
          id: entry.id, cmd: entry.cmd, line: entry.line,
          outcome: "superseded", priority: !!entry.priority,
        });
        pump();
        return;
      }
      armTimer(entry);
    }

    function pump() {
      if (inFlight || queue.length === 0) return;
      var entry = queue.shift();
      inFlight = entry;
      entry.sentAt = now();
      try {
        var p = sendFn(entry.line);
        if (p && typeof p.then === "function") {
          p.then(function () { afterSend(entry, null); })
           .catch(function (err) { afterSend(entry, err); });
        } else {
          afterSend(entry, null);
        }
      } catch (err) {
        afterSend(entry, err);
      }
    }

    function makeEntry(cmd, line, extra) {
      extra = extra || {};
      return {
        id: nextId++,
        cmd: cmd,
        line: line,
        expect: extra.expect || expectFor(cmd),
        class: extra.supersessionClass || SUPERSESSION_COMMANDS[cmd] || null,
        priority: !!extra.priority,
        established_by: extra.established_by || null,
        timer: null,
        sentAt: null,
        writeCompleted: false,
        supersededAfterWrite: false,
      };
    }

    return {
      enqueue: function (cmd, line, extra) {
        extra = extra || {};
        if (extra.supersessionClass || SUPERSESSION_COMMANDS[cmd]) {
          var cls = extra.supersessionClass || SUPERSESSION_COMMANDS[cmd];
          queue = queue.filter(function (e) { return e.class !== cls; });
        }
        var entry = makeEntry(cmd, line, extra);
        queue.push(entry);
        pump();
        return entry.id;
      },
      enqueuePriorityStop: function () {
        var retained = [];
        queue.forEach(function (queuedEntry) {
          if (!isMutationCommand(queuedEntry.cmd) || queuedEntry.priority) {
            retained.push(queuedEntry);
            return;
          }
          onSettle({
            id: queuedEntry.id, cmd: queuedEntry.cmd, line: queuedEntry.line,
            outcome: "superseded", priority: false,
          });
        });
        queue = retained;
        var entry = makeEntry("paint", serialize.paint("off"), {
          priority: true,
          expect: "paint",
        });
        if (inFlight && !inFlight.writeCompleted) {
          inFlight.supersededAfterWrite = true;
          queue.unshift(entry);
          return entry.id;
        }
        if (inFlight) {
          var superseded = inFlight;
          if (superseded.timer) clearTimer(superseded.timer);
          inFlight = null;
          onSettle({
            id: superseded.id, cmd: superseded.cmd, line: superseded.line,
            outcome: "superseded", priority: !!superseded.priority,
          });
        }
        queue.unshift(entry);
        pump();
        return entry.id;
      },
      onEvent: function (ev) {
        if (!inFlight) return false;
        var e = inFlight;
        function settle(outcome) {
          if (e.timer) clearTimer(e.timer);
          inFlight = null;
          var followUp = null;
          if (e.priority && outcome === "ok" && autoRequery) {
            followUp = serialize.paintStatus();
          }
          onSettle({
            id: e.id, cmd: e.cmd, line: e.line, outcome: outcome,
            event: ev, priority: !!e.priority, followUp: followUp,
            established_by: e.established_by,
            warning: (e.priority && outcome === "timeout") ? OUTPUT_UNKNOWN : null,
          });
          if (followUp) {
            queue.unshift(makeEntry("paint_status", followUp, { expect: "paint" }));
          }
          pump();
        }
        if (e.expect === "save") {
          if (ev.kind === "save_ok") { settle("ok"); return true; }
          if (ev.kind === "save_fail") { settle("fail"); return true; }
          return false;
        }
        if (ev.kind === "bad_command") { settle("rejected"); return true; }
        if (e.priority && e.cmd === "paint" && ev.kind === "paint") {
          if (ev.mode === "off") { settle("ok"); return true; }
          return false;
        }
        if (e.expect === "look" && (ev.kind === "look" || ev.kind === "look_empty")) {
          settle("ok");
          return true;
        }
        if (ev.kind === e.expect) { settle("ok"); return true; }
        return false;
      },
      flush: function () {
        if (inFlight && inFlight.timer) clearTimer(inFlight.timer);
        queue.forEach(function (e) {
          if (e.timer) clearTimer(e.timer);
        });
        queue = [];
        inFlight = null;
      },
      depth: function () { return queue.length + (inFlight ? 1 : 0); },
      queuedCmds: function () { return queue.map(function (e) { return e.cmd; }); },
      inFlightCmd: function () { return inFlight ? inFlight.cmd : null; },
      inFlightPriority: function () { return !!(inFlight && inFlight.priority); },
    };
  }

  function buildSnapshot(state, extra) {
    extra = extra || {};
    var p = state.confirmed.paint;
    var t = state.confirmed.tune;
    var cmds = [];
    if (t && state.slot15Content.status === "known-this-session") {
      cmds.push(serialize.tuneGain(t.gain_r, t.gain_g, t.gain_b));
      cmds.push(serialize.tuneGamma(t.gamma));
    }
    if (p) {
      cmds.push(serialize.paintTarget(p.target));
      if (p.stops && p.stops.length) cmds.push(serialize.paintStops(p.stops));
      if (p.mode === "solid") cmds.push(serialize.paintRgb(p.r, p.g, p.b));
      if (p.mode === "ramp") cmds.push(serialize.paintSv(p.s, p.v));
      cmds.push(serialize.paint(p.mode));
    }
    return {
      kind: "colourlab-session",
      version: 1,
      captured_at: extra.captured_at || new Date().toISOString(),
      deviceProfile: state.deviceProfile,
      paint: p,
      tune: t,
      slot15Content: state.slot15Content,
      sessionBaseline: state.sessionBaseline,
      persistence: state.persistence,
      reproduce: cmds,
    };
  }

  function runQueueScript(req) {
    var settled = [];
    var sent = [];
    var now = 0;
    var timers = [];
    var holdResolvers = [];
    var holdSends = !!req.holdSends;
    var q = createCommandQueue({
      send: function (line) {
        sent.push(line);
        if (!holdSends) return;
        return new Promise(function (resolve) {
          holdResolvers.push(resolve);
        });
      },
      now: function () { return now; },
      setTimer: function (fn, ms) {
        var id = timers.length;
        timers.push({ fn: fn, due: now + ms, cleared: false });
        return id;
      },
      clearTimer: function (id) {
        if (timers[id]) timers[id].cleared = true;
      },
      onSettle: function (info) { settled.push(info); },
      timeoutMs: req.timeoutMs,
      safetyTimeoutMs: req.safetyTimeoutMs,
      autoRequery: req.autoRequery,
    });
    function fireDue() {
      timers.forEach(function (t) {
        if (!t.cleared && t.due <= now) {
          t.cleared = true;
          t.fn();
        }
      });
    }
    (req.steps || []).forEach(function (step) {
      if (step.enqueue) {
        q.enqueue(step.enqueue.cmd, step.enqueue.line, step.enqueue);
      }
      if (step.priorityStop) q.enqueuePriorityStop();
      if (step.event) q.onEvent(step.event);
      if (step.releaseSend) {
        holdResolvers.splice(0).forEach(function (r) { r(); });
      }
      if (step.advance != null) {
        now += step.advance;
        fireDue();
      }
      if (step.flush) q.flush();
    });
    return {
      sent: sent,
      settled: settled,
      depth: q.depth(),
      queued: q.queuedCmds(),
      inFlight: q.inFlightCmd(),
    };
  }

  function classifyDisconnectShutdown(opts) {
    opts = opts || {};
    var outcome = opts.stopOutcome == null ? null : String(opts.stopOutcome);
    var mode = opts.paintModeFromReply == null ? null : String(opts.paintModeFromReply);
    var hadActive = !!opts.hadActivePaint;
    var inFlight = !!opts.inFlightAtStart;
    if (outcome === "ok" && mode === "off") {
      return { claim: "confirmed-off", paintStopped: true, outputUnknown: false };
    }
    if (outcome === "timeout" || outcome === "write-error" ||
        outcome === "rejected" || outcome === "fail") {
      return { claim: "unknown", paintStopped: false, outputUnknown: true };
    }
    /* Stale confirmed paint=off is not a this-turn safe-shutdown claim. */
    if (!hadActive && !inFlight && outcome == null) {
      return { claim: "already-idle", paintStopped: true, outputUnknown: false };
    }
    return { claim: "unknown", paintStopped: false, outputUnknown: true };
  }

  function classifyPersistLeaveState(opts) {
    opts = opts || {};
    var pre = opts.preTestLutStatus || "unknown";
    var leave = opts.leaveAction || "none";
    var saved = opts.savedTune || null;
    var reboot = opts.rebootResult || null;
    var knowable = pre === "known-this-session";
    if (leave === "prior-restored") {
      if (!knowable) {
        return {
          claim: "invalid-restore",
          restored: false,
          priorReconstructable: false,
          leaveState: "unknown",
          note: "boot TUNE is not restoration authority",
          savedTune: saved,
          rebootResult: reboot,
        };
      }
      return {
        claim: "prior-restored",
        restored: true,
        priorReconstructable: true,
        leaveState: "prior-session-snapshot",
        note: "rewrote the known-this-session snapshot",
        savedTune: saved,
        rebootResult: reboot,
      };
    }
    if (leave === "identity-saved") {
      return {
        claim: "identity-saved",
        restored: false,
        priorReconstructable: knowable,
        leaveState: "identity",
        note: knowable
          ? "overwrote with identity; prior snapshot was knowable but not rewritten"
          : "prior LUT could not be reconstructed; left identity",
        savedTune: saved,
        rebootResult: reboot,
      };
    }
    if (leave === "test-curve-left") {
      return {
        claim: "test-curve-left",
        restored: false,
        priorReconstructable: knowable,
        leaveState: "verification-curve",
        note: "verification curve remains in slot 15 — not a clean hardware leave-state",
        savedTune: saved,
        rebootResult: reboot,
      };
    }
    return {
      claim: "could-not-reconstruct",
      restored: false,
      priorReconstructable: false,
      leaveState: "unknown",
      note: "boot TUNE is not LUT knowledge",
      savedTune: saved,
      rebootResult: reboot,
    };
  }

  function dispatch(req) {
    req = req || {};
    switch (req.op) {
      case "constants":
        return {
          MAX_STOPS: MAX_STOPS,
          CARD_REGIONS: CARD_REGIONS,
          BOTH_SCALE: BOTH_SCALE,
          GAIN_MIN: GAIN_MIN,
          GAIN_MAX: GAIN_MAX,
          GAMMA_MIN: GAMMA_MIN,
          GAMMA_MAX: GAMMA_MAX,
          PAINT_STOPS_MAX_CHARS: PAINT_STOPS_MAX_CHARS,
          SAFETY_TIMEOUT_MS: SAFETY_TIMEOUT_MS,
          COMMAND_TIMEOUT_MS: COMMAND_TIMEOUT_MS,
          USER_SLOT: USER_SLOT,
          COMMANDS: COMMANDS,
          COLOUR_LAB_COMMANDS: COLOUR_LAB_COMMANDS,
          PROFILING_COMMANDS: PROFILING_COMMANDS,
          ENV_PROFILES: ENV_PROFILES,
          CONNECTION_STATES: CONNECTION_STATES,
          PRE_LUT_LABEL: PRE_LUT_LABEL,
          OUTPUT_UNKNOWN: OUTPUT_UNKNOWN,
          DISCONNECT_WAIT_MS: DISCONNECT_WAIT_MS,
        };
      case "parse": {
        var parser = createLineParser();
        var events = [];
        (req.chunks || []).forEach(function (c) {
          events = events.concat(parser.feed(c));
        });
        return { events: events, pending: parser.pending() };
      }
      case "parseLine":
        return parseLine(req.line);
      case "serialize":
        if (req.name) {
          return { line: serializeCommand(req.name, req.data) };
        }
        throw new Error("serialize requires name");
      case "serializeNamed": {
        var fn = serialize[req.fn];
        if (!fn) throw new Error("no serializer " + req.fn);
        var line = fn.apply(null, req.args || []);
        return { line: line };
      }
      case "render": {
        var options = {
          n: req.n,
          both_scale_enabled: !!req.both_scale_enabled,
          both_scale: req.both_scale,
        };
        var both = renderBoth(req.paint, req.tune, options);
        return {
          primary_pre: both.primary.pre,
          primary_post: both.primary.post,
          secondary_pre: both.secondary.pre,
          secondary_post: both.secondary.post,
        };
      }
      case "curve": {
        var nodes = buildRgb1d(req.tune);
        return {
          x: nodes.x, r: nodes.r, g: nodes.g, b: nodes.b,
          valid: rgb1dValid(nodes),
        };
      }
      case "initialState":
        return initialState(req.supported !== false);
      case "reduce": {
        var st = req.state || initialState(true);
        (req.actions || [req.action]).forEach(function (a) {
          if (a) st = reduce(st, a);
        });
        return st;
      }
      case "identityAction":
        return { action: identityAction(req.state) };
      case "resolveEffectiveLook":
        return resolveEffectiveLook(req.state, req.channel || "primary");
      case "previewFraming":
        return previewFraming(req.state, req.channel || "primary");
      case "stageFrame":
        return stageFrame(req);
      case "compareStageFrames":
        return compareStageFrames(req.primary, req.secondary);
      case "inspectStageFrame":
        return inspectStageFrame(req.frame, req.selectedLed);
      case "resolveProfile":
        return resolveDeviceProfile(req);
      case "queue":
        return runQueueScript(req);
      case "snapshot":
        return buildSnapshot(req.state, req.extra || {});
      case "controlsEnabled":
        return { enabled: controlsEnabled(req.state) };
      case "showTune":
        return { show: showTune(req.profile) };
      case "showBothScale":
        return { show: showBothScale(req.profile) };
      case "classifyDisconnectShutdown":
        return classifyDisconnectShutdown(req);
      case "classifyPersistLeaveState":
        return classifyPersistLeaveState(req);
      default:
        throw new Error("unknown op: " + req.op);
    }
  }

  return {
    MAX_STOPS: MAX_STOPS,
    CARD_REGIONS: CARD_REGIONS,
    BOTH_SCALE: BOTH_SCALE,
    GAIN_MIN: GAIN_MIN,
    GAIN_MAX: GAIN_MAX,
    GAMMA_MIN: GAMMA_MIN,
    GAMMA_MAX: GAMMA_MAX,
    RAMP_V: RAMP_V,
    DEFAULT_U8: DEFAULT_U8,
    USER_SLOT: USER_SLOT,
    PAINT_STOPS_MAX_CHARS: PAINT_STOPS_MAX_CHARS,
    SAFETY_TIMEOUT_MS: SAFETY_TIMEOUT_MS,
    COMMAND_TIMEOUT_MS: COMMAND_TIMEOUT_MS,
    GREYS: GREYS,
    GOLD: GOLD,
    PAINT_MODES: PAINT_MODES,
    PAINT_TARGETS: PAINT_TARGETS,
    COMMANDS: COMMANDS,
    COLOUR_LAB_COMMANDS: COLOUR_LAB_COMMANDS,
    PROFILING_COMMANDS: PROFILING_COMMANDS,
    ENV_PROFILES: ENV_PROFILES,
    CONNECTION_STATES: CONNECTION_STATES,
    PRE_LUT_LABEL: PRE_LUT_LABEL,
    OUTPUT_UNKNOWN: OUTPUT_UNKNOWN,
    DISCONNECT_WAIT_MS: DISCONNECT_WAIT_MS,
    hsv: hsv,
    region: region,
    cardRgb: cardRgb,
    pixel: pixel,
    sqTruncToU16: sqTruncToU16,
    satU16: satU16,
    curveU16: curveU16,
    buildRgb1d: buildRgb1d,
    rgb1dValid: rgb1dValid,
    lutLerp1d: lutLerp1d,
    renderChannel: renderChannel,
    renderBoth: renderBoth,
    identityTune: identityTune,
    fmtFloat: fmtFloat,
    serializeCommand: serializeCommand,
    serializeWire: serializeWire,
    serialize: serialize,
    parseLine: parseLine,
    createLineParser: createLineParser,
    isEnvelopeMarker: isEnvelopeMarker,
    resolveDeviceProfile: resolveDeviceProfile,
    initialState: initialState,
    reduce: reduce,
    controlsEnabled: controlsEnabled,
    identityAction: identityAction,
    showTune: showTune,
    showBothScale: showBothScale,
    canClaimExactParity: canClaimExactParity,
    resolveEffectiveLook: resolveEffectiveLook,
    previewFraming: previewFraming,
    stageFrame: stageFrame,
    compareStageFrames: compareStageFrames,
    inspectStageFrame: inspectStageFrame,
    isMutationCommand: isMutationCommand,
    createCommandQueue: createCommandQueue,
    buildSnapshot: buildSnapshot,
    classifyDisconnectShutdown: classifyDisconnectShutdown,
    classifyPersistLeaveState: classifyPersistLeaveState,
    dispatch: dispatch,
  };
}));
