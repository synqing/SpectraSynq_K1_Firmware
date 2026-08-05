/* HALO — layer-isolating radial renderer for the K718 Remoted.
 * Purpose: every design LAYER is an independent, toggleable element so each can be
 * shown ALONE for inspection (the "rip it out and look at it" guide). Compose any subset.
 * RULE: all ring/section text CURVES to its radius; only the central readout is straight.
 * Canvas 480px (Ø60mm @ 8px/mm). Each layer is a function returning SVG for just that layer.
 */
const HALO = (() => {
  const DESIGN = 480, R = 240, SAFE_R = 226;
  const BAND = { nav:[226,188], control:[188,138], core:[138,70], readout:[70,0] };
  const rad = d => (d - 90) * Math.PI / 180;
  const pt  = (r, deg) => [R + r*Math.cos(rad(deg)), R + r*Math.sin(rad(deg))];
  const clock = h => h*30;
  const esc = s => String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  const f = n => n.toFixed(1);
  function arcPath(r,a0,a1,sweep=1){ const [x0,y0]=pt(r,a0),[x1,y1]=pt(r,a1); const lg=Math.abs((a1-a0)%360)>180?1:0; return `M ${f(x0)} ${f(y0)} A ${r} ${r} 0 ${lg} ${sweep} ${f(x1)} ${f(y1)}`; }

  // ── curved text (all ring labels) ─────────────────────────────
  let PID = 0;
  function curved(label, r, centerDeg, cls, opts={}) {
    const id='cp'+(++PID); const c=((centerDeg%360)+360)%360; const flip=(c>90&&c<270);
    const span=Math.min(opts.maxSpan||160, Math.max(12,label.length*(opts.perChar||3.0))); const h=span/2;
    const a0=flip?c+h:c-h, a1=flip?c-h:c+h, sw=flip?0:1; const [x0,y0]=pt(r,a0),[x1,y1]=pt(r,a1);
    return `<path id="${id}" d="M ${f(x0)} ${f(y0)} A ${r} ${r} 0 0 ${sw} ${f(x1)} ${f(y1)}" fill="none"/><text class="${cls}"><textPath href="#${id}" startOffset="50%" text-anchor="middle">${esc(label)}</textPath></text>`;
  }

  // ── LAYER functions (each renders ONE layer, in isolation) ────
  const L = {
    face(){ return `<circle cx="${R}" cy="${R}" r="${R}" fill="#000"/><circle cx="${R}" cy="${R}" r="${R-4}" fill="var(--bg-base)" stroke="var(--bg-ring)" stroke-width="6"/><circle cx="${R}" cy="${R}" r="${R-6}" fill="none" stroke="var(--c1,var(--accent-focus))" stroke-width="1" opacity="0.22"/>`; },

    grid(){ let g=`<circle cx="${R}" cy="${R}" r="${SAFE_R}" fill="none" stroke="var(--accent-focus)" stroke-dasharray="3 7" stroke-width="1.4" opacity="0.7"/>`;
      [226,188,138,70].forEach(o=>g+=`<circle cx="${R}" cy="${R}" r="${o}" fill="none" stroke="var(--bg-hairline)" stroke-width="1" opacity="0.7"/>`);
      [0,90,180,270].forEach(d=>{const[x,y]=pt(SAFE_R,d);g+=`<line x1="${R}" y1="${R}" x2="${f(x)}" y2="${f(y)}" stroke="var(--bg-hairline)" stroke-width="0.75" opacity="0.4"/>`;});
      g+=`<path d="${arcPath(214,clock(6),clock(9))}" stroke="var(--status-down)" stroke-width="6" fill="none" opacity="0.16" stroke-linecap="round"/><path d="${arcPath(214,clock(3),clock(6))}" stroke="var(--accent-focus)" stroke-width="6" fill="none" opacity="0.16" stroke-linecap="round"/>`; return g; },

    navLabels(labels){ const slots=[0,clock(2.2),clock(4),-clock(4),-clock(2.2)]; return labels.slice(0,5).map((l,i)=>curved(l,205,slots[i]??0,'nav-label')).join(''); },

    ticks(n=60,r=218){ let o=''; for(let i=0;i<n;i++){const a=-90+(360/n)*i;const major=i%5===0;const[x0,y0]=pt(r,a),[x1,y1]=pt(r-(major?10:5),a);o+=`<line x1="${f(x0)}" y1="${f(y0)}" x2="${f(x1)}" y2="${f(y1)}" stroke="var(--bg-hairline)" stroke-width="${major?1.6:0.8}" opacity="${major?0.9:0.5}"/>`;} return o; },

    dotRing(r=168,count=36,pos=null){ let o=''; const m=pos==null?-1:Math.round(pos*count)%count; for(let i=0;i<count;i++){const[x,y]=pt(r,-90+(360/count)*i);const on=i===m;o+=`<circle cx="${f(x)}" cy="${f(y)}" r="${on?4.4:2.4}" fill="${on?'var(--accent-focus)':'var(--bg-hairline)'}"${on?' filter="url(#glow)"':''}/>`;} return o; },

    needle(pos=0.5,r=176){ const a=-90+pos*360;const[x,y]=pt(r,a);const[bx,by]=pt(28,a+180); return `<line x1="${f(bx)}" y1="${f(by)}" x2="${f(x)}" y2="${f(y)}" stroke="var(--accent-focus)" stroke-width="3" stroke-linecap="round" filter="url(#glow)"/><circle cx="${R}" cy="${R}" r="6" fill="var(--accent-focus)"/>`; },

    activeArc(frac=0.6,r=184){ return `<path d="${arcPath(r,-90,-90+360*frac)}" stroke="var(--accent-active,var(--accent-focus))" stroke-width="5" fill="none" stroke-linecap="round" filter="url(#glow)"/>`; },
    focusRing(r=184){ return `<circle cx="${R}" cy="${R}" r="${r}" fill="none" stroke="var(--accent-focus)" stroke-width="2.5" opacity="0.85" filter="url(#glow)"/>`; },
    confirmRing(r=184){ return `<circle cx="${R}" cy="${R}" r="${r}" fill="none" stroke="var(--status-ok)" stroke-width="4" opacity="0.95" filter="url(#glow)"/>`; },

    truthRing(r=168,count=36){ const cols=['var(--tz-pending,#FF4FD8)','var(--tz-near,#FF9A2E)','var(--tz-ready,#2DD4F5)']; let o=''; for(let i=0;i<count;i++){const[x,y]=pt(r,-90+(360/count)*i);o+=`<circle cx="${f(x)}" cy="${f(y)}" r="3" fill="${cols[Math.floor(i/count*3)]}" filter="url(#glow)"/>`;} return o; },

    signalCore(seed=1.3){ const n=42; let o=''; for(let i=0;i<n;i++){const t=i/(n-1);const s=0.25+0.7*Math.abs(Math.sin(seed*1.7+t*7.2))*Math.pow(1-t*0.55,1.3);const x=R-118+(236/(n-1))*i;const hgt=14+s*70;o+=`<rect x="${f(x)}" y="${f(R+96-hgt)}" width="3.2" height="${f(hgt)}" rx="1.4" fill="var(--c3,var(--accent-focus))" opacity="0.9"/>`;} return o; },

    readout(v,unit){ let o=`<text x="${R}" y="${R+(unit?-4:18)}" class="readout-val" text-anchor="middle">${esc(v)}</text>`; if(unit)o+=`<text x="${R}" y="${R+30}" class="readout-unit" text-anchor="middle">${esc(unit)}</text>`; return o; },

    ble(state){ const col=state==='down'?'var(--status-down)':'var(--status-ok)'; const bt='M17.71 7.71L12 2h-1v7.59L6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 11 14.41V22h1l5.71-5.71-4.3-4.29 4.3-4.29zM13 5.83l1.88 1.88L13 9.59V5.83zm1.88 10.46L13 18.17v-3.76l1.88 1.88z'; return `<g transform="translate(${R-13},22) scale(1.1)"><circle cx="12" cy="12" r="17" fill="none" stroke="${col}" stroke-width="1.4" opacity="0.5"/><path d="${bt}" fill="${col}" filter="url(#glow)"/></g>`; },

    statusBadge(label,col){ const c=col||'var(--accent-focus)'; return `<rect x="${R-34}" y="14" width="68" height="26" rx="13" fill="none" stroke="${c}" stroke-width="1.5"/><text x="${R}" y="31" class="badge" fill="${c}" text-anchor="middle">${esc(label)}</text>`; },

    promotionLane(text){ return `<rect x="${R-118}" y="${R+118}" width="236" height="40" rx="8" fill="var(--bg-raised)" stroke="var(--accent-focus)" stroke-width="1.2"/><text x="${R}" y="${R+143}" class="lane" fill="var(--accent-focus)" text-anchor="middle">${esc(text)}</text><text x="${R-104}" y="${R+143}" class="lane-arrow" fill="var(--accent-focus)">‹‹</text><text x="${R+104}" y="${R+143}" class="lane-arrow" fill="var(--accent-focus)" text-anchor="end">››</text>`; },

    alert(){ return `<circle cx="${R}" cy="${R}" r="${R-6}" fill="none" stroke="var(--status-down)" stroke-width="3" opacity="0.9" filter="url(#glow)"/><path d="M ${R} ${R+44} l 14 24 h -28 z" fill="none" stroke="var(--status-down)" stroke-width="2"/><text x="${R}" y="${R+64}" class="badge" fill="var(--status-down)" text-anchor="middle">!</text>`; },

    stateEdge(text){ return curved(text,158,180,'state-edge'); },
  };

  function dial(cfg={}) {
    const size=cfg.size||300, T=cfg.theme||cfg.territory||'measurement-grade';
    let s = L.face();
    if (cfg.showGrid) s += L.grid();
    if (cfg.ticks) s += L.ticks(cfg.ticks===true?60:cfg.ticks);
    if (cfg.navLabels) s += L.navLabels(cfg.navLabels);
    if (cfg.truthRing) s += L.truthRing();
    else if (cfg.dots !== false) s += L.dotRing(168, cfg.dots||36, cfg.pos);
    if (cfg.activeArc != null) s += L.activeArc(cfg.activeArc);
    if (cfg.focusRing) s += L.focusRing();
    if (cfg.confirmRing) s += L.confirmRing();
    if (cfg.needle != null) s += L.needle(cfg.needle);
    if (cfg.core) s += L.signalCore(cfg.seed);
    if (cfg.readout) s += L.readout(cfg.readout.value, cfg.readout.unit);
    if (cfg.ble) s += L.ble(cfg.ble);
    if (cfg.status) s += L.statusBadge(cfg.status.label, cfg.status.color);
    if (cfg.promotionLane) s += L.promotionLane(cfg.promotionLane);
    if (cfg.alert) s += L.alert();
    if (cfg.stateEdge) s += L.stateEdge(cfg.stateEdge);
    return `<svg viewBox="0 0 ${DESIGN} ${DESIGN}" width="${size}" height="${size}" class="dial" data-theme="${T}" data-territory="${cfg.territory||T}">
      <defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>${s}</svg>`;
  }

  function mountAll(){ document.querySelectorAll('[data-halo]').forEach(el=>{ try{ el.innerHTML=dial(JSON.parse(el.getAttribute('data-halo'))); }catch(e){ el.innerHTML=`<pre style="color:#FF4D4D">config error: ${e.message}</pre>`; } }); }
  return { dial, mountAll, layers:L, pt, clock };
})();
if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', HALO.mountAll);
