// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// K718 HALO Phase 1 controller shell. Built to K718-UX-LAWS.md:
//   LAW 1  no status/PEND/CONF/link text on glass (link → physical LED ring)
//   LAW 2  nothing in the centre bullseye but the visual
//   LAW 3  no on-screen rim dots (physical LED ring owns the rim)
//   LAW 4  centre is a deliberately AMBIENT field — no canned BPM, not "beat-reactive"
//   LAW 5  single-hand: rotary adjusts/scrubs; coarse swipes navigate; radial picker
//   LAW 6  generated truth only — 5 committed presets, mode = numeric ordinal here
//
// Render keeps the proven split: PSRAM face canvas (chrome + peripheral value/picker,
// recomposed on state change) + a small INTERNAL-SRAM ambient field canvas (~24 fps).
#include "remoted_dashboard.h"

#include <Arduino.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "esp_heap_caps.h"

#include "K1BleMidiMap.h"
#include "remoted_control.h"
#include "k718_feedback.h"

#ifndef K718_FX_SIZE
#define K718_FX_SIZE 144
#endif
#ifndef K718_FX_FRAME_MS
#define K718_FX_FRAME_MS 42U
#endif

// ── geometry (§9) ──
static const int SC = 360, CX = 180, CY = 180, R_SCREEN = 180;
static const float DEG = 0.01745329252f;
static const int NOTCH = 18;
static const int R_BORDER = 175;
static const int VALUE_ARC_R = 152, VALUE_ARC_W = 8;
static const int VALUE_ARC_START = 216, VALUE_ARC_SWEEP = 288;
static const int PICKER_R = 150;

// ── perf telemetry (read by knob.cpp PERF line) ──
volatile uint32_t g_compose_us = 0, g_compose_max_us = 0, g_compose_frames = 0; // ambient fx
volatile uint32_t g_face_us = 0, g_face_count = 0;                              // face recompose

// ── function model (LAW 6: no hand-typed mode/preset lists) ──
enum { K_VAL, K_ENUM, K_TOG, K_PRESET, K_LOCAL };
enum { G_LOOK, G_FEEL, G_LEVEL, G_STAGE, G_KNOB };
enum {
  FN_MODE = 0, FN_PALETTE, FN_PHOTONS, FN_CHROMA, FN_MOOD, FN_SATURATION,
  FN_BRIGHTNESS, FN_SENSITIVITY, FN_EDGE, FN_MIRROR, FN_VISUAL_FIELD, FN_PRESET,
  FN_SETTINGS, FN_COUNT
};
struct Fn { const char* name; uint8_t kind; bool per_channel; uint8_t group;
            uint8_t emax; const char* path_pri; const char* path_sec; };
static const Fn FN[FN_COUNT] = {
  { "MODE",        K_ENUM,   true,  G_LOOK,  29, "primary.mode",            "secondary.mode" },
  { "PALETTE",     K_ENUM,   true,  G_LOOK,  7,  "primary.palette",         "secondary.palette" },
  { "PHOTONS",     K_VAL,    true,  G_FEEL,  100,"primary.photons",         "secondary.photons" },
  { "CHROMA",      K_VAL,    true,  G_FEEL,  100,"primary.chroma",          "secondary.chroma" },
  { "MOOD",        K_VAL,    true,  G_FEEL,  100,"primary.mood",            "secondary.mood" },
  { "SATURATION",  K_VAL,    true,  G_FEEL,  100,"primary.saturation",      "secondary.saturation" },
  { "BRIGHTNESS",  K_VAL,    false, G_LEVEL, 100,"global.master_brightness", nullptr },
  { "SENSITIVITY", K_VAL,    false, G_LEVEL, 100,"global.sensitivity",       nullptr },
  { "EDGE LIGHT",  K_TOG,    false, G_STAGE, 1,  "edge.enabled",            nullptr },
  { "MIRROR",      K_TOG,    true,  G_STAGE, 1,  "primary.mirror",          "secondary.mirror" },
  { "VISUAL FIELD",K_LOCAL,  false, G_KNOB,  5,  nullptr,                   nullptr },
  { "PRESET",      K_PRESET, false, G_STAGE, 4,  "primary.preset",          nullptr },
  { "SETTINGS",    K_LOCAL,  false, G_KNOB,  0,  nullptr,                   nullptr },
};

