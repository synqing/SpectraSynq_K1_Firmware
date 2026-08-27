(function () {
  "use strict";

  var CL = globalThis.ColourLab;
  var CA = globalThis.ColourLabAuthoring;
  if (!CL || !CA) throw new Error("Colour Lab production modules failed to load");

  var $ = function (id) { return document.getElementById(id); };
  var params = new URLSearchParams(location.search);
  var demo = params.get("demo");
  var previewFixture = params.get("preview") || params.get("stage");
  var mockAckDelay = Math.max(0, Number(params.get("ackDelay")) || 0);
  var mockFailCommand = params.get("failCommand");
  var serialOk = !!navigator.serial;
  var coreState = CL.initialState(serialOk);
  var parser = CL.createLineParser();
  var queue = null;
  var port = null;
  var reader = null;
  var writer = null;
  var readLoop = false;
  var waiters = {};
  var pendingPriority = null;
  var disconnecting = false;
  var transaction = null;
  var stageFrames = { primary: null, secondary: null };
  var selectedLed = 86;
  var pointerActive = false;
  var txCount = 0;
  var txTrace = [];
  var legacyForbiddenDetected = demo === "safety";
  var legacyRecoveryGeneration = legacyForbiddenDetected ? 1 : 0;
  var legacyRecoveryStopId = null;
  var legacyRecoveryOffGeneration = 0;
  var legacyRecoveryStatusGeneration = 0;
  var legacyRecoveryAwaitingStatusGeneration = 0;
  var stopStatusPending = false;
  var mockDevice = {
    paint: { kind: "paint", mode: "off", target: "both", r: 140, g: 140, b: 140, s: 1, v: 0.55, stops: [] },
    tune: { kind: "tune", gain_r: 1.25, gain_g: 1, gain_b: 0.9, gamma: 1.8 },
  };

  var app = {
    stimulus: "neutral",
    target: "both",
    view: "led",
    interpolation: "oklch",
    baseHue: 48,
    sourceDirty: true,
    tuneDirty: false,
    sourceRevision: 0,
    tuneRevision: 0,
    paletteStops: [],
  };

  function clamp(value, low, high) { return Math.max(low, Math.min(high, value)); }
  function finite(value) { return typeof value === "number" && Number.isFinite(value); }
  function u8(rgb) { return rgb.map(function (channel) { return Math.round(clamp(channel, 0, 255)); }); }
  function parseHex(value) {
    var match = /^#([0-9a-f]{6})$/i.exec(value);
    if (!match) throw new Error("invalid colour value");
    return [0, 2, 4].map(function (offset) { return parseInt(match[1].slice(offset, offset + 2), 16); });
  }
  function formatNumber(value) { return Number(value).toFixed(3); }

  function toast(message) {
    var element = $("toast");
    element.textContent = message;
    element.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(function () { element.classList.remove("show"); }, 2200);
  }

  function log(kind, text) {
    var line = new Date().toISOString() + " " + kind + " " + text;
    $("log").textContent += "\n" + line;
    $("log").scrollTop = $("log").scrollHeight;
  }

  function presetStops(baseHue) {
    var offsets = [0, -20, -40, -60];
    var saturation = [0.58, 0.92, 0.96, 0.82];
    var value = [1.00, 0.94, 0.72, 0.48];
    return offsets.map(function (offset, index) {
      return {
        position: [0, 0.34, 0.67, 1][index],
        rgb: u8(CA.hsvToRgb([baseHue + offset, saturation[index], value[index]])),
      };
    });
  }
  app.paletteStops = presetStops(app.baseHue);
  if (demo === "policy") {
    app.stimulus = "bounded";
    app.paletteStops = [
      { position: 0, rgb: [255, 250, 242] },
      { position: 0.34, rgb: [255, 195, 76] },
      { position: 0.67, rgb: [240, 104, 18] },
      { position: 1, rgb: [145, 21, 36] },
    ];
  }

  function tuneFromControls() {
    return {
      gain_r: Number($("gainR").value),
      gain_g: Number($("gainG").value),
      gain_b: Number($("gainB").value),
      gamma: Number($("gamma").value),
    };
  }

  function tuneValid(tune) {
    return finite(tune.gain_r) && tune.gain_r >= CL.GAIN_MIN && tune.gain_r <= CL.GAIN_MAX &&
      finite(tune.gain_g) && tune.gain_g >= CL.GAIN_MIN && tune.gain_g <= CL.GAIN_MAX &&
      finite(tune.gain_b) && tune.gain_b >= CL.GAIN_MIN && tune.gain_b <= CL.GAIN_MAX &&
      finite(tune.gamma) && tune.gamma >= CL.GAMMA_MIN && tune.gamma <= CL.GAMMA_MAX;
  }

  function compiledPalette() {
    return CA.compilePaintStops(app.paletteStops, {
      interpolation: app.interpolation,
      maxStops: CL.MAX_STOPS,
      comparisonSamples: 161,
    });
  }

  function singleHueStops() {
    return [
      { position: 0, rgb: u8(CA.hsvToRgb([app.baseHue, 0, 0.45])) },
      { position: 0.25, rgb: u8(CA.hsvToRgb([app.baseHue, 0.45, 0.72])) },
      { position: 0.5, rgb: u8(CA.hsvToRgb([app.baseHue, 1, 1])) },
      { position: 0.75, rgb: u8(CA.hsvToRgb([app.baseHue, 1, 0.48])) },
      { position: 1, rgb: [0, 0, 0] },
    ];
  }

  function isolatedChannelStops() {
    return [
      { position: 0 / 8, rgb: [0, 0, 0] },
      { position: 1 / 8, rgb: [255, 0, 0] },
      { position: 2 / 8, rgb: [0, 0, 0] },
      { position: 3 / 8, rgb: [0, 255, 0] },
      { position: 4 / 8, rgb: [0, 0, 0] },
      { position: 5 / 8, rgb: [0, 0, 255] },
      { position: 6 / 8, rgb: [0, 0, 0] },
      { position: 1, rgb: [0, 0, 0] },
    ];
  }

  function currentPaint(compiled) {
    if (app.stimulus === "solid") {
      return {
        mode: "solid", target: app.target,
        r: Number($("solidR").value), g: Number($("solidG").value), b: Number($("solidB").value),
        stops: [],
      };
    }
    if (app.stimulus === "bounded") {
      return { mode: "stops", target: app.target, stops: (compiled || compiledPalette()).paintStops };
    }
    if (app.stimulus === "card") return { mode: "card", target: app.target, stops: [] };
    if (app.stimulus === "rgb") {
      return { mode: "stops", target: app.target, stops: isolatedChannelStops().map(function (stop) { return stop.rgb; }) };
    }
    if (app.stimulus === "sv") {
      return { mode: "stops", target: app.target, stops: singleHueStops().map(function (stop) { return stop.rgb; }) };
    }
    return { mode: "stops", target: app.target, stops: [[0, 0, 0], [255, 255, 255]] };
  }

  function policyForCurrentSource() {
    if (app.stimulus === "bounded") {
      return CA.validateProductOutput(app.paletteStops, {
        interpolation: app.interpolation,
        maxStops: CL.MAX_STOPS,
        comparisonSamples: 161,
      });
    }
    if (app.stimulus === "solid") {
      return CA.validateProductPolicy([{
        position: 0,
        rgb: [Number($("solidR").value), Number($("solidG").value), Number($("solidB").value)],
      }], { interpolation: "rgb" });
    }
    if (app.stimulus === "neutral") {
      return CA.validateDiagnosticReference("neutral", [[0, 0, 0], [64, 64, 64], [128, 128, 128], [192, 192, 192], [255, 255, 255]]);
    }
    if (app.stimulus === "rgb") {
      var isolated = [];
      for (var value = 0; value <= 255; value += 17) isolated.push([value, 0, 0]);
      for (var green = 0; green <= 255; green += 17) isolated.push([0, green, 0]);
      for (var blue = 0; blue <= 255; blue += 17) isolated.push([0, 0, blue]);
      return CA.validateDiagnosticReference("isolated_rgb", isolated);
    }
    if (app.stimulus === "sv") {
      return CA.validateDiagnosticReference("single_hue", CA.samplePalette(singleHueStops(), 65, "hsv"));
    }
    var card = CL.GREYS.map(function (grey) { return [grey, grey, grey]; });
    card.push([255, 0, 0], [0, 255, 0], [0, 0, 255], CL.GOLD.slice());
    return CA.validateDiagnosticReference("k1_card", card);
  }

  function profile() { return coreState.deviceProfile; }
  function tuneSupportedByProfile() {
    var known = profile();
    return !known || CL.showTune(known);
  }
  function localN(which) {
    var known = profile();
    var count = known && (which === "secondary" ? known.secondary_led_count : known.primary_led_count);
    return Number.isInteger(count) && count > 0 ? count : 160;
  }
  function transportReady() {
    return !!queue && coreState.connection === "ready" &&
      !coreState.needsResync && !coreState.outputStateUnknown &&
      (!demo || demo === "transport") && !disconnecting;
  }

  function safetyForCurrentSource(paint, tune) {
    var deviceEvidenceRequired = !!queue && coreState.connection === "ready";
    var verified = !!(profile() && profile().identity_status === "verified");
    var serialisedLength;
    if (paint.mode === "stops") {
      try { serialisedLength = CL.serialize.paintStops(paint.stops).length; }
      catch (error) { serialisedLength = 999; }
    }
    return CA.validateDeviceSafety({
      mode: legacyForbiddenDetected ? "intercepted" : paint.mode,
      target: paint.target,
      modelKnown: tuneValid(tune),
      deviceEvidenceRequired: deviceEvidenceRequired,
      profileVerified: verified,
      primaryLedCount: localN("primary"),
      secondaryLedCount: localN("secondary"),
      serialisedLength: serialisedLength,
      needsResync: !!coreState.needsResync,
      outputStateUnknown: !!coreState.outputStateUnknown,
      recoveryPending: recoveryPending(),
    });
  }

  function decisionBundle() {
    var policy = policyForCurrentSource();
    var compiled = app.stimulus === "bounded" && policy.compiled
      ? policy.compiled
      : null;
    var paint = currentPaint(compiled);
    var tune = tuneFromControls();
    var safety = safetyForCurrentSource(paint, tune);
    if (!tuneValid(tune)) tune = CL.identityTune();
    return {
      paint: paint,
      tune: tune,
      compiled: compiled,
      policy: policy,
      safety: safety,
      decision: CA.resolveOutputDecision({ safety: safety, policy: policy, transportReady: transportReady() }),
    };
  }

  function syncTuneControls(tune) {
    if (!tune) return;
    $("gainR").value = formatNumber(tune.gain_r);
    $("gainG").value = formatNumber(tune.gain_g);
    $("gainB").value = formatNumber(tune.gain_b);
    $("gamma").value = formatNumber(tune.gamma);
  }

  function applyCore(action) {
    coreState = CL.reduce(coreState, action);
    if (action.type === "DEVICE_TUNE" && !app.tuneDirty) syncTuneControls(action.tune);
    render();
  }

  function chromaticPathProhibited(policy) {
    return CA.prohibitsChromaticDisplay(policy);
  }

  function recoveryPending() {
    return legacyForbiddenDetected || stopStatusPending ||
      !!(queue && queue.inFlightPriority());
  }

  function maybeClearLegacyRecovery() {
    if (!legacyForbiddenDetected) return;
    if (legacyRecoveryOffGeneration !== legacyRecoveryGeneration ||
        legacyRecoveryStatusGeneration !== legacyRecoveryGeneration) return;
    if (!coreState.confirmed.paint || coreState.confirmed.paint.mode !== "off") return;
    legacyForbiddenDetected = false;
    legacyRecoveryStopId = null;
    legacyRecoveryOffGeneration = 0;
    legacyRecoveryStatusGeneration = 0;
    legacyRecoveryAwaitingStatusGeneration = 0;
    render();
  }

  function setupQueue() {
    queue = CL.createCommandQueue({
      send: function (line) {
        txCount += 1;
        txTrace.push(line);
        log("TX", line);
        if (demo === "transport") {
          setTimeout(function () {
            if (queue) queue.onEvent(mockEventForLine(line));
          }, mockAckDelay);
          return Promise.resolve();
        }
        if (!writer) return Promise.resolve();
        return writer.write(new TextEncoder().encode(line.endsWith("\n") ? line : line + "\n"));
      },
      onSettle: function (info) {
        if (info.priority && info.outcome === "ok" && info.event &&
            info.event.kind === "paint" && info.event.mode === "off") {
          stopStatusPending = true;
          if (info.id === legacyRecoveryStopId) {
            legacyRecoveryOffGeneration = legacyRecoveryGeneration;
            legacyRecoveryAwaitingStatusGeneration = legacyRecoveryGeneration;
          }
        }
        if (info.cmd === "paint_status" && stopStatusPending) {
          stopStatusPending = false;
          if (info.outcome === "ok" && info.event && info.event.kind === "paint" &&
              info.event.mode === "off" &&
              legacyRecoveryAwaitingStatusGeneration === legacyRecoveryGeneration) {
            legacyRecoveryStatusGeneration = legacyRecoveryGeneration;
          }
        }
        if (info.priority && ["timeout", "rejected", "write-error", "fail"].indexOf(info.outcome) !== -1) {
          stopStatusPending = false;
          if (info.id === legacyRecoveryStopId) {
            legacyRecoveryOffGeneration = 0;
            legacyRecoveryStatusGeneration = 0;
            legacyRecoveryAwaitingStatusGeneration = 0;
          }
          applyCore({ type: "RECOVERY_FAILED", detail: info.outcome + " paint=off" });
        }
        if (info.priority && pendingPriority) {
          var priorityResolver = pendingPriority;
          pendingPriority = null;
          priorityResolver(info);
        }
        if (waiters[info.id]) {
          waiters[info.id](info);
          delete waiters[info.id];
        }
        if (info.outcome === "timeout") {
          applyCore({ type: "COMMAND_TIMEOUT", command: info.cmd, priorityStop: !!info.priority });
          if (info.warning) log("WARN", info.warning);
          return;
        }
        if (info.outcome === "rejected") {
          applyCore({ type: "COMMAND_REJECTED", command: info.cmd });
          return;
        }
        var event = info.event;
        if (!event) return;
        if (event.kind === "paint") {
          interceptLegacyMode(event);
          applyCore({ type: "DEVICE_PAINT", paint: event, seq: info.id });
          maybeClearLegacyRecovery();
        } else if (event.kind === "tune") {
          applyCore({
            type: "DEVICE_TUNE",
            tune: event,
            seq: info.id,
            established_by: info.established_by || null,
          });
        } else if (event.kind === "save_ok") applyCore({ type: "DEVICE_SAVE_OK" });
        else if (event.kind === "save_fail") applyCore({ type: "DEVICE_SAVE_FAIL" });
        else if (event.kind === "look") applyCore({ type: "LOOK_STATUS", look: event });
      },
    });
  }

  function mockEventForLine(line) {
    var split = line.replace(/^:/, "").split("=");
    var command = split[0];
    var value = split.slice(1).join("=");
    if (command === mockFailCommand) return { kind: "bad_command", command: command };
    if (command === "chip_id") return { kind: "chip_id", chip_id: "9087A500" };
    if (command === "build") return { kind: "build", env: "k1_main_rpl_im69d" };
    if (command === "look_status") return {
      kind: "look", slot: 15, sec: "unknown", env: "k1_main_rpl_im69d",
    };
    if (command === "paint_status") return Object.assign({}, mockDevice.paint);
    if (command === "tune_status") return Object.assign({}, mockDevice.tune);
    if (command === "paint_target") mockDevice.paint.target = value;
    else if (command === "paint_rgb") {
      var rgb = value.split(",").map(Number);
      mockDevice.paint.r = rgb[0]; mockDevice.paint.g = rgb[1]; mockDevice.paint.b = rgb[2];
    } else if (command === "paint_stops") {
      var channels = value.split(",").map(Number);
      mockDevice.paint.stops = [];
      for (var index = 0; index < channels.length; index += 3) {
        mockDevice.paint.stops.push(channels.slice(index, index + 3));
      }
    } else if (command === "paint") mockDevice.paint.mode = value;
    else if (command === "tune_gain") {
      var gain = value.split(",").map(Number);
      mockDevice.tune.gain_r = gain[0]; mockDevice.tune.gain_g = gain[1]; mockDevice.tune.gain_b = gain[2];
    } else if (command === "tune_gamma") mockDevice.tune.gamma = Number(value);
    if (command.indexOf("paint") === 0) return Object.assign({}, mockDevice.paint);
    if (command.indexOf("tune_") === 0 && command !== "tune_save") return Object.assign({}, mockDevice.tune);
    if (command === "tune_save") return { kind: "save_ok" };
    return { kind: "bad_command", command: command };
  }

  function interceptLegacyMode(event) {
    if (event.mode !== "ramp") return;
    legacyRecoveryGeneration += 1;
    legacyForbiddenDetected = true;
    legacyRecoveryStopId = null;
    legacyRecoveryOffGeneration = 0;
    legacyRecoveryStatusGeneration = 0;
    legacyRecoveryAwaitingStatusGeneration = 0;
    stopStatusPending = false;
    log("WARN", "Prohibited legacy Paint mode intercepted; priority paint=off queued.");
    if (queue) legacyRecoveryStopId = queue.enqueuePriorityStop();
  }

  function request(command, line, extra) {
    return new Promise(function (resolve) {
      var id = queue.enqueue(command, line, extra || {});
      waiters[id] = resolve;
    });
  }

  function successful(info) { return !!info && info.outcome === "ok"; }

  function requireReply(info, command, kinds) {
    var event = info && info.event;
    if (!successful(info) || !event || kinds.indexOf(event.kind) === -1) {
      var outcome = info && info.outcome ? info.outcome : "missing reply";
      throw new Error(command + " hydration failed: " + outcome);
    }
    return event;
  }

  function consumeEvents(events) {
    events.forEach(function (event) {
      if (event.kind === "chatter") log("CHAT", event.line);
      else if (event.kind === "malformed") log("BAD", event.line);
      if (!queue || !queue.onEvent(event)) {
        if (event.kind === "paint") {
          interceptLegacyMode(event);
          applyCore({ type: "DEVICE_PAINT", paint: event });
        } else if (event.kind === "tune") applyCore({ type: "DEVICE_TUNE", tune: event });
        else if (event.kind === "save_ok") applyCore({ type: "DEVICE_SAVE_OK" });
        else if (event.kind === "save_fail") applyCore({ type: "DEVICE_SAVE_FAIL" });
      }
    });
  }

  async function pumpReader() {
    var decoder = new TextDecoder();
    readLoop = true;
    try {
      while (readLoop && reader) {
        var chunk = await reader.read();
        if (chunk.done) break;
        consumeEvents(parser.feed(decoder.decode(chunk.value, { stream: true })));
      }
    } catch (error) {
      if (readLoop) {
        log("ERR", String(error));
        applyCore({ type: "DEVICE_LOST" });
      }
    }
  }

  async function hydrate() {
    applyCore({ type: "PROFILE_START" });
    parser = CL.createLineParser();
    try {
      var chip = requireReply(
        await request("chip_id", CL.serialize.chipId()), "chip_id", ["chip_id"]
      );
      var build = requireReply(
        await request("build", CL.serialize.build()), "build", ["build"]
      );
      var look = requireReply(
        await request("look_status", CL.serialize.lookStatus()),
        "look_status", ["look", "look_empty"]
      );
      var lookEvent = look.kind === "look" ? look : null;
      var resolved = CL.resolveDeviceProfile({
        chip_id: chip.chip_id,
        build_env: build.env,
        look_env: lookEvent && lookEvent.env,
        active_primary_look: lookEvent ? lookEvent.slot : "unknown",
        active_secondary_look: lookEvent ? lookEvent.sec : "unknown",
      });
      applyCore({ type: "PROFILE_RESOLVED", profile: resolved, look: lookEvent });
      requireReply(
        await request("paint_status", CL.serialize.paintStatus()),
        "paint_status", ["paint"]
      );
      requireReply(
        await request("tune_status", CL.serialize.tuneStatus()),
        "tune_status", ["tune"]
      );
      maybeClearLegacyRecovery();
      if (legacyForbiddenDetected || recoveryPending()) {
        throw new Error("legacy Paint recovery remains unresolved");
      }
      applyCore({ type: "RESYNC_DONE" });
      return true;
    } catch (error) {
      applyCore({ type: "RECOVERY_FAILED", detail: String(error && error.message ? error.message : error) });
      log("ERR", "Hydration: " + String(error && error.message ? error.message : error));
      return false;
    }
  }

  async function connect() {
    if (!serialOk || demo) {
      toast(demo ? "Browser fixtures cannot open a serial port." : "Web Serial is unavailable in this browser.");
      return;
    }
    applyCore({ type: "REQUEST_PORT" });
    try {
      port = await navigator.serial.requestPort();
      applyCore({ type: "PORT_OPENING" });
      await port.open({ baudRate: 115200 });
      writer = port.writable.getWriter();
      reader = port.readable.getReader();
      port.addEventListener("disconnect", function () {
        applyCore({ type: "DEVICE_LOST" });
        log("WARN", "Unexpected disconnect; output state may be unknown.");
      });
      setupQueue();
      pumpReader();
      await hydrate();
    } catch (error) {
      log("ERR", String(error && error.message ? error.message : error));
      if (String(error.name) === "NotFoundError") applyCore({ type: "REQUEST_CANCELLED" });
      else applyCore({ type: "PORT_OPEN_FAILED", error: String(error) });
    }
  }

  function waitForPrioritySettle(ms) {
    return Promise.race([
      new Promise(function (resolve) { pendingPriority = resolve; }),
      new Promise(function (resolve) {
        setTimeout(function () {
          if (pendingPriority) pendingPriority = null;
          resolve({ outcome: "timeout", event: null, priority: true });
        }, ms);
      }),
    ]);
  }

  async function disconnect() {
    if (disconnecting) return;
    disconnecting = true;
    render();
    var hadActive = !!(coreState.confirmed.paint && coreState.confirmed.paint.mode !== "off") ||
      !!coreState.paintMayBeActive || !!coreState.outputStateUnknown;
    var inFlight = !!(queue && queue.depth() > 0);
    var shutdown;
    try {
      if (queue && port && (hadActive || inFlight)) {
        var settle = waitForPrioritySettle(CL.DISCONNECT_WAIT_MS);
        queue.enqueuePriorityStop();
        var info = await settle;
        shutdown = CL.classifyDisconnectShutdown({
          stopOutcome: info.outcome,
          paintModeFromReply: info.event && info.event.kind === "paint" ? info.event.mode : null,
          hadActivePaint: hadActive,
          inFlightAtStart: inFlight || hadActive,
        });
      } else {
        shutdown = CL.classifyDisconnectShutdown({
          stopOutcome: null,
          paintModeFromReply: null,
          hadActivePaint: hadActive,
          inFlightAtStart: inFlight,
        });
      }
    } catch (error) {
      shutdown = CL.classifyDisconnectShutdown({
        stopOutcome: "write-error",
        paintModeFromReply: null,
        hadActivePaint: hadActive,
        inFlightAtStart: inFlight,
      });
      log("ERR", "Disconnect stop failed: " + String(error));
    }
    if (queue) queue.flush();
    readLoop = false;
    try { if (reader) await reader.cancel(); } catch (ignoreReader) {}
    try { if (writer) writer.releaseLock(); } catch (ignoreWriter) {}
    try { if (port) await port.close(); } catch (ignorePort) {}
    reader = writer = port = queue = null;
    disconnecting = false;
    applyCore({
      type: "DISCONNECTED",
      shutdown: shutdown.claim,
      paintStopped: shutdown.paintStopped,
      outputUnknown: shutdown.outputUnknown,
      paintMayBeActive: !shutdown.paintStopped && hadActive,
    });
    log(
      shutdown.paintStopped ? "OK" : "WARN",
      shutdown.paintStopped
        ? "Disconnected with output confirmed off."
        : "Disconnected without confirmed output stop."
    );
  }

  function stopOutput() {
    if (!queue) {
      toast("No connected device. Local Preview remains unchanged.");
      return;
    }
    queue.enqueuePriorityStop();
    toast("Priority paint=off queued; all ordinary mutations were superseded.");
  }

  async function sendSourceTransaction() {
    var bundle = decisionBundle();
    if (!bundle.decision.deviceTestAllowed || transaction) return;
    var revisionAtStart = app.sourceRevision;
    var confirmedCount = 0;
    transaction = "source";
    render();
    try {
      var operations = [["paint_target", CL.serialize.paintTarget(bundle.paint.target)]];
      if (bundle.paint.mode === "solid") {
        operations.push(["paint_rgb", CL.serialize.paintRgb(bundle.paint.r, bundle.paint.g, bundle.paint.b)]);
      }
      if (bundle.paint.mode === "stops") {
        operations.push(["paint_stops", CL.serialize.paintStops(bundle.paint.stops)]);
      }
      operations.push(["paint", CL.serialize.paint(bundle.paint.mode)]);
      for (var index = 0; index < operations.length; index += 1) {
        var info = await request(operations[index][0], operations[index][1]);
        if (!successful(info)) {
          var sourceError = new Error(operations[index][0] + " was not confirmed");
          sourceError.outcome = info && info.outcome;
          throw sourceError;
        }
        confirmedCount += 1;
      }
      if (revisionAtStart === app.sourceRevision) {
        app.sourceDirty = false;
        coreState = CL.reduce(coreState, { type: "DRAFT_CLEAR_PAINT" });
        toast("Source command sequence confirmed. Persistence was not changed.");
      } else {
        toast("Sent Source snapshot confirmed; newer local edits remain drafted.");
      }
    } catch (error) {
      log("ERR", "Source command sequence: " + String(error));
      if (confirmedCount > 0) {
        applyCore({ type: "COMMAND_SEQUENCE_PARTIAL", sequence: "Source", confirmedCount: confirmedCount });
        if (error.outcome !== "superseded" && queue) queue.enqueuePriorityStop();
        toast("Source changed only partially; Stop output queued and Resync is required.");
      } else {
        toast("Source command sequence stopped; local draft is preserved.");
      }
    } finally {
      transaction = null;
      render();
    }
  }

  async function applyTuneTransaction() {
    var bundle = decisionBundle();
    if (!tuneSupportedByProfile() || !bundle.decision.deviceTestAllowed ||
        !app.tuneDirty || transaction) return;
    var revisionAtStart = app.tuneRevision;
    var confirmedCount = 0;
    transaction = "tune";
    render();
    try {
      var gain = await request(
        "tune_gain",
        CL.serialize.tuneGain(bundle.tune.gain_r, bundle.tune.gain_g, bundle.tune.gain_b),
        { established_by: "tune_gain" }
      );
      if (!successful(gain)) {
        var gainError = new Error("gain was not confirmed");
        gainError.outcome = gain && gain.outcome;
        throw gainError;
      }
      confirmedCount += 1;
      var gamma = await request(
        "tune_gamma",
        CL.serialize.tuneGamma(bundle.tune.gamma),
        { established_by: "tune_gamma" }
      );
      if (!successful(gamma)) {
        var gammaError = new Error("gamma was not confirmed");
        gammaError.outcome = gamma && gamma.outcome;
        throw gammaError;
      }
      confirmedCount += 1;
      if (revisionAtStart === app.tuneRevision) {
        app.tuneDirty = false;
        coreState = CL.reduce(coreState, { type: "DRAFT_CLEAR_TUNE" });
        toast("Gain and gamma command sequence confirmed.");
      } else {
        toast("Sent Tune snapshot confirmed; newer local edits remain drafted.");
      }
    } catch (error) {
      log("ERR", "Tune command sequence: " + String(error));
      if (confirmedCount > 0) {
        applyCore({ type: "COMMAND_SEQUENCE_PARTIAL", sequence: "Tune", confirmedCount: confirmedCount });
        if (error.outcome !== "superseded" && queue) queue.enqueuePriorityStop();
        toast("Tune changed only partially; Stop output queued and Resync is required.");
      } else {
        toast("Tune command sequence stopped; every unsent field remains drafted.");
      }
    } finally {
      transaction = null;
      render();
    }
  }

  async function saveTune() {
    var bundle = decisionBundle();
    if (!tuneSupportedByProfile() || !bundle.decision.saveAllowed ||
        coreState.slot15Content.status !== "known-this-session" || transaction) return;
    transaction = "save";
    applyCore({ type: "SAVE_START" });
    try {
      var info = await request("tune_save", CL.serialize.tuneSave());
      if (!successful(info)) throw new Error("save was not confirmed");
      toast("Slot 15 save confirmed this session.");
    } catch (error) {
      log("ERR", "Save: " + String(error));
      toast("Save failed; persistence is unchanged or unknown.");
    } finally {
      transaction = null;
      render();
    }
  }

  function resync() {
    if (port && !transaction) hydrate();
  }

  function markSourceDirty() {
    app.sourceDirty = true;
    app.sourceRevision += 1;
    coreState = CL.reduce(coreState, { type: "DRAFT_PAINT", values: currentPaint() });
    render();
  }

  function markTuneDirty() {
    app.tuneDirty = true;
    app.tuneRevision += 1;
    var tune = tuneFromControls();
    if (tuneValid(tune)) coreState = CL.reduce(coreState, { type: "DRAFT_TUNE", values: tune });
    render();
  }

  function drawStrip(canvas, frame, n, blocked, suppressChromaticPath) {
    var context = canvas.getContext("2d");
    var width = canvas.width;
    var height = canvas.height;
    context.clearRect(0, 0, width, height);
    context.fillStyle = "#000";
    context.fillRect(0, 0, width, height);
    if (blocked || suppressChromaticPath || !frame || !frame.pixels || !n) return;
    var rows = [];
    for (var index = 0; index < n; index += 1) {
      rows.push([
        frame.pixels[3 * index] >> 8,
        frame.pixels[3 * index + 1] >> 8,
        frame.pixels[3 * index + 2] >> 8,
      ]);
    }
    if (app.view === "diffusion") {
      rows = rows.map(function (_, rowIndex) {
        var colour = [0, 0, 0];
        var weightTotal = 0;
        for (var distance = -5; distance <= 5; distance += 1) {
          var sourceIndex = clamp(rowIndex + distance, 0, n - 1);
          var weight = Math.exp(-(distance * distance) / 8);
          weightTotal += weight;
          for (var channel = 0; channel < 3; channel += 1) {
            colour[channel] += rows[sourceIndex][channel] * weight;
          }
        }
        return colour.map(function (channel) { return channel / weightTotal; });
      });
    }
    var pitch = width / n;
    rows.forEach(function (rgb, rowIndex) {
      if (app.view === "diffusion") {
        var rounded = u8(rgb);
        var gradient = context.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, "rgba(" + rounded.join(",") + ",.18)");
        gradient.addColorStop(0.5, "rgba(" + rounded.join(",") + ",1)");
        gradient.addColorStop(1, "rgba(" + rounded.join(",") + ",.18)");
        context.fillStyle = gradient;
      } else context.fillStyle = CA.toHex(rgb);
      context.fillRect(
        rowIndex * pitch - (app.view === "diffusion" ? 1 : 0),
        0,
        pitch + (app.view === "diffusion" ? 2 : 1),
        height
      );
    });
    context.fillStyle = "rgba(0,0,0,.48)";
    context.fillRect(width / 2 - 1, 0, 2, height);
    if (selectedLed < frame.n) {
      var markerX = Math.round((selectedLed + 0.5) / frame.n * width);
      context.fillStyle = "rgba(0,0,0,.9)";
      context.fillRect(markerX - 2, 0, 5, height);
      context.fillStyle = "rgba(255,255,255,.96)";
      context.fillRect(markerX, 0, 1, height);
    }
  }

  function drawCurve(tune, blocked) {
    var canvas = $("curveCanvas");
    var context = canvas.getContext("2d");
    var width = canvas.width;
    var height = canvas.height;
    context.clearRect(0, 0, width, height);
    if (blocked) return;
    context.strokeStyle = "rgba(255,255,255,.32)";
    context.lineWidth = 2;
    context.beginPath();
    context.moveTo(0, height);
    context.lineTo(width, 0);
    context.stroke();
    var nodes = CL.buildRgb1d(tune);
    [
      { key: "r", colour: "#ff786d" },
      { key: "g", colour: "#88c98b" },
      { key: "b", colour: "#7797f5" },
    ].forEach(function (channel) {
      context.strokeStyle = channel.colour;
      context.lineWidth = 3;
      context.beginPath();
      nodes[channel.key].forEach(function (value, nodeIndex) {
        var x = nodeIndex / 255 * width;
        var y = height - value / 65535 * height;
        if (nodeIndex === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      });
      context.stroke();
    });
  }

  function correctionText(frame) {
    if (!frame) return "Not evaluated";
    if (!frame.source.applied || !frame.pixels) return "Not targeted";
    var look = frame.lookResolution;
    var inherited = look && look.relation === "inherit";
    if (frame.transform.kind === "local_draft_simulated") {
      return inherited
        ? "Inherits Primary look · local draft simulated"
        : "Local draft · not applied";
    }
    if (!look || !look.effectiveKnown) {
      return inherited
        ? "Inherits Primary look · Primary look unknown"
        : "Before correction · active look unknown";
    }
    if (frame.framingReason === "slot15_unknown" ||
        (frame.slot15Knowledge === "unknown" && frame.selection === "pre")) {
      return inherited
        ? "Inherits Primary look · slot-15 contents unknown"
        : "Before correction · slot-15 contents unknown";
    }
    if (frame.transform.kind === "device_confirmed_tune") {
      return inherited
        ? "Inherits Primary look · slot 15 browser model"
        : "Device-confirmed tune · browser parity model";
    }
    if (frame.transform.kind === "known_session_simulated") {
      return inherited
        ? "Inherits Primary look · active look " + look.effectiveSlot + " not modelled"
        : "Known session tune simulated · active look " + look.effectiveSlot + " not modelled";
    }
    return inherited ? "Inherits Primary look · before correction" : "Before correction";
  }

  function patternText(frame) {
    if (!frame) return "Unavailable";
    if (!frame.source.applied || !frame.pixels) return "Not targeted";
    return frame.source.kind === "local_stimulus" ? "Local draft" : "Current settings";
  }

  function outputText(output, primary, secondary) {
    if (output.status === "unavailable") {
      return { title: "Output comparison unavailable", note: "Preview frames are not available." };
    }
    if (output.unmatchedLedCount) {
      return {
        title: "LED geometry differs",
        note: output.primaryLedCount + " Primary · " + output.secondaryLedCount + " Secondary",
      };
    }
    var activeLookUnknown = primary && secondary &&
      (!primary.lookResolution.effectiveKnown || !secondary.lookResolution.effectiveKnown);
    var slotContentsUnknown = primary && secondary &&
      ((primary.selection === "pre" && primary.framingReason === "slot15_unknown") ||
       (secondary.selection === "pre" && secondary.framingReason === "slot15_unknown"));
    if (output.status === "match" && (activeLookUnknown || slotContentsUnknown)) {
      return {
        title: "Pre-correction references match",
        note: activeLookUnknown
          ? "Correction output is not claimed until the active look is known."
          : "Correction output is not claimed until slot-15 contents are known.",
      };
    }
    if (output.status === "match") {
      return { title: "LED values match", note: "All " + output.sharedLedCount + " cached LED values are equal." };
    }
    return {
      title: "LED values differ at " + output.differingLedCount + " LEDs",
      note: "First difference at LED " + output.firstDifferingLed + ".",
    };
  }

  function basisText(basis, secondary) {
    if (basis.status === "unavailable") {
      return { title: "Preview basis unavailable", note: "Frame authority is not established." };
    }
    if (basis.status === "match") {
      return { title: "Preview basis matches", note: "Pattern, correction and look relationship match." };
    }
    var inheritsUnknown = secondary && secondary.lookResolution.relation === "inherit" &&
      !secondary.lookResolution.effectiveKnown;
    var labels = {
      source_provenance: "Source provenance differs.",
      source_pattern: "Pattern differs.",
      source_targeting: "Targeting differs.",
      correction_provenance: "Correction evidence differs.",
      preview_selection: "Pre/post selection differs.",
      look_relationship: inheritsUnknown
        ? "Secondary inherits an unknown Primary look."
        : "Secondary inherits Primary look.",
      effective_look: "Effective looks differ.",
      slot15_knowledge: "Slot-15 knowledge differs.",
      applied_tune: "Applied tune differs.",
      render_scale: "Render scale differs.",
    };
    return {
      title: "Preview basis differs",
      note: basis.reasons.map(function (reason) { return labels[reason]; }).join(" "),
    };
  }

  function setChannel(which, frame, safetyBlocked, chromaticSuppressed) {
    var unavailable = !frame || !frame.pixels || safetyBlocked || chromaticSuppressed;
    $(which + "StripWrap").classList.toggle("unavailable", unavailable);
    $(which + "Unavailable").textContent = safetyBlocked
      ? "Preview unavailable — Device Safety gate failed"
      : chromaticSuppressed
        ? "Prohibited chromatic path suppressed"
        : "Preview frame not established";
    if (!frame) {
      $(which + "Pattern").textContent = "Unavailable";
      $(which + "Correction").textContent = "Not evaluated";
      return;
    }
    $(which + "Geometry").textContent = frame.n + " LEDs · centre " +
      Math.floor((frame.n - 1) / 2) + "/" + Math.ceil((frame.n - 1) / 2);
    $(which + "Pattern").textContent = patternText(frame);
    $(which + "Correction").textContent = correctionText(frame);
    $(which + "Canvas").setAttribute("aria-label",
      (which === "primary" ? "Primary" : "Secondary") + " " +
      (app.view === "diffusion" ? "diffusion-model" : "LED-values") +
      " preview, " + frame.n + " LEDs");
  }

  function formatTriplet(values) {
    return '<span class="component">R ' + values[0] + '</span>' +
      '<span class="component">G ' + values[1] + '</span>' +
      '<span class="component">B ' + values[2] + '</span>';
  }

  function setInspectorOutput(which, reading, safetyBlocked) {
    var rgb16 = $(which + "Rgb16");
    var rgb8 = $(which + "Rgb8");
    if (safetyBlocked) {
      rgb16.textContent = "Unavailable — Device Safety gate failed";
      rgb8.textContent = "No cached value shown";
    } else if (reading.kind === "not_present") {
      rgb16.textContent = "Not present — " + reading.n + " LEDs";
      rgb8.textContent = "Not present";
    } else if (reading.kind !== "value") {
      rgb16.textContent = "Unavailable — preview frame not established";
      rgb8.textContent = "Unavailable";
    } else {
      rgb16.innerHTML = formatTriplet(reading.rgb16);
      rgb8.innerHTML = formatTriplet(reading.rgb8);
    }
  }

  function maximumSelectedLed() {
    return Math.max(
      stageFrames.primary ? stageFrames.primary.n : 0,
      stageFrames.secondary ? stageFrames.secondary.n : 0
    ) - 1;
  }

  function renderInspector(safetyBlocked) {
    $("selectedLedInput").value = String(selectedLed);
    $("inspectorCaption").textContent = "Computed colour values at LED " + selectedLed;
    setInspectorOutput("primary", CL.inspectStageFrame(stageFrames.primary, selectedLed), safetyBlocked);
    setInspectorOutput("secondary", CL.inspectStageFrame(stageFrames.secondary, selectedLed), safetyBlocked);
    var maximum = maximumSelectedLed();
    $("selectedLedInput").max = String(Math.max(maximum, 0));
    $("selectedLedInput").disabled = safetyBlocked || maximum < 0;
    $("selectedLedRange").textContent = safetyBlocked
      ? "LED inspection unavailable until device truth is re-established."
      : maximum < 0
        ? "LED inspection unavailable because no preview frame is established."
        : "Available range: 0 to " + maximum + ".";
  }

  function announceSelection() {
    function phrase(which, reading) {
      return reading.kind === "value"
        ? which + " RGB8 " + reading.rgb8.join(", ") + "."
        : which + " " + (reading.kind === "not_present" ? "not present." : "unavailable.");
    }
    var primary = CL.inspectStageFrame(stageFrames.primary, selectedLed);
    var secondary = CL.inspectStageFrame(stageFrames.secondary, selectedLed);
    $("inspectorAnnouncement").textContent = "LED " + selectedLed + ". " +
      phrase("Primary", primary) + " " + phrase("Secondary", secondary);
  }

  function clearInspectorError() {
    $("selectedLedInput").removeAttribute("aria-invalid");
    $("selectedLedError").hidden = true;
    $("selectedLedError").textContent = "";
  }

  function setSelectedLed(candidate, inputKind, announce) {
    var maximum = maximumSelectedLed();
    var value = Number(candidate);
    if (!Number.isFinite(value) || !Number.isInteger(value) || value < 0 || value > maximum) {
      if (inputKind === "number") {
        $("selectedLedInput").setAttribute("aria-invalid", "true");
        $("selectedLedError").textContent = "Enter a whole LED index from 0 to " + Math.max(maximum, 0) + ".";
        $("selectedLedError").hidden = false;
      }
      return false;
    }
    clearInspectorError();
    selectedLed = value;
    drawStrip($("primaryCanvas"), stageFrames.primary, localN("primary"), false, false);
    drawStrip($("secondaryCanvas"), stageFrames.secondary, localN("secondary"), false, false);
    renderInspector(false);
    if (announce) announceSelection();
    if (globalThis.__colourLabWorkbench) globalThis.__colourLabWorkbench.selectedLed = selectedLed;
    return true;
  }

  function renderComparison(comparison) {
    var output = outputText(comparison.output, stageFrames.primary, stageFrames.secondary);
    var basis = basisText(comparison.basis, stageFrames.secondary);
    $("outputComparison").textContent = output.title;
    $("outputComparisonNote").textContent = output.note;
    $("basisComparison").textContent = basis.title;
    $("basisComparisonNote").textContent = basis.note;
  }

  function renderHandoff(bundle, safetyBlocked, policyBlocked) {
    var state;
    var label;
    var href;
    if (safetyBlocked || coreState.needsResync || coreState.outputStateUnknown) {
      state = "Device truth must be re-established before Preview.";
      label = "Return to Device";
      href = "#deviceTitle";
    } else if (policyBlocked) {
      state = "Product colour policy blocks this source.";
      label = "Review Source";
      href = "#sourceTitle";
    } else if (app.tuneDirty) {
      state = "Tune draft has not been applied.";
      label = "Review Tune";
      href = "#tuneTitle";
    } else if (app.sourceDirty) {
      state = "Source draft has not been tested on K1.";
      label = "Review Source";
      href = "#sourceTitle";
    } else if (coreState.slot15Content.status !== "known-this-session") {
      state = "Slot-15 contents are unknown; device truth needs review.";
      label = "Return to Device";
      href = "#deviceTitle";
    } else {
      state = "No pending draft. Preview remains read-only.";
      label = "Review Tune";
      href = "#tuneTitle";
    }
    $("nextState").textContent = state;
    $("nextLink").innerHTML = label + ' <span aria-hidden="true">→</span>';
    $("nextLink").href = href;
  }

  function gradientFor(space, suppressed) {
    if (suppressed) {
      return "repeating-linear-gradient(-45deg,#080808 0 7px,#17100a 7px 14px)";
    }
    var colours = CA.samplePalette(app.paletteStops, 25, space).map(function (rgb, index) {
      return CA.toHex(rgb) + " " + Math.round(index / 24 * 100) + "%";
    });
    return "linear-gradient(90deg," + colours.join(",") + ")";
  }

  function renderPaletteEditor(policy) {
    var suppressed = chromaticPathProhibited(policy);
    $("stopRow").innerHTML = app.paletteStops.map(function (stop, index) {
      var value = CA.toHex(stop.rgb);
      var swatch = suppressed ? "#111111" : value;
      return '<div class="stop"><span class="stop-swatch" aria-hidden="true" style="background:' +
        swatch + '"></span><label class="stop-hex">Hex<input type="text" inputmode="text" maxlength="7" pattern="#[0-9A-Fa-f]{6}" aria-label="Hex colour for stop ' +
        (index + 1) + '" data-picker-index="' + index + '" value="' + value +
        '"></label><label class="stop-position">Position<input type="number" data-position-index="' + index +
        '" min="0" max="1" step="0.01" value="' + stop.position.toFixed(2) + '"></label></div>';
    }).join("");
    document.querySelectorAll("[data-picker-index]").forEach(function (picker) {
      picker.addEventListener("change", function () {
        try {
          app.paletteStops[Number(picker.dataset.pickerIndex)].rgb = parseHex(picker.value);
          markSourceDirty();
        } catch (error) {
          toast("Enter a hexadecimal colour in the form #FFB84D.");
          render();
        }
      });
    });
    document.querySelectorAll("[data-position-index]").forEach(function (input) {
      input.addEventListener("change", function () {
        var index = Number(input.dataset.positionIndex);
        var candidate = Number(input.value);
        var duplicate = app.paletteStops.some(function (stop, stopIndex) {
          return stopIndex !== index && Math.abs(stop.position - candidate) < 0.0001;
        });
        if (!finite(candidate) || candidate < 0 || candidate > 1 || duplicate) {
          toast("Stop positions must be unique values from 0 to 1.");
          render();
          return;
        }
        app.paletteStops[index].position = candidate;
        app.paletteStops.sort(function (left, right) { return left.position - right.position; });
        markSourceDirty();
      });
    });
    $("baseHueValue").textContent = app.baseHue + "°";
    $("rgbTrack").style.background = gradientFor("rgb", suppressed);
    $("oklchTrack").style.background = gradientFor("oklch", suppressed);
    $("hsvTrack").style.background = gradientFor("hsv", suppressed);
  }

  function renderStatus(bundle) {
    var connection = coreState.connection;
    $("serialChip").textContent = serialOk ? "Web Serial available" : "Web Serial unavailable";
    $("connectionChip").textContent = connection.charAt(0).toUpperCase() + connection.slice(1) +
      (demo ? " · browser fixture" : "");
    $("connectionChip").classList.toggle("ok", connection === "ready");
    var known = profile();
    var tuneAvailable = tuneSupportedByProfile();
    $("tunePanel").hidden = !tuneAvailable;
    var showBothScale = !!(known && CL.showBothScale(known));
    $("scaleDetailRow").hidden = !showBothScale;
    $("scaleDetail").textContent = showBothScale
      ? "Both target applies ×" + known.both_scale.toFixed(2) + " on this verified profile."
      : "Verified profile scale unavailable.";
    $("profileChip").textContent = known
      ? known.identity_status + " · " + (known.env || "unknown env") + " · " +
        (known.chip_id || "unknown chip") + " · " + localN("primary") + "/" +
        localN("secondary") + " · " + (known.look_backend || "unknown backend")
      : "No verified device profile · local geometry 160/160";
    var paint = coreState.confirmed.paint;
    $("deviceStateChip").textContent = bundle.decision.kind === "safety_blocked"
      ? "device safety FAIL · Preview unavailable · paint=off recovery is the only output action"
      : bundle.decision.kind === "policy_blocked"
        ? "product policy FAIL · bounded local analysis visible · device and export locked"
        : (paint ? "paint " + paint.mode + "/" + paint.target : "paint state unknown") +
          " · slot-15 " + coreState.slot15Content.status + " · active P=" +
          coreState.activeLookPrimary + " · S=" + coreState.activeLookSecondary;
    $("connectBtn").disabled = !serialOk || !!port || !!demo || disconnecting;
    $("disconnectBtn").disabled = !port || disconnecting;
    $("resyncBtn").disabled = !port || !!transaction || disconnecting;
    $("safetyRecoveryValue").textContent = queue
      ? (coreState.needsResync ? "Stop output, then Resync required" : "Stop output available")
      : "No device output path";
  }

  function render() {
    var bundle;
    try {
      bundle = decisionBundle();
    } catch (error) {
      log("ERR", "Render decision: " + String(error));
      var safetyFailure = { ok: false, issues: [{ code: "model_unknown", message: String(error) }] };
      bundle = {
        paint: { mode: "off", target: app.target },
        tune: CL.identityTune(),
        policy: { ok: false, issues: [{ code: "invalid_palette", message: String(error) }], metrics: null },
        safety: safetyFailure,
        decision: CA.resolveOutputDecision({ safety: safetyFailure, policy: { ok: false, issues: [] }, transportReady: false }),
      };
    }
    var tuneAvailable = tuneSupportedByProfile();
    var safetyBlocked = bundle.decision.kind === "safety_blocked";
    var policyBlocked = bundle.decision.kind === "policy_blocked";
    var suppressChromaticPath = chromaticPathProhibited(bundle.policy);
    $("policyBanner").classList.toggle("visible", policyBlocked);
    $("safetyBanner").classList.toggle("visible", safetyBlocked);
    $("nonProductStamp").classList.toggle("visible", policyBlocked);
    $("previewPanel").classList.toggle("diffusion-view", app.view === "diffusion");
    $("viewQualifier").textContent = app.view === "diffusion"
      ? "Relative diffusion audition only; not device readback, LUT readback or a physical colour match."
      : "Not device readback, LUT readback or a physical colour match.";
    var stimulusName = {
      neutral: "Neutral transfer", solid: "Solid", bounded: "Bounded palette",
      card: "K1 Card · 17", rgb: "Isolated R / G / B ramps", sv: "Single-hue S/V",
    }[app.stimulus];
    $("sourceDraftTitle").textContent = stimulusName + " · " +
      app.target.charAt(0).toUpperCase() + app.target.slice(1);
    $("sourceDraftState").textContent = transaction === "source"
      ? "Command sequence in progress · draft retained until all replies confirm"
      : app.sourceDirty
        ? "Local draft · no command sent"
        : "Device-confirmed this session · persistence unchanged";
    $("tuneDraftTitle").textContent = app.tuneDirty
      ? "Gain + gamma drafted as one command sequence"
      : "No tune draft";
    $("tuneDraftState").textContent = transaction === "tune"
      ? "Command sequence in progress · unsent fields retained"
      : "Previewed locally · persistence unchanged";
    $("sendStimulusBtn").disabled = !app.sourceDirty || !bundle.decision.deviceTestAllowed || !!transaction;
    $("applyTuneBtn").disabled = !tuneAvailable || !app.tuneDirty ||
      !bundle.decision.deviceTestAllowed || !!transaction;
    $("saveBtn").disabled = !tuneAvailable || !bundle.decision.saveAllowed ||
      coreState.slot15Content.status !== "known-this-session" || app.tuneDirty || !!transaction;
    $("identityBtn").disabled = !tuneAvailable || !!transaction;
    $("revertBtn").disabled = !tuneAvailable || !coreState.sessionBaseline || !!transaction;
    $("exportBtn").disabled = !bundle.decision.exportAllowed;
    $("sendStimulusBtn").textContent = safetyBlocked
      ? "Blocked · use Stop output"
      : policyBlocked ? "NON-PRODUCT · blocked" : transaction === "source" ? "Testing…" : "Test on device";
    $("applyTuneBtn").textContent = safetyBlocked || policyBlocked
      ? "Blocked by gate"
      : transaction === "tune" ? "Applying…" : "Apply tune (gain + gamma)";
    $("safetyGate").classList.toggle("fail", !bundle.safety.ok);
    $("safetyGateStatus").textContent = bundle.safety.ok ? (queue ? "PASS" : "LOCAL") : "FAIL";
    $("safetyModelState").textContent = bundle.safety.ok
      ? (queue ? "Coherent verified profile" : "Coherent local model only")
      : (bundle.safety.issues[0] ? bundle.safety.issues[0].message : "Unsafe / unknown");
    $("policyGate").classList.toggle("fail", !bundle.policy.ok);
    $("policyGateStatus").textContent = bundle.policy.ok ? "PASS" : "FAIL";
    var metrics = bundle.policy.metrics || {};
    $("hueTravelValue").textContent = metrics.hueTravelDeg === undefined
      ? "Diagnostic shape"
      : metrics.hueTravelDeg.toFixed(1) + "° / 80° max";
    $("hueFamilyValue").textContent = metrics.hueFamilies === undefined
      ? "Diagnostic shape"
      : metrics.hueFamilies + " / 3 max";
    $("wheelSpanValue").textContent = suppressChromaticPath ? "Present · all colour pixels suppressed" : "Absent";
    $("nearWhiteValue").textContent = metrics.nearWhite ? "Present · blocked" : "Absent";
    var compiled = bundle.compiled || compiledPalette();
    $("sourceStopCount").textContent = app.paletteStops.length + " source stops";
    $("compiledStopCount").textContent = "Rich local draft → " + compiled.compiledStopCount + " Paint stops";
    $("approximationChip").textContent = "Max error " + compiled.approximation.maxChannelError8.toFixed(1) +
      "/255 · RMS " + compiled.approximation.rmsChannelError8.toFixed(1);
    $("paletteNameChip").textContent = (app.sourceDirty ? "Draft" : "Confirmed source") + " · Amber Ember";
    renderPaletteEditor(bundle.policy);
    renderStatus(bundle);

    if (!safetyBlocked && !suppressChromaticPath) {
      stageFrames.primary = CL.stageFrame({
        state: coreState, channel: "primary", paint: bundle.paint, tune: bundle.tune,
        n: localN("primary"), both_scale_enabled: !!(profile() && profile().both_scale_enabled),
        both_scale: profile() && profile().both_scale, simulate_draft: true,
        local_stimulus: app.sourceDirty,
        source_in_flight: transaction === "source",
      });
      stageFrames.secondary = CL.stageFrame({
        state: coreState, channel: "secondary", paint: bundle.paint, tune: bundle.tune,
        n: localN("secondary"), both_scale_enabled: !!(profile() && profile().both_scale_enabled),
        both_scale: profile() && profile().both_scale, simulate_draft: true,
        local_stimulus: app.sourceDirty,
        source_in_flight: transaction === "source",
      });
    } else stageFrames = { primary: null, secondary: null };
    var comparison = CL.compareStageFrames(stageFrames.primary, stageFrames.secondary);
    renderComparison(comparison);
    setChannel("primary", stageFrames.primary, safetyBlocked, suppressChromaticPath);
    setChannel("secondary", stageFrames.secondary, safetyBlocked, suppressChromaticPath);
    drawStrip($("primaryCanvas"), stageFrames.primary, localN("primary"), safetyBlocked, suppressChromaticPath);
    drawStrip($("secondaryCanvas"), stageFrames.secondary, localN("secondary"), safetyBlocked, suppressChromaticPath);
    renderInspector(safetyBlocked || suppressChromaticPath);
    renderHandoff(bundle, safetyBlocked, policyBlocked);
    var secondaryLook = stageFrames.secondary && stageFrames.secondary.lookResolution;
    $("inheritDetail").textContent = secondaryLook && secondaryLook.relation === "inherit"
      ? "Secondary reports inherit and resolves " +
        (secondaryLook.effectiveKnown
          ? "effective look " + secondaryLook.effectiveSlot
          : "an unknown Primary look") + " inside its own frame."
      : "Secondary reports its own look directly; its frame remains independent.";
    drawCurve(bundle.tune, safetyBlocked);
    $("curveSummary").textContent = safetyBlocked
      ? "Transfer curve suppressed because the Device Safety gate failed."
      : "Browser parity model: red gain " + bundle.tune.gain_r.toFixed(3) +
        ", green gain " + bundle.tune.gain_g.toFixed(3) +
        ", blue gain " + bundle.tune.gain_b.toFixed(3) +
        ", gamma " + bundle.tune.gamma.toFixed(3) + ".";
    globalThis.__colourLabWorkbench = {
      app: app,
      coreState: coreState,
      decision: bundle.decision,
      safety: bundle.safety,
      policy: bundle.policy,
      currentPaint: bundle.paint,
      compiled: compiled,
      stageFrames: stageFrames,
      comparison: comparison,
      selectedLed: selectedLed,
      txCount: txCount,
      txTrace: txTrace.slice(),
      transaction: transaction,
      recoveryPending: recoveryPending(),
      legacyRecoveryGeneration: legacyRecoveryGeneration,
      legacyRecoveryOffGeneration: legacyRecoveryOffGeneration,
      legacyRecoveryStatusGeneration: legacyRecoveryStatusGeneration,
      legacyForbiddenDetected: legacyForbiddenDetected,
      testOnlyEmit: demo ? function (event) { consumeEvents([event]); } : null,
      testOnlySetFailCommand: demo ? function (command) { mockFailCommand = command; } : null,
      testOnlySetDevicePaintMode: demo ? function (mode) { mockDevice.paint.mode = mode; } : null,
      testOnlyHydrate: demo ? function () { return hydrate(); } : null,
      testOnlyDeviceLost: demo ? function () { applyCore({ type: "DEVICE_LOST" }); } : null,
      setSelectedLed: setSelectedLed,
      testOnlyApplyPalette: demo ? function (stops) {
        app.stimulus = "bounded";
        app.paletteStops = stops.map(function (stop) {
          return { position: stop.position, rgb: stop.rgb.slice() };
        });
        markSourceDirty();
      } : null,
    };
  }

  function bindPreviewStrip(which) {
    var canvas = $(which + "Canvas");
    function indexFromEvent(event) {
      var frame = stageFrames[which];
      if (!frame || !frame.pixels) return null;
      var box = canvas.getBoundingClientRect();
      return clamp(
        Math.floor((event.clientX - box.left) / box.width * frame.n),
        0,
        frame.n - 1
      );
    }
    canvas.addEventListener("pointermove", function (event) {
      if (event.pointerType !== "mouse" && !pointerActive) return;
      var index = indexFromEvent(event);
      if (index != null) setSelectedLed(index, "pointer", false);
    });
    canvas.addEventListener("pointerdown", function (event) {
      pointerActive = true;
      canvas.setPointerCapture(event.pointerId);
      var index = indexFromEvent(event);
      if (index != null) setSelectedLed(index, "pointer", false);
    });
    function release(event) {
      if (!pointerActive) return;
      pointerActive = false;
      if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
      announceSelection();
    }
    canvas.addEventListener("pointerup", release);
    canvas.addEventListener("pointercancel", release);
  }

  function bindSegment(hostId, key, dataKey) {
    $(hostId).querySelectorAll("button").forEach(function (button) {
      button.addEventListener("click", function () {
        app[key] = button.dataset[dataKey];
        $(hostId).querySelectorAll("button").forEach(function (candidate) {
          candidate.classList.toggle("active", candidate === button);
        });
        markSourceDirty();
      });
    });
  }

  function addLocalStop() {
    if (app.paletteStops.length >= 16) {
      toast("Local authoring is capped at 16 stops before compilation to eight.");
      return;
    }
    var largest = { gap: -1, index: 0 };
    for (var index = 1; index < app.paletteStops.length; index += 1) {
      var gap = app.paletteStops[index].position - app.paletteStops[index - 1].position;
      if (gap > largest.gap) largest = { gap: gap, index: index };
    }
    var position = (
      app.paletteStops[largest.index - 1].position + app.paletteStops[largest.index].position
    ) / 2;
    var rgb = u8(CA.interpolate(app.paletteStops, position, app.interpolation));
    app.paletteStops.splice(largest.index, 0, { position: position, rgb: rgb });
    markSourceDirty();
  }

  function removeLocalStop() {
    if (app.paletteStops.length <= 2) {
      toast("At least two palette stops are required.");
      return;
    }
    app.paletteStops.splice(app.paletteStops.length - 2, 1);
    markSourceDirty();
  }

  function exportStops() {
    var bundle = decisionBundle();
    if (!bundle.decision.exportAllowed) return;
    var compiled = compiledPalette();
    var line = CL.serialize.paintStops(compiled.paintStops);
    var payload = [
      "# SpectraSynq K1 Colour Lab · bounded palette export",
      "# source_stops=" + app.paletteStops.length + " compiled_stops=" +
        compiled.compiledStopCount + " interpolation=" + app.interpolation,
      "# max_channel_error_8=" + compiled.approximation.maxChannelError8 +
        " rms_channel_error_8=" + compiled.approximation.rmsChannelError8,
      line,
    ].join("\n") + "\n";
    var url = URL.createObjectURL(new Blob([payload], { type: "text/plain" }));
    var anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "k1-colourlab-paint-stops.txt";
    anchor.click();
    URL.revokeObjectURL(url);
    toast("Bounded ≤8-stop Paint export created.");
  }

  bindSegment("targetSeg", "target", "target");
  document.querySelectorAll("[data-stimulus]").forEach(function (button) {
    button.addEventListener("click", function () {
      app.stimulus = button.dataset.stimulus;
      document.querySelectorAll("[data-stimulus]").forEach(function (candidate) {
        candidate.classList.toggle("active", candidate === button);
      });
      markSourceDirty();
    });
  });
  document.querySelectorAll('input[name="previewView"]').forEach(function (input) {
    input.addEventListener("change", function () {
      app.view = input.value;
      render();
    });
  });
  document.querySelectorAll("#interpolationSeg button").forEach(function (button) {
    button.addEventListener("click", function () {
      app.interpolation = button.dataset.space;
      document.querySelectorAll("#interpolationSeg button").forEach(function (candidate) {
        candidate.classList.toggle("active", candidate === button);
      });
      markSourceDirty();
    });
  });
  ["solidR", "solidG", "solidB"].forEach(function (id) {
    $(id).addEventListener("input", markSourceDirty);
  });
  ["gainR", "gainG", "gainB", "gamma"].forEach(function (id) {
    $(id).addEventListener("input", markTuneDirty);
  });
  $("baseHue").addEventListener("input", function () {
    app.baseHue = Number(this.value);
    app.paletteStops = presetStops(app.baseHue);
    markSourceDirty();
  });
  $("addStopBtn").addEventListener("click", addLocalStop);
  $("removeStopBtn").addEventListener("click", removeLocalStop);
  $("exportBtn").addEventListener("click", exportStops);
  $("connectBtn").addEventListener("click", connect);
  $("disconnectBtn").addEventListener("click", disconnect);
  $("resyncBtn").addEventListener("click", resync);
  $("stopBtn").addEventListener("click", stopOutput);
  $("sendStimulusBtn").addEventListener("click", sendSourceTransaction);
  $("applyTuneBtn").addEventListener("click", applyTuneTransaction);
  $("saveBtn").addEventListener("click", saveTune);
  $("identityBtn").addEventListener("click", function () {
    syncTuneControls(CL.identityTune());
    markTuneDirty();
  });
  $("revertBtn").addEventListener("click", function () {
    if (!coreState.sessionBaseline) {
      toast("No session baseline exists yet.");
      return;
    }
    syncTuneControls(coreState.sessionBaseline);
    markTuneDirty();
  });
  $("selectedLedInput").addEventListener("input", function () {
    setSelectedLed(this.value, "number", true);
  });
  $("selectedLedInput").addEventListener("keydown", function (event) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    setSelectedLed(selectedLed + (event.key === "ArrowRight" ? 1 : -1), "number", true);
  });
  $("selectedLedInput").addEventListener("change", function () {
    setSelectedLed(this.value, "number", true);
  });
  bindPreviewStrip("primary");
  bindPreviewStrip("secondary");

  if (demo === "ready" || demo === "policy" || demo === "safety" ||
      demo === "transport" || demo === "bench") {
    var demoIsBench = demo === "bench";
    var fixturePrimaryLook = demoIsBench ? 0 : 15;
    var fixtureSecondaryLook = demoIsBench ? "inherit" : "unknown";
    var fixtureSlotKnown = previewFixture !== "slotUnknown" &&
      previewFixture !== "slotUnknownDirect";
    if (previewFixture === "inherit15" || previewFixture === "slotUnknown") {
      fixtureSecondaryLook = "inherit";
    } else if (previewFixture === "same" || previewFixture === "slotUnknownDirect") {
      fixtureSecondaryLook = 15;
    } else if (previewFixture === "inherit0") {
      fixturePrimaryLook = 0;
      fixtureSecondaryLook = "inherit";
    } else if (previewFixture === "inheritUnknown") {
      fixturePrimaryLook = "unknown";
      fixtureSecondaryLook = "inherit";
    } else if (previewFixture === "secondaryKnown") {
      fixturePrimaryLook = "unknown";
      fixtureSecondaryLook = 15;
    }
    var demoProfile = CL.resolveDeviceProfile({
      chip_id: demoIsBench ? "B489A500" : "9087A500",
      build_env: demoIsBench ? "k1_bench_im69d_led150" : "k1_main_rpl_im69d",
      look_env: demoIsBench ? "k1_bench_im69d_led150" : "k1_main_rpl_im69d",
      active_primary_look: fixturePrimaryLook,
      active_secondary_look: fixtureSecondaryLook,
    });
    coreState = CL.reduce(coreState, { type: "PROFILE_START" });
    coreState = CL.reduce(coreState, {
      type: "PROFILE_RESOLVED",
      profile: demoProfile,
      look: { slot: fixturePrimaryLook, sec: fixtureSecondaryLook },
    });
    coreState = CL.reduce(coreState, {
      type: "DEVICE_PAINT",
      paint: {
        mode: "off", target: "both", r: 140, g: 140, b: 140,
        s: 1, v: 0.55, stops: [],
      },
      seq: 1,
    });
    if (fixtureSlotKnown && !demoIsBench) {
      coreState = CL.reduce(coreState, {
        type: "DEVICE_TUNE",
        tune: Object.assign({}, mockDevice.tune),
        seq: 1,
        established_by: "tune_reset",
      });
    }
    coreState = CL.reduce(coreState, { type: "RESYNC_DONE" });
    syncTuneControls(mockDevice.tune);
    if (demo === "transport") setupQueue();
  }
  render();
}());
