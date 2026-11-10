// Host driver for audio/k1_afe2.cpp (tests/test_k1_afe2_native.py).
// Usage: k1_afe2_host <raw int16 little-endian file> <hop samples> <sample rate> <gamma> <floor>
// Prints one line per hop: how_much section anchor fast quiet
#include <cstdio>
#include <cstdlib>
#include <vector>

#include "k1_afe2.h"

int main(int argc, char** argv) {
  if (argc != 6) return 2;
  FILE* f = fopen(argv[1], "rb");
  if (f == nullptr) return 3;
  const unsigned hop = (unsigned)atoi(argv[2]);
  const float rate = (float)atof(argv[3]);
  const float gamma = (float)atof(argv[4]);
  const float floor_v = (float)atof(argv[5]);
  if (hop == 0 || hop > 4096) return 4;
  K1Afe2State st;
  k1_afe2_init(st, rate);
  std::vector<int16_t> buf(hop);
  while (fread(buf.data(), sizeof(int16_t), hop, f) == hop) {
    const float h = k1_afe2_process_hop(st, buf.data(), (uint16_t)hop, gamma, floor_v);
    printf("%.6f %.4f %.4f %d %d\n", (double)h, (double)st.section, (double)st.anchor, st.fast ? 1 : 0, st.quiet ? 1 : 0);
  }
  fclose(f);
  return 0;
}
