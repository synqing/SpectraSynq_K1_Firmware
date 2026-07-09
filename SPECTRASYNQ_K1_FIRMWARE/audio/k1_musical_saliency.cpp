#include "k1_musical_saliency.h"

#include <Arduino.h>
#include <math.h>

static const SaliencyTuning kSaliencyTuning{};
static const float K1_MS_TO_SEC = 0.001f;

struct K1MusicalSaliencyState {
  float prevFrameMs = 0.0f;
  float prevChromaStrength = 0.0f;
  float prevNovelty = 0.0f;
  float prevFastFluxNovelty = 0.0f;
  float prevEnergy = 0.0f;
  float adaptiveFloor = 0.0f;
  uint32_t lastEventMs = 0;
#ifdef K1_CHORD_V2
  // Chord-change memory for the revived harmonic axis. Seeded to sentinels so a
  // detected chord on the first warmed frame counts as a change (axis fires).
  uint8_t prevChordRoot = 0xFF;  // last seen root pitch class (0xFF = none yet)
  uint8_t prevChordType = 0xFF;  // last seen K1ChordType (0xFF = none yet)
#endif
};

static K1MusicalSaliencyState g_saliency_state{};

static K1SaliencyAxisFrame g_saliency_axis{};
static K1SaliencyEvent g_saliency_event{};
static bool g_saliency_event_valid = false;

static bool g_saliency_warmed = false;

static portMUX_TYPE g_saliency_mutex = portMUX_INITIALIZER_UNLOCKED;

