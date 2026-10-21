// Host cost of the bar-pointer frame update (lane R1 Phase 2.6). Arithmetic only: same state space as
// tempo_joint_estimator.py PointerFilter (periods 52..133 frames, time-indexed slots, Gaussian beat window
// with peak weight 1 and sum P/lam), window weights quantised to 1/16 so g^w is a 16-entry table (one powf
// per frame, no per-state exp). Rank evidence by a sorted window (memmove insert/remove).
// Build: cc -O2 -o tempo_joint_pointer_bench tempo_joint_pointer_bench.c -lm ; run: ./tempo_joint_pointer_bench FRAMES
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#define PMIN 52
#define PMAX 133
#define NP (PMAX - PMIN + 1)
#define W 1536
static float p[8000];
static int off[NP], P[NP];
static short wk_k[NP][64]; static unsigned char wk_q[NP][64]; static int wk_n[NP];
static float win[W], sorted_w[W]; static int nwin = 0, head = 0;
static float rank_of(float x) {
  int lo = 0, hi = nwin;
  while (lo < hi) { int m = (lo + hi) / 2; if (sorted_w[m] < x) lo = m + 1; else hi = m; }
  float r = nwin ? (float)lo / nwin : 0.5f;
  if (nwin == W) {                       // remove oldest
    float old = win[head]; int a = 0, b = nwin;
    while (a < b) { int m = (a + b) / 2; if (sorted_w[m] < old) a = m + 1; else b = m; }
    memmove(&sorted_w[a], &sorted_w[a + 1], (nwin - a - 1) * sizeof(float)); nwin--;
    if (lo > a) lo--;
  }
  memmove(&sorted_w[lo + 1], &sorted_w[lo], (nwin - lo) * sizeof(float)); sorted_w[lo] = x; nwin++;
  win[head] = x; head = (head + 1) % W;
  return r;
}
int main(int argc, char** argv) {
  long frames = argc > 1 ? atol(argv[1]) : 1000000;
  const float lam = 8.0f, kappa = 8.0f, q = 0.02f;
  int n = 0;
  for (int i = 0; i < NP; i++) {
    P[i] = PMIN + i; off[i] = n; n += P[i];
    float sig = P[i] / (lam * sqrtf(2.0f * (float)M_PI)); int h = (int)ceilf(3.0f * sig);
    wk_n[i] = 0;
    for (int k = -h; k <= h; k++) {
      float w = expf(-0.5f * (k / sig) * (k / sig)); int qw = (int)lrintf(w * 16.0f);
      if (qw > 0) { wk_k[i][wk_n[i]] = (short)k; wk_q[i][wk_n[i]] = (unsigned char)qw; wk_n[i]++; }
    }
  }
  for (int i = 0; i < NP; i++) for (int s = 0; s < P[i]; s++) p[off[i] + s] = 1.0f / (NP * P[i]);
  unsigned rng = 12345; long t = 0; double sink = 0; long win_ops = 0;
  struct timespec a, b; clock_gettime(CLOCK_MONOTONIC, &a);
  for (long f = 0; f < frames; f++, t++) {
    rng = rng * 1103515245u + 12345u; float x = (rng >> 8) * (1.0f / 16777216.0f);
    float acc[NP];
    for (int i = 0; i < NP; i++) { int s = off[i] + (int)((P[i] - 1 - t % P[i]) % P[i]); acc[i] = p[s]; p[s] *= 1.0f - q; }
    for (int i = 0; i < NP; i++) {
      int s0 = off[i] + (int)(((-(t + 1)) % P[i] + P[i]) % P[i]);
      float in = 0.0f;
      if (i + 1 < NP) in += 0.5f * q * acc[i + 1]; else in += 0.5f * q * acc[i];
      if (i > 0) in += 0.5f * q * acc[i - 1]; else in += 0.5f * q * acc[i];
      p[s0] += in;
    }
    float r = rank_of(x);
    float g = (kappa + 1.0f) * powf(r, kappa); if (g < 1e-3f) g = 1e-3f;
    float gq[17]; gq[0] = 1.0f; float g16 = powf(g, 1.0f / 16.0f); for (int k = 1; k <= 16; k++) gq[k] = gq[k - 1] * g16;
    for (int i = 0; i < NP; i++) {
      long tp = (t + 1) % P[i];
      for (int j = 0; j < wk_n[i]; j++) { int s = (int)((wk_k[i][j] - tp + 2 * P[i]) % P[i]); p[off[i] + s] *= gq[wk_q[i][j]]; }
      win_ops += wk_n[i];
    }
    float sum = 0.0f; for (int s = 0; s < n; s++) sum += p[s];
    float inv = 1.0f / sum; for (int s = 0; s < n; s++) p[s] *= inv;
    sink += p[(int)(t % n)];
  }
  clock_gettime(CLOCK_MONOTONIC, &b);
  double ns = ((b.tv_sec - a.tv_sec) * 1e9 + (b.tv_nsec - a.tv_nsec)) / frames;
  printf("{\"states\": %d, \"window_mults_per_frame\": %.1f, \"host_ns_per_frame\": %.1f, \"host_us_per_emit\": %.3f, "
         "\"floats_ram_bytes\": %d, \"sink\": %g}\n", n, (double)win_ops / frames, ns, 3.0 * ns / 1000.0,
         (int)((n + 2 * W) * sizeof(float)), sink);
  return 0;
}
