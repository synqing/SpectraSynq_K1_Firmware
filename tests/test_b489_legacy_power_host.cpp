#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <initializer_list>
#include <FixedPoints.h>
#include <FixedPointsCommon.h>
struct CRGB16 { SQ15x16 r, g, b; };
#include "k1_b489_legacy_power.h"
#include "k1_lever2_emit.h"
#include "power_mgt.h"
#include "integration.h"

static Pixel16 primary[160], secondary[160];
static CRGB proxy[320];
static CLEDController controllers[4];

static uint8_t upper8(uint16_t value) {
  return uint8_t(value / 257U + (value % 257U != 0U));
}

static K1B489LegacyPowerLimit compare(uint16_t cap, uint16_t peer_count=160) {
  const Pixel16* edges[] = {primary, secondary};
  const uint16_t counts[] = {160, peer_count};
  uint32_t expected_total = 125;
  unsigned controller_count = 0;
  for (unsigned edge=0; edge<2; ++edge) {
    for (unsigned i=0; i<counts[edge]; ++i) {
      const auto p=edges[edge][i];
      proxy[edge*160+i] = CRGB(upper8(p.r),upper8(p.g),upper8(p.b));
    }
    for (unsigned i=0; i<counts[edge]; i+=80) {
      auto& controller=controllers[controller_count++];
      controller.data=proxy+edge*160+i;
      controller.count=uint16_t(counts[edge]-i < 80 ? counts[edge]-i : 80);
      controller.link=nullptr;
      expected_total += calculate_unscaled_power_mW(controller.data,controller.count);
    }
  }
  for (unsigned i=1; i<controller_count; ++i) controllers[i-1].link=&controllers[i];
  CLEDController::first=controllers;
  const auto result=k1_b489_legacy_power_limit(primary,160,secondary,peer_count,cap);
  assert(result.estimated_unscaled_mw==expected_total);
  assert(result.estimated_requested_mw==expected_total*255/256);
  const auto original=calculate_max_brightness_for_power_mW(uint8_t(255),uint32_t(cap)*5);
  assert(result.legacy_brightness==original);
  if (original==255) assert(result.scale_q16==65535);
  else assert(uint32_t(result.scale_q16)*255 <= uint32_t(original)*65536);
  for (unsigned ch=0; ch<=65535; ch+=257) {
    const auto out=k1_b489_legacy_power_apply(uint16_t(ch),result.scale_q16);
    assert(out<=ch);
    if (original==255) assert(out==ch);
    else assert(uint32_t(out)*255<=ch*original);
  }
  return result;
}

int main() {
  // Frozen arithmetic goldens derived independently from the pinned estimator:
  // 4 physical controllers,80 pixels each,target255,budget1913*5.
  struct Golden {uint8_t r,g,b; uint32_t total,requested; uint8_t brightness; uint16_t q16;};
  const Golden goldens[] = {
    {0,0,0,1725,1718,255,65535},
    {255,255,255,68657,68388,35,8995},
    {255,0,0,27225,27118,89,22873},
    {0,255,0,19253,19177,127,32639},
    {0,0,255,25629,25528,95,24415},
    {128,63,7,19509,19432,125,32125},
  };
  for (const auto& golden:goldens) {
    for (unsigned i=0;i<160;++i)
      primary[i]=secondary[i]={uint16_t(golden.r*257),uint16_t(golden.g*257),uint16_t(golden.b*257)};
    const auto result=compare(1913);
    assert(result.estimated_unscaled_mw==golden.total);
    assert(result.estimated_requested_mw==golden.requested);
    assert(result.legacy_brightness==golden.brightness);
    assert(result.scale_q16==golden.q16);
  }
  // Native low bits, unequal edges and DIN-boundary floors. No random source.
  for (unsigned i=0;i<160;++i) {
    primary[i]={uint16_t(i*409U),uint16_t(i*137U),uint16_t(i*3U+1)};
    secondary[i]={uint16_t(65535U-i*101U),uint16_t(i*251U),uint16_t(i*47U)};
  }
  for (uint16_t cap:{uint16_t(0),uint16_t(1),uint16_t(343),uint16_t(1913),uint16_t(65535)}) compare(cap);
  const auto held=compare(1913);
  const auto absent=compare(1913,0);
  assert(held.scale_q16<absent.scale_q16); // disabled-but-held must remain counted
  const Pixel16 saved=secondary[31];
  for (unsigned repeat=0;repeat<5;++repeat) {
    const auto repeated=compare(1913);
    assert(repeated.scale_q16==held.scale_q16);
    assert(memcmp(&saved,&secondary[31],sizeof(saved))==0);
  }
  for (auto& pixel:secondary) pixel={};
  compare(1913); // a black peer still costs its physical idle estimate
  assert(k1_b489_legacy_power_edge(nullptr,160)==800);
  for (unsigned value=0;value<=65535;++value) {
    assert(k1_b489_legacy_power_proxy(uint16_t(value))==upper8(uint16_t(value)));
    assert(k1_b489_legacy_power_apply(uint16_t(value),65535)==value);
  }

  // Execute the actual led_utilities prepare/pack bodies with real FixedPoints,
  // look and packer headers; only transport/storage has a host double.
  CRGB16 scaled[160];
  Pixel16 native[160];
  CRGB old_wire[320],new_wire[320];
  for (unsigned i=0;i<160;++i)
    scaled[i]={SQ15x16(double(i)/159.0),SQ15x16(double(159-i)/159.0),SQ15x16(double(i%13)/13.0)};
  for (uint8_t slot=0;slot<16;++slot) {
    k1_b489_prepare_native(scaled,160,native,SQ15x16(1),SQ15x16(0.4453),SQ15x16(0.1562),slot);
    k1_b489_pack_limited(native,160,new_wire,65535);
    k1_lever2_pack_frame(scaled,160,old_wire,160ULL*3*65535,
                        SQ15x16(1),SQ15x16(0.4453),SQ15x16(0.1562),slot);
    assert(memcmp(old_wire,new_wire,sizeof(old_wire))==0);
    const auto limit=k1_b489_legacy_power_limit(native,160,native,160,1913);
    k1_b489_pack_limited(native,160,new_wire,limit.scale_q16);
    for (unsigned i=0;i<160;++i) {
      const auto* bytes=reinterpret_cast<const uint8_t*>(new_wire)+i*6;
      const uint16_t actual[]={uint16_t(bytes[2]*256U+bytes[3]),
                               uint16_t(bytes[0]*256U+bytes[1]),
                               uint16_t(bytes[4]*256U+bytes[5])};
      const uint16_t input[]={native[i].r,native[i].g,native[i].b};
      for (unsigned c=0;c<3;++c) {
        const uint16_t expected=limit.scale_q16==65535 ? input[c] :
            uint16_t(uint64_t(input[c])*limit.scale_q16/65536);
        assert(actual[c]==expected);
      }
    }
  }
  puts("Pinned FastLED oracle, six goldens, held/black peer and 16 look/pack integrations compared.");
}
