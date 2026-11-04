#!/usr/bin/env python3
"""B489 line-in test: Mac headphone/AUX out -> PCM1808 -> K1.
usage: linein_test.py PORT MUSIC_WAV OUT_LOG
Timeline (s, from port open; opening resets the chip, boot takes ~6 s):
  12 :audio_src=line   14 :fe_status (silence)
  16 tone 1 kHz 6 s    19 :fe_status (tone)
  24 :fe_status (silence after tone)
  26 music 12 s        29, 32, 35 :fe_status (music)
  40 :fe_status (silence)   42 :audio_src=auto   44 :fe_status (mic)
Each line the board prints is kept; markers '#T=<s> <event>' are inserted."""
import math, struct, subprocess, sys, time, wave
import serial

port, music, out = sys.argv[1], sys.argv[2], sys.argv[3]
tone = out.rsplit("/", 1)[0] + "/tone_1khz_6s.wav"
with wave.open(tone, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
    frames = bytearray()
    for n in range(48000 * 6):
        v = int(0.5 * 32767 * math.sin(2 * math.pi * 1000 * n / 48000))
        frames += struct.pack("<hh", v, v)
    w.writeframes(bytes(frames))

plan = [(12, "cmd", ":audio_src=line"), (14, "cmd", ":fe_status"),
        (16, "play", tone), (19, "cmd", ":fe_status"), (24, "cmd", ":fe_status"),
        (26, "play", music), (29, "cmd", ":fe_status"), (32, "cmd", ":fe_status"),
        (35, "cmd", ":fe_status"), (40, "cmd", ":fe_status"),
        (42, "cmd", ":audio_src=auto"), (44, "cmd", ":fe_status")]
s = serial.Serial(); s.port = port; s.baudrate = 115200; s.timeout = 0.05
s.dtr = False; s.rts = False; s.open()
buf = bytearray(); t0 = time.time(); players = []
while time.time() - t0 < 47:
    t = time.time() - t0
    if plan and t >= plan[0][0]:
        at, kind, arg = plan.pop(0)
        buf += f"\n#T={at} {kind} {arg}\n".encode()
        if kind == "cmd":
            s.write((arg + "\n").encode())
        else:
            # afplay -t caps the music clip at 12 s; the tone file is 6 s long.
            players.append(subprocess.Popen(["afplay", "-t", "12", arg]))
    buf += s.read(4096)
s.close()
for p in players:
    p.wait()
open(out, "wb").write(bytes(buf))
print(f"captured {len(buf)} bytes -> {out}")
