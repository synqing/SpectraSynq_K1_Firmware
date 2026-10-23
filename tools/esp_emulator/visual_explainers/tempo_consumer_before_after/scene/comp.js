// Film clock is the retained hop-end audio clock. seek(t) only reads immutable
// evidence plus the annotation file. LED colours are the display projection of
// the latest captured frame at or before t. Nothing is interpolated.
const W = 1920, H = 1080, DUR = 10, FPS = 60;
const { $, set, vis, text, ease, inv, clamp, finish } = RM;
$('stage').style.width = W + 'px';
$('stage').style.height = H + 'px';

const PX = 160;
let data = null;

function b64(s) {
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function latest(frames, t) {
  let lo = 0, hi = frames.length - 1, ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].rel_s <= t + 1e-9) { ans = mid; lo = mid + 1; }
    else hi = mid - 1;
  }
  return ans;
}

function paint(canvas, rgb, frameIndex, edge) {
  const ctx = canvas.getContext('2d', { alpha: false });
  const img = ctx.createImageData(PX, 16);
  const d = img.data;
  if (frameIndex < 0) {
    d.fill(0);
    for (let i = 3; i < d.length; i += 4) d[i] = 255;
  } else {
    const off = (frameIndex * 2 + edge) * PX * 3;
    for (let x = 0; x < PX; x++) {
      const r = rgb[off + x * 3], g = rgb[off + x * 3 + 1], b = rgb[off + x * 3 + 2];
      for (let y = 0; y < 16; y++) {
        const p = (y * PX + x) * 4;
        d[p] = r; d[p + 1] = g; d[p + 2] = b; d[p + 3] = 255;
      }
    }
  }
  ctx.putImageData(img, 0, 0);
}

function lockText(frame) {
  if (!frame) return 'published lock — no frame yet';
  return frame.locked ? 'published lock true' : 'published lock false';
}

function estText(frame) {
  if (!frame) return '';
  // Four decimal places: 0.5999 is below the 0.60 display boundary. Rounding
// it to 0.60 made the estimate look like it had crossed that line. The lock
// badge reads frame.locked only.
return 'estimate ' + frame.bpm.toFixed(1) + ' BPM · confidence ' + frame.conf.toFixed(4) + ' · tentative';
}

function showCaption(el, t, start, hold, label) {
  const on = t >= start && t < start + hold;
  vis(el, on);
  text(el, on ? label : '');
  const fadeOut = 1 - ease.inCubic(inv(start + hold - 0.25, start + hold, t));
  set(el, { o: on ? clamp(fadeOut) : 0 });
}

function seek(t) {
  if (!data) return;
  const b = latest(data.before, t);
  const a = latest(data.after, t);
  paint($('led-ba'), data.beforeRgb, b, 0);
  paint($('led-bb'), data.beforeRgb, b, 1);
  paint($('led-aa'), data.afterRgb, a, 0);
  paint($('led-ab'), data.afterRgb, a, 1);
  const bf = b < 0 ? null : data.before[b];
  const af = a < 0 ? null : data.after[a];
  text($('lock-before'), lockText(bf));
  text($('lock-after'), lockText(af));
  text($('est-before'), estText(bf));
  text($('est-after'), estText(af));
  text($('clock'), 'source time ' + (68 + t).toFixed(3) + ' s    film ' + t.toFixed(3) + ' / ' + DUR.toFixed(3) + ' s');
  set($('cursor'), { x: (t / DUR) * 1792, o: 1 });
  const ann = data.ann;
  showCaption($('cap-before'), t, data.falseCue + ann.false_cue.offset_s, ann.false_cue.hold, ann.false_cue.text);
  showCaption($('cap-after'), t, data.onset + ann.onset.offset_s, ann.onset.hold, ann.onset.text);
  showCaption($('ending'), t, ann.ending.t, ann.ending.hold, ann.ending.text);
  vis($('mark-ba'), true); vis($('mark-bb'), true); vis($('mark-aa'), true); vis($('mark-ab'), true);
  set($('mark-ba'), { o: 1 }); set($('mark-bb'), { o: 1 }); set($('mark-aa'), { o: 1 }); set($('mark-ab'), { o: 1 });
}

function drawRuler() {
  const canvas = document.createElement('canvas');
  canvas.width = 1792; canvas.height = 48;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#1d1a16';
  ctx.fillRect(0, 0, 1792, 48);
  ctx.fillStyle = '#7ea8c4';
  for (const s of data.bass) {
    const x = (s / DUR) * 1792;
    ctx.fillRect(x, 8, 2, 14);
  }
  ctx.fillStyle = '#d35b4a';
  for (const s of data.predicted) {
    const x = (s / DUR) * 1792;
    ctx.fillRect(x, 26, 2, 16);
  }
  $('ruler').appendChild(canvas);
  canvas.style.width = '1792px';
  canvas.style.height = '48px';
  canvas.style.display = 'block';
}

window.__ready = (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => {
  const ev = window.EVIDENCE;
  const ann = window.ANNOTATIONS;
  const meta = ev.meta;
  data = {
    before: meta.before.frames,
    after: meta.after.frames,
    beforeRgb: b64(ev.beforeB64),
    afterRgb: b64(ev.afterB64),
    bass: meta.before.bass_rel_s,
    predicted: meta.before.edges.tempo_comet.predicted_rel_s,
    falseCue: meta.before.edges.tempo_comet.predicted_rel_s[0],
    onset: meta.after.edges.tempo_comet.launch_rel_s.find(s => s >= meta.before.edges.tempo_comet.predicted_rel_s[0]),
    ann: ann,
  };
  const wb = meta.whole_case;
  text($('coord'), 'fixture loreen_127 · original 68.000–78.000 s · 1× · both sides, one sample map · published lock fraction 0 and 0');
  text($('totals'), 'Whole captured case — bass onsets ' + wb.bass_onsets[0]
    + ' · Comet launches ' + wb.comet_launches[0] + ' → ' + wb.comet_launches[1]
    + ' · detected predicted cues ' + wb.comet_predicted[0] + ' → ' + wb.comet_predicted[1]
    + ' · Anticipate detected launches ' + wb.anticipate_launches_detected[0] + ' → ' + wb.anticipate_launches_detected[1]);
  text($('la-b'), 'B · Tempo Comet Anticipate · ' + wb.anticipate_launches_detected[0] + ' detected launches');
  text($('ra-b'), 'B · Tempo Comet Anticipate · ' + wb.anticipate_launches_detected[1] + ' detected launches, 0 predicted');
  drawRuler();
  // Static labels are set once from immutable evidence. seek still rewrites
  // every time-varying property on every call.
  text($('title'), 'Why turning lock off did not stop false beat cues');
  text($('kicker'), 'RECORDED DIGITAL OUTPUT · EMULATOR');
  text($('legend'), 'Time ruler: blue ticks are consumed bass onsets · red ticks are detected predicted cues · the white bar is the shared source-time cursor. Edges are logical names, not a claim about the physical plate.');
  text($('open'), 'DEF-002 stays open. This film does not show a recovered tempo lock.');
  text($('blind'), '0 detected Anticipate launches on the unrepaired side. This detector misses eased heads, so zero is not proof the edge was idle.');
});

finish(seek, DUR, null);