// ── state ──
struct Dash {
  uint8_t view;            // 0 home, 1 picker
  uint8_t func, picker;    // active / highlighted
  uint8_t channel;         // 0 pri, 1 sec
  uint8_t val[FN_COUNT][2];
  bool ble, face_dirty;
  uint32_t last_fx_ms, t0;
  int16_t tx, ty; uint32_t tt; bool touching;
};
static Dash s;

static lv_color_t* s_face_buf = nullptr;
static lv_color_t* s_fx_buf = nullptr;
static lv_obj_t* s_face = nullptr;
static lv_obj_t* s_fx = nullptr;
static int s_fx_size = 0;
static uint16_t s_key = 0;                 // chroma key
static lv_obj_t* s_keel = nullptr;         // function name (peripheral, bottom)
static lv_obj_t* s_keelval = nullptr;      // value text   (peripheral, bottom)

static inline int clampi(int v, int lo, int hi){ return v<lo?lo:(v>hi?hi:v); }
static inline uint16_t rgb565(uint8_t r,uint8_t g,uint8_t b){ return lv_color_make(r,g,b).full; }
static inline void setpx(uint16_t* p,int x,int y,uint16_t v){ if((unsigned)x<(unsigned)SC&&(unsigned)y<(unsigned)SC) p[y*SC+x]=v; }

