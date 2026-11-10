#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <random>
#include <vector>
#include "k1_fe_gx_power_policy.h"
#include "k1_fe_gx_led_power.h"

struct Pixel { uint16_t r, g, b; };

static void policy_cases() {
  for (bool reverse : {false,true}) {
    const auto classify = [reverse](uint32_t mv) {
      return reverse ? k1_fe_gx_classify_cc(0,mv) : k1_fe_gx_classify_cc(mv,0);
    };
    for (uint32_t mv : {0u,199u,249u,611u,699u,1161u,1309u,2041u,3300u,UINT32_MAX})
      assert(classify(mv)==K1FeGxSource::Invalid);
    for (uint32_t mv : {250u,450u,610u}) assert(classify(mv)==K1FeGxSource::DefaultUsb);
    for (uint32_t mv : {700u,950u,1160u}) assert(classify(mv)==K1FeGxSource::Amp1_5);
    for (uint32_t mv : {1310u,1600u,2040u}) assert(classify(mv)==K1FeGxSource::Amp3);
  }
  assert(k1_fe_gx_classify_cc(1500,1500)==K1FeGxSource::Invalid);
  assert(k1_fe_gx_classify_cc(1500,201)==K1FeGxSource::Invalid);
  K1FeGxPowerPolicy p;
  p.update(0,true,1500,0,false);
  p.update(249,true,1500,0,false);
  assert(!p.permit && p.led_budget_ma==0);
  p.update(250,true,1500,0,false);
  assert(p.permit && p.led_budget_ma==1900);
  p.update(251,true,950,0,false);
  assert(p.permit && p.led_budget_ma==800 && p.dropping);
  p.update(260,true,950,0,true);
  p.update(269,true,950,0,true);
  assert(p.permit);
  p.update(270,true,950,0,true);
  assert(!p.permit && p.led_budget_ma==800);
  p.update(300,true,1500,0,false);
  p.update(549,true,1500,0,false);
  assert(!p.permit);
  p.update(550,true,1500,0,false);
  assert(p.permit);
  p.update(551,true,0,0,false);
  assert(p.led_budget_ma==0 && p.permit);
  p.update(590,true,0,0,false);
  assert(p.permit);
  p.update(591,true,0,0,false);
  assert(!p.permit);  // stalled-renderer timeout cannot retain high threshold
  p.update(600,true,1500,0,false);
  p.update(850,true,1500,0,false);
  assert(p.permit);
  p.update(851,false,1500,0,false);
  assert(!p.permit && p.led_budget_ma==0);
  // Noisy source cannot accumulate qualification across invalid samples.
  K1FeGxPowerPolicy noise;
  for (uint32_t t=0;t<2000;t+=10) {
    noise.update(t,true,(t/10)%2 ? 1500 : 1200,0,false);
    assert(!noise.permit && noise.led_budget_ma==0);
  }
  // millis rollover preserves the same dwell time.
  K1FeGxPowerPolicy wrap;
  wrap.update(UINT32_MAX-99,true,0,1500,false);
  wrap.update(149,true,0,1500,false);
  assert(!wrap.permit);
  wrap.update(150,true,0,1500,false);
  assert(wrap.permit);
  assert(k1_fe_gx_effective_led_ma(UINT32_MAX,1900)==1900);
  assert(k1_fe_gx_effective_led_ma(500,1900)==500);
  assert(k1_fe_gx_effective_led_ma(2500,0)==0);
}

static void limiter_cases() {
  Pixel p[160],s[160];
  for (auto& x:p) x={65535,65535,65535};
  for (auto& x:s) x={65535,65535,65535};
  assert(k1_fe_gx_led_scale(p,160,s,160,0)==0);
  assert(k1_fe_gx_led_scale(p,160,s,160,320)==0);
  const auto both = k1_fe_gx_led_scale(p,160,s,160,1900);
  const auto one = k1_fe_gx_led_scale(p,160,static_cast<Pixel*>(nullptr),0,1900);
  assert(both<one && both>0);
  // Repeated limiting never modifies the cached source (held-peer stability).
  for (int i=0;i<100;++i) {
    assert(k1_fe_gx_led_scale(p,160,s,160,1900)==both);
    assert(s[0].r==65535);
  }
  for (auto& x:p) x={17,9,3};
  for (auto& x:s) x={0,0,0};
  assert(k1_fe_gx_led_scale(p,160,s,160,800)==65535);
  for (uint32_t v=0;v<=65535;v++)
    assert(k1_fe_gx_apply_led_scale(uint16_t(v),65535)==v);
  // Exact identity uses a reserved 65535 sentinel. A one-code overload must
  // not round back to that sentinel and escape the model ceiling.
  for (const uint16_t cap : {uint16_t(800),uint16_t(1900)}) {
    for (auto& x:p) x={0,0,0};
    for (auto& x:s) x={0,0,0};
    uint64_t remaining=(uint64_t(cap-320)*65535)/20+1;
    for (auto& x:p) {
      x.r=uint16_t(remaining>65535 ? 65535 : remaining);
      remaining-=x.r;
    }
    assert(remaining==0);
    const auto scale=k1_fe_gx_led_scale(p,160,s,160,cap);
    assert(scale<65535);
    uint64_t emitted=0;
    for (const auto& x:p) emitted+=k1_fe_gx_apply_led_scale(x.r,scale);
    assert(320ull*65535+20ull*emitted<=uint64_t(cap)*65535);
  }
  // Independent current calculation over random post-limit frames. Synthetic
  // all-colour stresses test the limiter; they are not a product power target.
  std::mt19937 rng(0x4b314645u);
  for (int trial=0;trial<10000;++trial) {
    const uint16_t n=uint16_t(1+rng()%160),m=uint16_t(rng()%161);
    for (auto& x:p) x={uint16_t(rng()),uint16_t(rng()),uint16_t(rng())};
    for (auto& x:s) x={uint16_t(rng()),uint16_t(rng()),uint16_t(rng())};
    const uint16_t cap=uint16_t(rng()%3001);
    const auto gain=k1_fe_gx_led_scale(p,n,s,m,cap);
    uint64_t sum=0;
    for (uint16_t i=0;i<n;++i)
      sum+=k1_fe_gx_apply_led_scale(p[i].r,gain)+
           k1_fe_gx_apply_led_scale(p[i].g,gain)+k1_fe_gx_apply_led_scale(p[i].b,gain);
    for (uint16_t i=0;i<m;++i)
      sum+=k1_fe_gx_apply_led_scale(s[i].r,gain)+
           k1_fe_gx_apply_led_scale(s[i].g,gain)+k1_fe_gx_apply_led_scale(s[i].b,gain);
    if (cap<=uint32_t(n)+m) assert(sum==0);
    else assert((uint64_t(n)+m)*65535ull+20ull*sum<=uint64_t(cap)*65535ull);
  }
}

int main() {
  policy_cases(); limiter_cases();
  puts("PASS: CC bands/orientations, noisy/dual CC rejection, dwell, downgrade/frame timeout, PG loss, rollover, and 10000 two-edge current-model trials");
}
