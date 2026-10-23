// Every painted property is a function of seek(t). No CSS motion, no blur, no grain.
const W = 1920, H = 1080, FPS = 60;
const { $, set, vis, text, finish } = RM;
$('stage').style.width = W + 'px';
$('stage').style.height = H + 'px';

const WAVE_W = 1760, STRIP_W = 1760, STRIP_H = 88;

window.__ready = (async () => {
  const [doc, notes] = await Promise.all([
    fetch('scene-data.json').then(r => r.json()),
    fetch('annotations.json').then(r => r.json()),
  ]);
  const rate = doc.rate_hz, hopN = doc.hop_samples, px = doc.px, DUR = doc.duration_s;
  const pcm = Uint8Array.from(atob(doc.pcm_b64), c => c.charCodeAt(0));
  const native = Uint8Array.from(atob(doc.native_b64), c => c.charCodeAt(0));
  const pcmN = pcm.length / 2;
  const s16 = i => { const v = pcm[i * 2] | (pcm[i * 2 + 1] << 8); return v & 0x8000 ? v - 65536 : v; };
  const hops = doc.hops;
  const missing = new Set(doc.capture.missing_hops);
  const zeroAt = 7 * rate, returnAt = 10 * rate;
  const cols = WAVE_W;
  const peak = new Int16Array(cols * 2);
  const per = pcmN / cols;
  for (let x = 0; x < cols; x++) {
    let lo = 32767, hi = -32768;
    const a = Math.floor(x * per), b = Math.floor((x + 1) * per);
    for (let i = a; i < b; i++) {
      const s = s16(i);
      if (s < lo) lo = s;
      if (s > hi) hi = s;
    }
    peak[x * 2] = lo; peak[x * 2 + 1] = hi;
  }

  function sampleLimit(t) { return t * rate + 1e-9; }

  function rowAt(t) {
    const limit = sampleLimit(t);
    let chosen = -1;
    for (let i = 0; i < hops.length; i++) {
      if ((hops[i] + 1) * hopN <= limit) chosen = i;
      else break;
    }
    if (chosen < 0) return null;
    for (const lost of missing) {
      if (hops[chosen] < lost && (lost + 1) * hopN <= limit) return null;
    }
    return chosen;
  }

  function u16(row, edge, i, ch) {
    const off = (row * 2 * px + edge * px + i) * 6 + ch * 2;
    return native[off] | (native[off + 1] << 8);
  }

  function proj(c) { return Math.round(c * 255 / 65535); }

  function paintStrip(canvas, row, edge) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, STRIP_W, STRIP_H);
    const cell = STRIP_W / px;
    for (let i = 0; i < px; i++) {
      const r = proj(u16(row, edge, i, 0));
      const g = proj(u16(row, edge, i, 1));
      const b = proj(u16(row, edge, i, 2));
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.fillRect(Math.round(i * cell), 0, Math.ceil(cell), STRIP_H);
    }
  }

  function paintWave(t) {
    const ctx = $('wave').getContext('2d');
    ctx.clearRect(0, 0, WAVE_W, 120);
    const bands = [[0, 7, '#3a332b'], [7, 10, '#2a2d33'], [10, DUR, '#24302c']];
    for (const [a, b, fill] of bands) {
      ctx.fillStyle = fill;
      ctx.fillRect(a / DUR * WAVE_W, 0, (b - a) / DUR * WAVE_W, 120);
    }
    ctx.strokeStyle = '#ece7dc';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = 0; x < cols; x++) {
      const lo = 60 - (peak[x * 2 + 1] / 32768) * 56;
      const hi = 60 - (peak[x * 2] / 32768) * 56;
      ctx.moveTo(x + 0.5, lo);
      ctx.lineTo(x + 0.5, hi);
    }
    ctx.stroke();
    const x = Math.max(0, Math.min(WAVE_W - 1, t / DUR * WAVE_W));
    ctx.strokeStyle = '#e7c9a0';
    ctx.beginPath();
    ctx.moveTo(x + 0.5, 0);
    ctx.lineTo(x + 0.5, 120);
    ctx.stroke();
  }

  function ticks(id) {
    const host = $(id);
    host.textContent = '';
    const marks = [[0, '0', '0'], [80 / px * STRIP_W, '79–80', '-50%'], [STRIP_W, '159', '-100%']];
    for (const [left, label, shift] of marks) {
      const s = document.createElement('span');
      s.className = 'tick';
      s.style.left = left + 'px';
      s.style.transform = `translateX(${shift})`;
      s.textContent = label;
      host.appendChild(s);
    }
  }
  ticks('ticksA');
  ticks('ticksB');

  function triple(row, edge, i) {
    if (row == null) return '— / — / —';
    return `${u16(row, edge, i, 0)} / ${u16(row, edge, i, 1)} / ${u16(row, edge, i, 2)}`;
  }

  function paintEmpty(canvas) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, STRIP_W, STRIP_H);
    ctx.fillStyle = '#1a1e26';
    ctx.fillRect(0, 0, STRIP_W, STRIP_H);
    ctx.strokeStyle = '#343a46';
    ctx.lineWidth = 2;
    for (let x = -STRIP_H; x < STRIP_W; x += 16) {
      ctx.beginPath();
      ctx.moveTo(x, STRIP_H);
      ctx.lineTo(x + STRIP_H, 0);
      ctx.stroke();
    }
  }

  function seek(t) {
    t = Math.max(0, Math.min(DUR, t));
    const sample = Math.min(pcmN - 1, Math.floor(t * rate));
    const row = rowAt(t);
    text($('title'), 'K1 dual-edge replay — music, declared silence, return');
    text($('badge'), 'Recorded digital output • emulator');
    text($('sub'), 'Replay sample clock. Pre-audio startup is outside this interval. Colour is the display projection, not a light guide.');
    const phaseOf = s => s >= returnAt ? 'Return · original 149–155 s'
      : s >= zeroAt ? 'Declared zeros · digital zero, not musical silence'
      : 'Active music · original 130–137 s';
    const phase = phaseOf(sample);
    const picture = row == null ? '' : phaseOf((hops[row] + 1) * hopN - 1);
    const lag = row != null && picture !== phase ? '  ·  picture is still the previous hop' : '';
    const hopTxt = row == null ? 'no frame yet' : `hop ${hops[row]} · generation ${doc.generation[row]} · mode ${doc.mode[row]}`;
    text($('clock'), `${phase}\nt = ${t.toFixed(3)} s    sample ${sample}    ${hopTxt}${lag}`);
    $('clock').style.color = '#ece7dc';
    text($('labA'), 'EDGE A  ·  PRIMARY  ·  LOGICAL  ·  PIXEL 0 AT THE LEFT');
    text($('labB'), 'EDGE B  ·  SECONDARY  ·  LOGICAL  ·  PIXEL 0 AT THE LEFT');
    paintWave(t);
    const show = row != null;
    vis($('edgeA'), true);
    vis($('edgeB'), true);
    if (show) {
      paintStrip($('edgeA'), row, 0);
      paintStrip($('edgeB'), row, 1);
    } else {
      paintEmpty($('edgeA'));
      paintEmpty($('edgeB'));
    }
    let line = '';
    for (const item of notes.items) {
      if (t >= item.t && t < item.t + item.hold) line = item.text;
    }
    if (!show && !line) line = 'No captured frame at or before this replay time.';
    text($('callout'), line);
    const nativeLine = [
      'Native R / G / B',
      `A  79  ${triple(row, 0, 79)}    80  ${triple(row, 0, 80)}`,
      `A   0  ${triple(row, 0, 0)}   159  ${triple(row, 0, 159)}`,
      `B  79  ${triple(row, 1, 79)}    80  ${triple(row, 1, 80)}`,
      `B   0  ${triple(row, 1, 0)}   159  ${triple(row, 1, 159)}`,
    ].join('\n');
    text($('native'), nativeLine);
    text($('foot'), `Capture ${doc.invocation_id} · source ${doc.capture_source.head.slice(0, 12)} · not this checkout · epoch ${doc.epochs[0].epoch_us} µs is not an audio delay`);
    set($('callout'), { o: line ? 1 : 0 });
  }

  finish(seek, DUR, null);
})();
