#include <cstdio>
#include <stdint.h>

#include "k1_ap_structured_evidence.h"

int main() {
  constexpr uint32_t required_ms = 300U;
  K1ApStructuredEvidenceState state = {};
  uint32_t now_ms = 1000U;

  // A 100 ms room transient must not wake the classifier.
  for (int i = 0; i < 10; ++i) {
    if (k1_ap_structured_evidence_tick(state, true, now_ms, required_ms)) return 1;
    now_ms += 10U;
  }
  for (int i = 0; i < 20; ++i) {
    if (k1_ap_structured_evidence_tick(state, false, now_ms, required_ms)) return 2;
    now_ms += 10U;
  }

  // A 70% candidate duty cycle represents sustained structured programme audio.
  bool woke = false;
  for (int i = 0; i < 200; ++i) {
    const bool candidate = (i % 10) < 7;
    woke = k1_ap_structured_evidence_tick(state, candidate, now_ms, required_ms) || woke;
    now_ms += 10U;
  }
  if (!woke || !state.active) return 3;

  // Silence drains the evidence and returns the classifier to inactive.
  for (int i = 0; i < 40; ++i) {
    k1_ap_structured_evidence_tick(state, false, now_ms, required_ms);
    now_ms += 10U;
  }
  if (state.active || state.score_ms != 0U) return 4;

  std::puts("AP_STRUCTURED_EVIDENCE PASS");
  return 0;
}
