#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <initializer_list>
#include <FixedPoints.h>
#include <FixedPointsCommon.h>

struct CRGB16 { SQ15x16 r, g, b; };
#include "k1_lever2_emit.h"
#include "k1_fe_gx_led_power.h"
#include "k1_fe_gx_power_policy.h"

constexpr uint16_t NATIVE_RESOLUTION = 160;
constexpr uint16_t SECONDARY_LED_COUNT = 160;
CRGB16 leds_16[160], leds_scaled_secondary[160];
struct { float PHOTONS = 0.25f; } CONFIG;
SQ15x16 MASTER_BRIGHTNESS = 0.5f;
float SECONDARY_PHOTONS = 1.0f, silent_scale = 0.5f, drop_cut_scale = 0.5f;
float k1_queue_transition_scale_primary = 0.5f;
float k1_queue_transition_scale_secondary = 0.25f;
bool noise_transition_queued = false, mode_transition_queued = false, debug_mode = false;
uint32_t millis() { return 100; }  // Do not advance boot fade in this composition test.
bool k1_authored_suppresses_live_update() { return false; }
void drop_cut_update() {}  // The musical-cut value is an explicit input here.
struct SerialDouble {
  template<class T> void print(T) {}
  template<class T> void println(T) {}
} USBSerial;
void clip_led_values(CRGB16* a) {
  for (unsigned i=0;i<160;++i) for (auto* c : {&a[i].r,&a[i].g,&a[i].b}) {
    if (*c < SQ15x16(0)) *c = SQ15x16(0);
    if (*c > SQ15x16(1)) *c = SQ15x16(1);
  }
}
#include "gx_output_integration.h"  // Extracted verbatim from production led_utilities.h.

static Pixel16 unpack(const CRGB* wire, uint16_t i) {
  // Independent decode of the two RGB carrier slots, not the production packer.
  return {uint16_t((uint16_t(wire[2*i].b)<<8)|wire[2*i+1].r),
          uint16_t((uint16_t(wire[2*i].r)<<8)|wire[2*i].g),
          uint16_t((uint16_t(wire[2*i+1].g)<<8)|wire[2*i+1].b)};
}

static void edge_composition() {
  for (unsigned i=0;i<160;++i) {
    leds_16[i] = {SQ15x16(1),SQ15x16(0.5),SQ15x16(0.25)};
    leds_scaled_secondary[i] = leds_16[i];
  }
  apply_brightness();
  apply_brightness_secondary();
  // Primary: master .5 * sqrt(.25) * silence .5 * cut .5 * dip .5.
  // Secondary: sqrt(1) * silence .5 * cut .5 * its own dip .25.
  assert(leds_16[0].r.getInternal()==2048);             // .03125
  assert(leds_scaled_secondary[0].r.getInternal()==4096); // .0625
  assert(leds_16[0].g.getInternal()==1024);
  assert(leds_scaled_secondary[0].g.getInternal()==2048);
  assert(leds_16[0].b.getInternal()==512);
  assert(leds_scaled_secondary[0].b.getInternal()==1024);
}

static void output_cases() {
  Pixel16 p[160],s[160],saved[160];
  CRGB wp[320],ws[320],expected[320],held[320];
  for (uint8_t slot : {0,1,2,3}) {
    // Distinct, composed primary/secondary brightness plus incandescent ratios.
    // Below the cap, splitting prepare/pack must be byte-identical to the
    // established production emitter, including the production look tables.
    const SQ15x16 r(1.0f),g(0.7f),b(0.3f);
    k1_fe_gx_prepare(leds_16,160,p,r,g,b,slot);
    k1_fe_gx_prepare(leds_scaled_secondary,160,s,r,g,b,slot);
    k1_fe_gx_pack(p,160,wp,65535);
    k1_lever2_pack_frame(leds_16,160,expected,160ull*3*65535,r,g,b,slot);
    assert(memcmp(wp,expected,sizeof(wp))==0);
    k1_fe_gx_pack(s,160,ws,65535);
    k1_lever2_pack_frame(leds_scaled_secondary,160,expected,160ull*3*65535,r,g,b,slot);
    assert(memcmp(ws,expected,sizeof(ws))==0);

    // Use an intentionally tight user request to exercise limiting after the
    // actual look. One common gain must preserve both edges and all channels.
    const uint16_t cap=k1_fe_gx_effective_led_ma(340,1900);
    const uint16_t gain=k1_fe_gx_led_scale(p,160,s,160,cap);
    assert(gain<65535 && gain>0);
    memcpy(saved,s,sizeof(s));
    k1_fe_gx_pack(p,160,wp,gain);
    k1_fe_gx_pack(s,160,ws,gain);
    uint64_t emitted_sum=0;
    for (unsigned i=0;i<160;++i) {
      const Pixel16 a=unpack(wp,i),b_out=unpack(ws,i);
      assert(a.r==(uint32_t(p[i].r)*gain>>16));
      assert(a.g==(uint32_t(p[i].g)*gain>>16));
      assert(a.b==(uint32_t(p[i].b)*gain>>16));
      assert(b_out.r==(uint32_t(s[i].r)*gain>>16));
      assert(b_out.g==(uint32_t(s[i].g)*gain>>16));
      assert(b_out.b==(uint32_t(s[i].b)*gain>>16));
      emitted_sum+=a.r+a.g+a.b+b_out.r+b_out.g+b_out.b;
    }
    assert(320ull*65535+20ull*emitted_sum<=uint64_t(cap)*65535);
    memcpy(held,ws,sizeof(ws));
    for (int repeat=0;repeat<20;++repeat) {
      k1_fe_gx_pack(s,160,ws,k1_fe_gx_led_scale(p,160,s,160,cap));
      assert(memcmp(held,ws,sizeof(ws))==0);
      assert(memcmp(saved,s,sizeof(s))==0);
    }
    // Reverse only complete 48-bit pixels; every decoded channel survives.
    for (unsigned i=0;i<160;++i) p[i]={uint16_t(i),uint16_t(i+256),uint16_t(i+1024)};
    k1_fe_gx_pack(p,160,wp,65535);
    ws2816_reverse_packed_pixels(wp,160);
    for (unsigned i=0;i<160;++i) {
      const Pixel16 a=unpack(wp,i),e=p[159-i];
      assert(a.r==e.r && a.g==e.g && a.b==e.b);
    }
  }
  for (auto& a:p) a={65535,32768,16384};
  for (auto& a:s) a={32768,16384,8192};
  const auto unlimited_request=k1_fe_gx_led_scale(p,160,s,160,
      k1_fe_gx_effective_led_ma(UINT32_MAX,1900));
  assert(unlimited_request==k1_fe_gx_led_scale(p,160,s,160,1900));
  assert(unlimited_request<65535);
  k1_fe_gx_pack(p,160,wp,k1_fe_gx_led_scale(p,160,s,160,0));
  for (unsigned i=0;i<160;++i) {
    const auto a=unpack(wp,i); assert(a.r==0 && a.g==0 && a.b==0);
  }
}

int main() {
  edge_composition(); output_cases();
  puts("PASS: production primary/secondary brightness composition, all four built-in looks, exact below-cap bytes, final shared RGB16 scaling, held peer, whole-pixel reverse and CONFIG bypass rejection");
}
