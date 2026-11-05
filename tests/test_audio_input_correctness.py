"""Audio acquisition regressions: clock domain, zero input and SPSC publication."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"


def compile_run(tmp_path, source):
    path = tmp_path / "input.cpp"
    exe = tmp_path / "input"
    path.write_text(source)
    subprocess.run(["c++", "-std=c++17", "-O2", "-pthread", "-I", str(FW / "audio"), "-I", str(FW / "system"), str(path), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=20)


def test_loop_milliseconds_do_not_wrap_with_microseconds(tmp_path):
    ino = (FW / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text()
    expression = re.search(r"uint32_t t_now = ([^;]+);", ino).group(1)
    compile_run(tmp_path, r'''
    #include <stdint.h>
    #include <assert.h>
    uint64_t clock_us;
    uint32_t micros() { return (uint32_t)clock_us; }
    uint32_t millis() { return (uint32_t)(clock_us / 1000); }
    uint32_t stamp() { uint32_t t_now_us = micros(); return ''' + expression + r'''; }
    int main() {
      clock_us = 4294967000ULL; uint32_t before = stamp();
      clock_us += 7500; uint32_t after = stamp();
      assert(after - before == 7);
    }
    ''')


def test_line_silence_dwell_wake_reset_and_wrap(tmp_path):
    compile_run(tmp_path, r'''
    #define K1_PCM1808_CANON_TRIM_Q15 2048
    #define K1_PCM1808_LINE_SWITCH 1
    #define K1_FE_BOARD_V1 1
    #include "k1_audio_input_state.h"
    #include <assert.h>
    bool line_active = false;
    bool k1_fe_audio_line_active() { return line_active; }
    int main() {
      static_assert(K1_LINE_PRESENCE_FLOOR == 2, "Grounded B489 canonical floor");
      assert(k1_audio_presence_floor(108.0f) == 108.0f);
      line_active = true;
      assert(k1_audio_presence_floor(108.0f) == 2.0f);
      line_active = false;
      assert(k1_audio_presence_floor(57.0f) == 57.0f);
      K1LineSilenceState s = {}; int16_t pcm[96] = {};
      // The measured canonical idle includes nonzero samples on every hop.
      for (int i=0;i<96;++i) pcm[i]=(i%2) ? K1_LINE_PRESENCE_FLOOR : -int16_t(K1_LINE_PRESENCE_FLOOR);
      assert(!k1_line_silence_update(s, pcm, 96, 100, 5000));
      assert(!k1_line_silence_update(s, pcm, 96, 5099, 5000));
      assert(k1_line_silence_update(s, pcm, 96, 5100, 5000));
      pcm[95] = -int16_t(K1_LINE_PRESENCE_FLOOR + 1);
      assert(!k1_line_silence_update(s, pcm, 96, 5101, 5000));
      pcm[95] = 0;
      assert(!k1_line_silence_update(s, pcm, 96, 5102, 5000));
      s = {};
      assert(!k1_line_silence_update(s, pcm, 96, UINT32_MAX - 99, 5000));
      assert(k1_line_silence_update(s, pcm, 96, 4900, 5000));
      // Measured idle can have sparse peaks 3..7 despite interval RMS <2.
      // Independent expected criterion: 95*1 + 7*7 =144 <=96*2*2=384.
      s = {};
      for (int i=0;i<96;++i) pcm[i]=(i%2) ? 1 : -1;
      pcm[95]=7;
      assert(!k1_line_silence_update(s, pcm, 96, 100, 1000));
      assert(k1_line_silence_update(s, pcm, 96, 1100, 1000));
      // Sustained above-floor programme: 96*3*3=864 >384; same-hop wake.
      for (int i=0;i<96;++i) pcm[i]=(i%2) ? 3 : -3;
      assert(!k1_line_silence_update(s, pcm, 96, 1101, 1000));
      for (int i=0;i<96;++i) pcm[i]=0;
      assert(!k1_line_silence_update(s, pcm, 96, 1200, 1000));
      assert(k1_line_silence_update(s, pcm, 96, 2200, 1000));
      pcm[95]=-32768;
      assert(!k1_line_silence_update(s, pcm, 96, 2201, 1000));
    }
    ''')


def test_ring_concurrent_order_and_counter_wrap(tmp_path):
    ring = (FW / "audio/k1_pcm1808_ring.h").read_text()
    assert "__ATOMIC_RELEASE" in ring and "__ATOMIC_ACQUIRE" in ring
    compile_run(tmp_path, r'''
    #include "k1_pcm1808_ring.h"
    #include <thread>
    #include <assert.h>
    int main() {
      uint8_t store[64 * 6]; K1PcmRing q = {};
      q.buf = store; q.cap_frames = 64;
      q.w = q.r = UINT32_MAX - 31;
      std::thread writer([&] {
        for (uint32_t i = 0; i < 200000; ++i) {
          uint8_t v[6]; for (int j=0;j<6;++j) v[j]=(uint8_t)(i+j);
          while (!k1_pcm_ring_push(&q,v,1)) std::this_thread::yield();
        }
      });
      for (uint32_t i = 0; i < 200000; ++i) {
        uint8_t v[6]; while (!k1_pcm_ring_pop(&q,v,1)) std::this_thread::yield();
        for (int j=0;j<6;++j) assert(v[j] == (uint8_t)(i+j));
      }
      writer.join(); assert(k1_pcm_ring_used(&q)==0);
    }
    ''')


def test_publication_uses_acquisition_owned_times():
    ino = (FW / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text()
    source = (FW / "audio/i2s_audio.h").read_text()
    assert "producer_next.i2s_read_return_us = k1_audio_capture_timing.read_return_us;" in ino
    assert "producer_next.newest_sample_estimate_us = k1_audio_capture_timing.newest_us;" in ino
    assert "k1_audio_capture_timing.newest_us = (uint32_t)pcm_read.newest_sample_estimate_us;" in source
    assert "k1_audio_capture_timing.assumption = 2;" in source
    assert "k1_audio_capture_timing.assumption = 1;" in source
    assert "k1_line_silence_update(k1_fe_line_silence" in source


def test_event_metadata_survives_a_non_event_hop(tmp_path):
    ino = (FW / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text()
    start = ino.index("      if (k1_onset_beat_event.onset) {", ino.index("K1AudioFrame producer_next"))
    end = ino.index("#ifdef K1_SEMANTIC_STATE", start)
    block = ino[start:end]
    compile_run(tmp_path, r'''
    #include <stdint.h>
    #include <assert.h>
    struct Onset { bool onset; float onset_strength; } k1_onset_beat_event;
    struct K1TempoEvent { bool beat_tick; } tempo;
    K1TempoEvent k1_tempo_read() { return tempo; }
    struct Frame { uint32_t last_onset_time_us, onset_epoch, onset_sequence_total;
      float last_onset_strength; uint32_t last_beat_time_us, beat_epoch, beat_sequence_total; };
    Frame hop(uint32_t now_us) {
      static uint32_t s_onset_sequence=0,s_beat_sequence=0,s_onset_epoch=1,s_beat_epoch=1;
      static uint32_t s_last_onset_us=0,s_last_beat_us=0;
      static float s_last_onset_strength=0;
      Frame producer_next = {};
    ''' + block + r'''
      return producer_next;
    }
    int main() {
      k1_onset_beat_event={true,.75f}; tempo={true}; Frame a=hop(100);
      k1_onset_beat_event={false,0}; tempo={false}; Frame b=hop(200);
      assert(a.last_onset_time_us==100 && b.last_onset_time_us==100);
      assert(b.last_onset_strength==.75f && b.last_beat_time_us==100);
      assert(b.onset_sequence_total==1 && b.beat_sequence_total==1);
    }
    ''')


def test_shared_tempo_gather_exact_under_product_optimisation(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts/regression-harness"))
    import tempo_replay as trp
    (tmp_path / "Arduino.h").write_text(trp.ARDUINO_STUB)
    driver = tmp_path / "tempo.cpp"
    driver.write_text(r'''
    #include "k1_tempo.cpp"
    #include <assert.h>
    #include <string.h>
    int main() {
      k1_tempo_init(); uint32_t seed=123;
      // Silence, pulse trains, harmonically mixed periodic input, bounded noise,
      // negatives and over-range values exercise both sides of the 0..4 clamp.
      for (int kind=0;kind<6;++kind) for (int pos=0;pos<5;++pos) {
        k1_spectral_index=(pos*127)%512;
        k1_novelty_scale = pos == 0 ? 0.0f : (float)pos * 2.7f;
        for (int i=0;i<512;++i) {
          seed=seed*1664525u+1013904223u;
          float v=0;
          if(kind==1) v=(i%17==0)?1.0f:0.0f;
          if(kind==2) v=.5f+.3f*sinf(i*.17f)+.2f*sinf(i*.31f);
          if(kind==3) v=(float)(seed>>8)/16777216.0f;
          if(kind==4) v=-1.0f;
          if(kind==5) v=100.0f;
          k1_spectral_curve[i]=v;
        }
        k1_goertzel_fill_window();
        for (int b=0;b<K1_NUM_TEMPI;++b) {
          float ref=k1_compute_magnitude(b), phase=k1_tempi[b].phase;
          float got=k1_compute_magnitude_from_window(b);
          assert(memcmp(&ref,&got,sizeof(float))==0);
          assert(memcmp(&phase,&k1_tempi[b].phase,sizeof(float))==0);
        }
      }
    }
    ''')
    exe = tmp_path / "tempo"
    subprocess.run(["c++", "-std=c++17", "-O3", "-ffast-math", "-fno-finite-math-only",
                    "-DK1_TEMPO_HOST_TEST", "-DK1_TEMPO_CONF_V2", "-DK1_TEMPO_FLYWHEEL_V2",
                    "-DK1_TEMPO_ACF_SPREAD_V1=1", "-I", str(tmp_path), "-I", str(FW / "audio"),
                    "-I", str(FW / "system"), str(driver), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=20)