static lv_color_t* alloc_fx(int* outsz){
  int sizes[] = { K718_FX_SIZE, 136, 128, 112, 96 };
  for (unsigned i=0;i<sizeof(sizes)/sizeof(sizes[0]);++i){
    lv_color_t* p=(lv_color_t*)heap_caps_malloc((size_t)sizes[i]*sizes[i]*sizeof(lv_color_t), MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT);
    if(p){ *outsz=sizes[i]; return p; }
  }
  *outsz=128;
  return (lv_color_t*)heap_caps_malloc(128*128*sizeof(lv_color_t), MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
}

// thin arc band, angle in degrees (0 = up, clockwise)
static void arc_band(uint16_t* b,int r,float a0,float a1,float w,uint16_t v){
  float step=(0.8f/r)*57.2958f;
  for(float a=a0;a<=a1;a+=step){ float t=(a-90.0f)*DEG, c=cosf(t), si=sinf(t);
    for(float rr=r-w*0.5f;rr<=r+w*0.5f;rr+=1.0f) setpx(b,(int)(CX+rr*c+0.5f),(int)(CY+rr*si+0.5f),v); }
}
static void filldot(uint16_t* b,float cx,float cy,float rad,uint16_t v){
  for(int y=(int)(cy-rad);y<=(int)(cy+rad);++y) for(int x=(int)(cx-rad);x<=(int)(cx+rad);++x){
    float dx=x-cx,dy=y-cy; if(dx*dx+dy*dy<=rad*rad) setpx(b,x,y,v); }
}

static uint16_t group_color(uint8_t g){
  switch(g){ case G_LOOK:return rgb565(0x00,0xAE,0xCF); case G_FEEL:return rgb565(0xEF,0xA0,0x20);
    case G_LEVEL:return rgb565(0x28,0xB7,0x6E); case G_STAGE:return rgb565(0x7C,0x5C,0xFF);
    default:return rgb565(0x58,0x62,0x73); }   // KNOB / local = muted (visibly separated)
}
static inline uint8_t chan_of(uint8_t fn){ return FN[fn].per_channel ? s.channel : 0; }

// ── BLE emit (generated map, coalesced) ──
static float ui_to_ble(uint8_t fn, int v){
  switch(fn){ case FN_PHOTONS: return 0.05f + 0.0095f*v;
    case FN_CHROMA: case FN_MOOD: case FN_SATURATION: case FN_BRIGHTNESS: case FN_SENSITIVITY: return v/100.0f;
    default: return (float)v; }                 // enum/preset/tog ordinal
}
static void emit_active(void){
  const Fn& f = FN[s.func];
  const char* path = (s.channel==1 && f.path_sec) ? f.path_sec : f.path_pri;
  if(!path) return;                              // LOCAL (VISUAL FIELD / SETTINGS) — no K1 send
  int idx = remoted_control_find_path(path);
  if(idx < 0) return;
  remoted_control_queue_emit_index(idx, ui_to_ble(s.func, s.val[s.func][chan_of(s.func)]), false);
}

// preset committed name from the generated map (never hand-typed)
static const char* preset_name(int ord){
  int idx = remoted_control_find_path("primary.preset");
  if(idx < 0) return "";
  const K1BleMidiEntry& e = kK1BleMidiMap[idx];
  if(e.text_count <= 0) return "";
  if(ord < 0) ord = 0; if(ord >= e.text_count) ord = e.text_count-1;
  return kK1BleMidiTextValues[e.text_index + ord];
}

// ── ambient field (LAW 4: no BPM, free-running phase) ──
static void render_fx(uint16_t* b,int sz,float t,uint16_t tint){
  int c=sz/2, fr=c-2, fr2=fr*fr;
  for(int y=0;y<sz;++y){ int dy=y-c, dy2=dy*dy; for(int x=0;x<sz;++x){ int dx=x-c, d2=dx*dx+dy2;
    if(d2>fr2){ b[y*sz+x]=s_key; continue; }
    float d=sqrtf((float)d2), a=atan2f((float)dy,(float)dx);
    float inten=0.0f;
    for(int k=0;k<3;++k){ float rr=fr*0.55f + sinf(a*2.0f+t*0.9f+k*1.7f)*fr*0.16f + sinf(a*3.0f-t*0.6f+k)*fr*0.06f;
      float e=1.0f-fabsf(d-rr)/6.0f; if(e>0.0f) inten+=e*(0.18f+0.05f*k); }
    if(inten>1.0f) inten=1.0f;
    uint8_t tr=(tint>>11)&0x1F, tg=(tint>>5)&0x3F, tb=tint&0x1F;     // 565 channels
    int rr=(int)(2 + (tr<<3)*inten*0.5f), gg=(int)(3 + (tg<<2)*inten), bb=(int)(4 + (tb<<3)*inten);
    b[y*sz+x]=rgb565((uint8_t)clampi(rr,0,255),(uint8_t)clampi(gg,0,255),(uint8_t)clampi(bb,0,255)); } }
}

// ── static face: chrome + (home: value arc) | (picker: radial sectors) ──
static void render_face(uint16_t* b){
  for(int y=0;y<SC;++y){ int dy=y-CY, dy2=dy*dy; for(int x=0;x<SC;++x){ int dx=x-CX, d2=dx*dx+dy2;
    if(d2>R_SCREEN*R_SCREEN){ b[y*SC+x]=0; continue; }
    float td=sqrtf((float)d2)/R_SCREEN;
    b[y*SC+x]=rgb565((uint8_t)(12-10*td),(uint8_t)(12-10*td),(uint8_t)(16-13*td)); } }
  arc_band(b,R_BORDER,0,360,3.0f,rgb565(0x16,0x1b,0x25));

  if(s.view==1){
    // RADIAL picker — 13 group-coloured sector marks; highlighted one bright (LAW 5)
    for(int i=0;i<FN_COUNT;++i){ float deg=(float)i*(360.0f/FN_COUNT);
      float t=(deg-90.0f)*DEG, px=CX+PICKER_R*cosf(t), py=CY+PICKER_R*sinf(t);
      uint16_t col=group_color(FN[i].group);
      if(i==s.picker) filldot(b,px,py,7.0f,col); else filldot(b,px,py,3.0f,col); }
    return;
  }

  // HOME — peripheral value arc (LAW 2: value lives on the rim, never the centre)
  const Fn& f=FN[s.func];
  uint16_t col=group_color(f.group);
  arc_band(b,VALUE_ARC_R,VALUE_ARC_START,VALUE_ARC_START+VALUE_ARC_SWEEP,VALUE_ARC_W*0.5f,rgb565(0x1b,0x21,0x2e));
  int v=s.val[s.func][chan_of(s.func)];
  float frac = f.emax ? (float)v/(float)f.emax : 0.0f;
  if(frac>0.0f) arc_band(b,VALUE_ARC_R,VALUE_ARC_START,VALUE_ARC_START+VALUE_ARC_SWEEP*frac,VALUE_ARC_W*0.5f,col);
}

static void update_keel(void){
  if(s.view==1){ lv_label_set_text(s_keel, FN[s.picker].name); lv_label_set_text(s_keelval, ""); return; }
  const Fn& f=FN[s.func];
  lv_label_set_text(s_keel, f.name);
  int v=s.val[s.func][chan_of(s.func)];
  char buf[24];
  switch(f.kind){
    case K_VAL:    snprintf(buf,sizeof(buf),"%d%%", v); break;
    case K_TOG:    snprintf(buf,sizeof(buf),"%s", v?"ON":"OFF"); break;
    case K_PRESET: snprintf(buf,sizeof(buf),"%s", preset_name(v)); break;
    case K_ENUM:   snprintf(buf,sizeof(buf),"%d", v); break;          // MODE/PALETTE numeric (MODE_NAMES_BLOCKED)
    case K_LOCAL:  if(s.func==FN_VISUAL_FIELD) snprintf(buf,sizeof(buf),"FIELD %d", v);
                   else snprintf(buf,sizeof(buf),"%s","—");
                   break;
    default: buf[0]=0;
  }
  lv_label_set_text(s_keelval, buf);
  // channel shown by tint of the value text — never PRI/SEC glass tabs
  uint16_t cc = (s.channel==1) ? 0x586273 : 0x00AECF;
  lv_obj_set_style_text_color(s_keelval, lv_color_hex(f.per_channel ? cc : 0x9aa3b2), 0);
}

static void compose_face_if_needed(void){
  if(!s.face_dirty || !s_face_buf) return;
  uint32_t t0=micros();
  render_face((uint16_t*)s_face_buf);
  lv_obj_invalidate(s_face);
  s.face_dirty=false;
  update_keel();
  g_face_us += micros()-t0; g_face_count++;
}

// ── public API ──
void remoted_dashboard_build(lv_obj_t* parent){
  memset(&s,0,sizeof(s));
  s.func=FN_MODE; s.view=0; s.channel=0;
  uint8_t defs[FN_COUNT]={0,0,74,60,48,88,80,65,1,0,1,0,0};
  for(int i=0;i<FN_COUNT;++i){ s.val[i][0]=defs[i]; s.val[i][1]=defs[i]; }
  s_key = lv_color_hex(0x00ff00).full;

  lv_obj_set_style_bg_color(parent, lv_color_hex(0x000000), 0);
  s_face_buf=(lv_color_t*)heap_caps_malloc((size_t)SC*SC*sizeof(lv_color_t), MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
  s_fx_buf=alloc_fx(&s_fx_size);
  if(!s_face_buf || !s_fx_buf){ Serial.printf("DASH_INIT FAILED face=%p fx=%p\n",(void*)s_face_buf,(void*)s_fx_buf); return; }

  s_face=lv_canvas_create(parent);
  lv_canvas_set_buffer(s_face,s_face_buf,SC,SC,LV_IMG_CF_TRUE_COLOR);
  lv_obj_center(s_face);
  s_fx=lv_canvas_create(parent);
  lv_canvas_set_buffer(s_fx,s_fx_buf,s_fx_size,s_fx_size,LV_IMG_CF_TRUE_COLOR_CHROMA_KEYED);
  lv_obj_center(s_fx);

  // peripheral keel labels — bottom, NEVER centre (LAW 2)
  s_keelval=lv_label_create(parent);
  lv_obj_set_style_text_font(s_keelval,&lv_font_montserrat_22,0);
  lv_obj_set_style_text_color(s_keelval,lv_color_hex(0xEDE9E3),0);
  lv_obj_align(s_keelval,LV_ALIGN_BOTTOM_MID,0,-46);
  s_keel=lv_label_create(parent);
  lv_obj_set_style_text_font(s_keel,&lv_font_montserrat_14,0);
  lv_obj_set_style_text_color(s_keel,lv_color_hex(0x9aa3b2),0);
  lv_obj_align(s_keel,LV_ALIGN_BOTTOM_MID,0,-26);

  s.t0=millis(); s.face_dirty=true;
  render_fx((uint16_t*)s_fx_buf,s_fx_size,0.0f,group_color(G_LOOK));
  compose_face_if_needed();
  Serial.printf("DASH_INIT halo canvas=360x360 face=psram fx=%dx%d fx_mem=%s heap=%u psram=%u\n",
                s_fx_size,s_fx_size,"INTERNAL",ESP.getFreeHeap(),ESP.getFreePsram());
  Serial.println("MODE_NAMES_BLOCKED reason=no_config_types_or_enabled_table_in_knob_repo render=numeric_ordinal");
}

void remoted_dashboard_tick(bool ble_connected){
  if(ble_connected!=s.ble){ s.ble=ble_connected; }   // link state → LED ring only (LAW 1)
  compose_face_if_needed();
  if(s.view==0){
    uint32_t now=millis();
    if(now - s.last_fx_ms >= K718_FX_FRAME_MS){
      s.last_fx_ms=now; uint32_t c0=micros();
      uint16_t tint = (s.channel==1)? rgb565(0x90,0x00,0x70) : group_color(FN[s.func].group);
      render_fx((uint16_t*)s_fx_buf,s_fx_size,(now-s.t0)*0.0016f,tint);
      lv_obj_invalidate(s_fx);
      uint32_t d=micros()-c0; g_compose_us+=d; if(d>g_compose_max_us) g_compose_max_us=d; g_compose_frames++;
    }
  }
}

void remoted_dashboard_on_encoder(int delta){
  if(delta==0) return;
  if(s.view==1){                                   // picker: rotary scrubs the highlight
    int p=(int)s.picker + delta; while(p<0)p+=FN_COUNT; p%=FN_COUNT;
    s.picker=(uint8_t)p; s.face_dirty=true; k718_feedback_event(K718_FB_PICKER_MOVE);
    return;
  }
  const Fn& f=FN[s.func]; uint8_t ch=chan_of(s.func);
  int v=s.val[s.func][ch];
  if(f.kind==K_TOG) v = v?0:1;
  else if(f.kind==K_ENUM||f.kind==K_PRESET||f.kind==K_LOCAL){ int n=f.emax+1; v=((v+delta)%n+n)%n; }
  else v=clampi(v+delta, 0, f.emax);
  s.val[s.func][ch]=(uint8_t)v;
  s.face_dirty=true;
  k718_feedback_event(K718_FB_DETENT);
  emit_active();
}

void remoted_dashboard_on_touch_down(int x,int y,uint32_t now_ms){ s.tx=x; s.ty=y; s.tt=now_ms; s.touching=true; }
void remoted_dashboard_on_touch_move(int x,int y,uint32_t now_ms){ (void)x;(void)y;(void)now_ms; }

void remoted_dashboard_on_touch_up(int x,int y,uint32_t now_ms){
  if(!s.touching) return; s.touching=false;
  int dx=x-s.tx, dy=y-s.ty; float dist=sqrtf((float)(dx*dx+dy*dy)); uint32_t held=now_ms-s.tt;
  int adx=dx<0?-dx:dx, ady=dy<0?-dy:dy;
  // long press (held, no travel) → BRIGHTNESS (LAW 5)
  if(held>=750 && dist<16){ remoted_dashboard_on_long_press(now_ms); return; }
  // swipe (42 px, dominant axis ≥1.35×)
  if(ady>=42 && ady>=(int)(1.35f*adx)){
    if(dy<0){ if(s.view==0){ s.view=1; s.picker=s.func; s.face_dirty=true; } }   // swipe up → picker
    else    { if(s.view==1){ s.view=0; s.face_dirty=true; } }                    // swipe down → close
    return;
  }
  if(adx>=42 && adx>=(int)(1.35f*ady)){                                          // swipe L/R → channel
    if(FN[s.func].per_channel){ s.channel ^= 1; s.face_dirty=true;
      k718_feedback_event(s.channel? K718_FB_CHANNEL_SECONDARY : K718_FB_CHANNEL_PRIMARY); }
    return;
  }
  // tap (<16 px, <450 ms)
  if(dist<16 && held<450){
    if(s.view==1){ s.func=s.picker; s.view=0; s.face_dirty=true; k718_feedback_event(K718_FB_PICKER_COMMIT); }
    else if(FN[s.func].kind==K_TOG){ uint8_t ch=chan_of(s.func); s.val[s.func][ch]=s.val[s.func][ch]?0:1;
      s.face_dirty=true; k718_feedback_event(K718_FB_DETENT); emit_active(); }
  }
}

void remoted_dashboard_on_long_press(uint32_t now_ms){
  (void)now_ms;
  s.func=FN_BRIGHTNESS; s.view=0; s.face_dirty=true;
  k718_feedback_event(K718_FB_PICKER_COMMIT);
}

// Temporary Phase 1 acceptance instrumentation (gesture proof without hands). Serial only.
extern "C" void remoted_dashboard_selftest_dump(const char* tag){
  Serial.printf("ST %s view=%s func=%d:%s picker=%d ch=%s val=%d\n",
    tag, s.view? "PICKER":"HOME", s.func, FN[s.func].name, s.picker,
    s.channel? "SEC":"PRI", s.val[s.func][chan_of(s.func)]);
}