static float k1_saliency_clamp01(float v) {
  if (!isfinite(v)) return 0.0f;
  if (v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

static float k1_saliency_asymmetric_smooth(float current, float target, float rise_time, float fall_time, float dt_seconds) {
  float t = dt_seconds > 0.0f ? dt_seconds : K1_MS_TO_SEC;
  if (rise_time < K1_MS_TO_SEC) rise_time = K1_MS_TO_SEC;
  if (fall_time < K1_MS_TO_SEC) fall_time = K1_MS_TO_SEC;

  const float rise_alpha = 1.0f - expf(-t / rise_time);
  const float fall_alpha = 1.0f - expf(-t / fall_time);
  const float alpha = (target >= current) ? rise_alpha : fall_alpha;
  return current + (target - current) * alpha;
}

static void k1_publish_axis(const K1SaliencyAxisFrame& src) {
  portENTER_CRITICAL(&g_saliency_mutex);
  g_saliency_axis = src;
  portEXIT_CRITICAL(&g_saliency_mutex);
}

static void k1_publish_event(const K1SaliencyEvent& event, bool valid) {
  portENTER_CRITICAL(&g_saliency_mutex);
  g_saliency_event = event;
  g_saliency_event_valid = valid;
  portEXIT_CRITICAL(&g_saliency_mutex);
}

void k1_musical_saliency_update(const K1AudioSnapshot& audio, const K1OnsetBeatEvent* onset) {
  if (!isfinite(audio.frame_ms) || !isfinite(audio.novelty) || !isfinite(audio.spectral_energy) || !isfinite(audio.chroma_strength)) {
    k1_publish_axis(g_saliency_axis);
    return;
  }

  float now_ms = (float)audio.frame_ms;
  if (!g_saliency_warmed) {
#ifdef K1_CHORD_V2
    // Field-by-field so prevChordRoot/prevChordType keep their 0xFF sentinels
    // (the default member initialisers) — the first detected chord after warm-up
    // then registers as a harmonic change. (An aggregate {...} would zero them.)
    g_saliency_state = K1MusicalSaliencyState{};
    g_saliency_state.prevFrameMs = now_ms;
    g_saliency_state.prevChromaStrength = audio.chroma_strength;
    g_saliency_state.prevNovelty = audio.novelty;
    g_saliency_state.prevFastFluxNovelty = audio.novelty;
    g_saliency_state.prevEnergy = audio.spectral_energy;
    g_saliency_state.adaptiveFloor = 0.0f;
    g_saliency_state.lastEventMs = 0;
#else
    g_saliency_state = {
      now_ms, audio.chroma_strength, audio.novelty, audio.novelty, audio.spectral_energy,
      0.0f, 0
    };
#endif
    g_saliency_warmed = true;
    g_saliency_axis = {};
    k1_publish_axis(g_saliency_axis);
    return;
  }

  // Silence gate (v3 PipelineAdapter/ControlBus.cpp:749-775 parity): no musical saliency in
  // silence. Hold/zero the axes, do not emit an event, and do not ratchet the floor -- the
  // engine previously never read audio.silence, so noise jitter mis-fired in quiet (RC-1).
  if (audio.silence) {
    K1SaliencyAxisFrame quiet{};
    quiet.dominantType = static_cast<uint8_t>(K1SaliencyType::DYNAMIC);
    g_saliency_state.prevChromaStrength = audio.chroma_strength;
    g_saliency_state.prevNovelty = audio.novelty;
    g_saliency_state.prevFastFluxNovelty = audio.novelty;
    g_saliency_state.prevEnergy = audio.spectral_energy;
    g_saliency_state.prevFrameMs = now_ms;
#ifdef K1_CHORD_V2
    // Forget the held chord during silence so the first chord on re-entry is a
    // harmonic event, not a no-change continuation of whatever played before.
    g_saliency_state.prevChordRoot = 0xFF;
    g_saliency_state.prevChordType = 0xFF;
#endif
    k1_publish_axis(quiet);
    return;
  }

  float dt_ms = now_ms - g_saliency_state.prevFrameMs;
  if (dt_ms <= 1.0f || !isfinite(dt_ms)) dt_ms = 1.0f;
  float dt_seconds = dt_ms * K1_MS_TO_SEC;

#ifdef K1_CHORD_V2
  // Harmonic axis (REVIVED): real chord root/type-change saliency, ported from
  // donor ControlBus::computeSaliency (ControlBus.cpp:871-895). Base component is
  // proportional to chord confidence so a sustained chord still registers as
  // weakly harmonic; a chord-ROOT change spikes to 1.0; a chord-TYPE change (e.g.
  // major<->minor) lifts to at least 0.6. This is genuine harmonic structure,
  // not the chroma_strength peakiness delta the incumbent (below) keyed on.
  float harmonic_raw = audio.chord.confidence * 0.3f;
  if (audio.chord.confidence > 0.3f) {
    const uint8_t curType = static_cast<uint8_t>(audio.chord.type);
    if (audio.chord.rootNote != g_saliency_state.prevChordRoot) {
      harmonic_raw = 1.0f;
      g_saliency_state.prevChordRoot = audio.chord.rootNote;
    } else if (curType != g_saliency_state.prevChordType &&
               audio.chord.type != K1ChordType::NONE) {
      harmonic_raw = fmaxf(harmonic_raw, 0.6f);
    }
    g_saliency_state.prevChordType = curType;
  }
  harmonic_raw = k1_saliency_clamp01(harmonic_raw);
#else
  // Harmonic proxy: chroma strength change magnitude (fork has chroma_strength, not chord root/confidence fields).
  const float harmonic_raw = k1_saliency_clamp01(
    fabsf(audio.chroma_strength - g_saliency_state.prevChromaStrength) > kSaliencyTuning.harmonicChangeThreshold
      ? fabsf(audio.chroma_strength - g_saliency_state.prevChromaStrength)
      : 0.0f
  );
#endif

  // Timbral proxy: novelty derivative surrogate.
  const float flux_delta = fabsf(audio.novelty - g_saliency_state.prevNovelty);
  const float timbral_raw = k1_saliency_clamp01(flux_delta / kSaliencyTuning.fluxDerivativeThreshold);

  // Dynamic proxy: spectral energy derivative surrogate.
  const float energy_delta = fabsf(audio.spectral_energy - g_saliency_state.prevEnergy);
  const float dynamic_raw = k1_saliency_clamp01(energy_delta / kSaliencyTuning.rmsDerivativeThreshold);

  // Rhythmic proxy: accepted beat event preferred, else fast-flux fallback from novelty.
  float rhythmic_raw = 0.0f;
  bool has_onset_beat = onset != nullptr && onset->beat;
  if (has_onset_beat && isfinite(onset->beat_confidence)) {
    float conf = onset->beat_confidence;
    rhythmic_raw = k1_saliency_clamp01(0.8f * conf + 0.5f);
  } else {
    const float fast_flux = fabsf(audio.novelty - g_saliency_state.prevFastFluxNovelty);
    rhythmic_raw = k1_saliency_clamp01(0.5f * fast_flux);
  }

  K1SaliencyAxisFrame frame{};
  frame.harmonicNovelty = harmonic_raw;
  frame.rhythmicNovelty = rhythmic_raw;
  frame.timbralNovelty = timbral_raw;
  frame.dynamicNovelty = dynamic_raw;

  frame.harmonicNoveltySmooth = k1_saliency_asymmetric_smooth(
    g_saliency_axis.harmonicNoveltySmooth,
    harmonic_raw,
    kSaliencyTuning.harmonicRiseTime,
    kSaliencyTuning.harmonicFallTime,
    dt_seconds
  );
  frame.rhythmicNoveltySmooth = k1_saliency_asymmetric_smooth(
    g_saliency_axis.rhythmicNoveltySmooth,
    rhythmic_raw,
    kSaliencyTuning.rhythmicRiseTime,
    kSaliencyTuning.rhythmicFallTime,
    dt_seconds
  );
  frame.timbralNoveltySmooth = k1_saliency_asymmetric_smooth(
    g_saliency_axis.timbralNoveltySmooth,
    timbral_raw,
    kSaliencyTuning.timbralRiseTime,
    kSaliencyTuning.timbralFallTime,
    dt_seconds
  );
  frame.dynamicNoveltySmooth = k1_saliency_asymmetric_smooth(
    g_saliency_axis.dynamicNoveltySmooth,
    dynamic_raw,
    kSaliencyTuning.dynamicRiseTime,
    kSaliencyTuning.dynamicFallTime,
    dt_seconds
  );

  frame.overallSaliency = k1_saliency_clamp01(
    frame.harmonicNoveltySmooth * kSaliencyTuning.harmonicWeight +
    frame.rhythmicNoveltySmooth * kSaliencyTuning.rhythmicWeight +
    frame.timbralNoveltySmooth * kSaliencyTuning.timbralWeight +
    frame.dynamicNoveltySmooth * kSaliencyTuning.dynamicWeight
  );

  frame.dominantType = static_cast<uint8_t>(K1SaliencyType::DYNAMIC);
  if (frame.harmonicNoveltySmooth >= frame.rhythmicNoveltySmooth &&
      frame.harmonicNoveltySmooth >= frame.timbralNoveltySmooth &&
      frame.harmonicNoveltySmooth >= frame.dynamicNoveltySmooth) {
    frame.dominantType = static_cast<uint8_t>(K1SaliencyType::HARMONIC);
  } else if (frame.rhythmicNoveltySmooth >= frame.harmonicNoveltySmooth &&
             frame.rhythmicNoveltySmooth >= frame.timbralNoveltySmooth &&
             frame.rhythmicNoveltySmooth >= frame.dynamicNoveltySmooth) {
    frame.dominantType = static_cast<uint8_t>(K1SaliencyType::RHYTHMIC);
  } else if (frame.timbralNoveltySmooth >= frame.harmonicNoveltySmooth &&
             frame.timbralNoveltySmooth >= frame.rhythmicNoveltySmooth &&
             frame.timbralNoveltySmooth >= frame.dynamicNoveltySmooth) {
    frame.dominantType = static_cast<uint8_t>(K1SaliencyType::TIMBRAL);
  }

  // Fixed-floor relative gate (v3 ControlBus.cpp:271-273 parity): slow baseline + fixed margin.
  // REPLACES the prior self-ratcheting 2x-EMA-of-overallSaliency threshold -- a fork-author
  // invention (absent from v3) that ratcheted shut on music and mis-fired in silence (RC-1).
  const float adaptive_threshold = k1_saliency_clamp01(g_saliency_state.adaptiveFloor + 0.15f);
  K1SaliencyEvent event{};
  event.frameMs = audio.frame_ms;
  event.salient = (frame.overallSaliency > adaptive_threshold) &&
                  (uint32_t(now_ms - g_saliency_state.lastEventMs) > 120u);
  event.overallSaliency = frame.overallSaliency;
  event.adaptiveThreshold = adaptive_threshold;
  event.ageMs = (uint16_t)fabsf(now_ms - g_saliency_state.lastEventMs);
  event.flags = 0;
  if (event.salient) g_saliency_state.lastEventMs = (uint32_t)now_ms;

  g_saliency_state.prevChromaStrength = audio.chroma_strength;
  g_saliency_state.prevNovelty = audio.novelty;
  g_saliency_state.prevFastFluxNovelty = audio.novelty;
  g_saliency_state.prevEnergy = audio.spectral_energy;
  g_saliency_state.prevFrameMs = now_ms;
  g_saliency_state.adaptiveFloor = 0.995f * g_saliency_state.adaptiveFloor + 0.005f * frame.overallSaliency;

  k1_publish_axis(frame);
  if (event.salient) k1_publish_event(event, true);
}

K1SaliencyAxisFrame k1_musical_saliency_read() {
  portENTER_CRITICAL(&g_saliency_mutex);
  K1SaliencyAxisFrame out = g_saliency_axis;
  portEXIT_CRITICAL(&g_saliency_mutex);
  return out;
}

bool k1_musical_saliency_read_event(K1SaliencyEvent* out, bool clear_after_read) {
  if (out == nullptr) return false;
  portENTER_CRITICAL(&g_saliency_mutex);
  const bool valid = g_saliency_event_valid;
  if (valid) {
    *out = g_saliency_event;
    if (clear_after_read) g_saliency_event_valid = false;
  }
  portEXIT_CRITICAL(&g_saliency_mutex);
  return valid;
}
