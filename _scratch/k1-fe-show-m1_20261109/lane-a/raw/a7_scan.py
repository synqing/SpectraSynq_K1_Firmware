"""Lane A7: list audio-input reads per effect source file (and shared helper headers).

Usage: python3 a7_scan.py <firmware_dir> <file> [<file> ...]
Prints, per file, each line that reads an audio input, tagged:
  SNAP   = field of the K1AudioSnapshot (replaced by authored intent while AUTHORED)
  BUS    = other Core-1 bus accessors (onset/tempo/semantic/frame/k1_vp_spectrogram)
  LIVE   = Core-0 live global that the authored path does NOT replace
Comment-only lines are skipped. Matching is lexical; every hit is then read by hand.
"""
import re
import sys

SNAP_FIELDS = r"(vu_level|peak_scaled|spectral_energy|novelty|low_energy|mid_energy|high_energy|silence|chroma_strength|spectrum|chroma_pc|chord|nyquist_safe_bin_hi)"
PATTERNS = [
    ("SNAP", re.compile(r"k1_vp_audio_snapshot_read\s*\(")),
    ("SNAP", re.compile(r"\b(snap|snapshot|audio|a|s|smart_audio|aud)\." + SNAP_FIELDS + r"\b")),
    ("BUS", re.compile(r"\bk1_vp_(onset_beat_read|tempo_read|audio_semantic_read|audio_frame|spectrogram)\b")),
    ("BUS", re.compile(r"\bk1_(tempo_read|onset_beat_read|audio_snapshot_read)\s*\(")),
    ("LIVE", re.compile(r"(?<![\w.>])(spectrogram|spectrogram_smooth|chromagram_smooth|chromagram_pregate|note_chromagram|note_spectrogram\w*|chromagram_max_val|chromagram_bass_max_val|waveform|waveform_fixed_point|waveform_history\w*|max_waveform_val_raw|max_waveform_val|max_waveform_val_follower|waveform_peak_scaled|silence|silent_scale|current_punch|audio_vu_level\w*|novelty_curve|novelty_linear_curve|spectral_history|spectrogram_history|sweet_spot_state\w*|hue_position|hue_shifting_mix)\b(?!\s*\()")),
]

def strip_comment(line):
    i = line.find("//")
    return line if i < 0 else line[:i]

root = sys.argv[1]
for rel in sys.argv[2:]:
    print(f"=== {rel}")
    in_block = False
    with open(f"{root}/{rel}", encoding="utf-8", errors="replace") as fh:
        for n, raw in enumerate(fh, 1):
            line = raw
            if in_block:
                if "*/" in line:
                    in_block = False
                    line = line.split("*/", 1)[1]
                else:
                    continue
            if "/*" in line and "*/" not in line:
                in_block = True
                line = line.split("/*", 1)[0]
            code = strip_comment(line)
            tags = sorted({t for t, p in PATTERNS if p.search(code)})
            if tags:
                print(f"{n}:{','.join(tags)}: {code.strip()[:170]}")
