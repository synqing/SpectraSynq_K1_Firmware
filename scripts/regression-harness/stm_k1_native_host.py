#!/usr/bin/env python3
"""Host candidate STM via compiled k1_stm.cpp."""
from __future__ import annotations
import ctypes, hashlib, json, math, wave
from pathlib import Path
import numpy as np

SR, HOP, NFFT, NUM_FREQS, NOTE0 = 12800.0, 96, 512, 80, 55.0
ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / ".pio/stm_host_shim.dylib"
ALGO_ID = "k1-stm-native-40-v1"

class K1StmResult(ctypes.Structure):
    _fields_ = [("ready", ctypes.c_bool), ("temporal_energy", ctypes.c_float),
                ("spectral_energy", ctypes.c_float), ("spectral", ctypes.c_float * 40)]

def exe_hash():
    h = hashlib.sha256()
    for p in [ROOT/"SPECTRASYNQ_K1_FIRMWARE/audio/k1_stm.cpp", ROOT/"SPECTRASYNQ_K1_FIRMWARE/audio/k1_stm.h"]:
        h.update(p.read_bytes())
    return h.hexdigest()

def load_pcm(path: Path, max_s: float):
    with wave.open(str(path), "rb") as w:
        ch, fr, n = w.getnchannels(), w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32)
    if ch > 1: x = x.reshape(-1, ch).mean(axis=1)
    if fr != int(SR):
        t_old = np.arange(len(x))/fr; t_new = np.arange(0, t_old[-1], 1/SR)
        x = np.interp(t_new, t_old, x)
    return (x[:int(max_s*SR)]/32768.0).astype(np.float32)

def goertzel(seg, freq):
    n = len(seg); k = 0.5 + (n*freq)/SR; w = 2*math.pi*k/n; c = 2*math.cos(w)
    s1=s2=0.0
    for v in seg:
        s0=c*s1-s2+float(v); s2,s1=s1,s0
    p=s1*s1+s2*s2-c*s1*s2
    return math.sqrt(max(0.0,p))

def spec80(seg):
    return [min(1.0, goertzel(seg, NOTE0*(2**(i/12.0)))*4.0) for i in range(NUM_FREQS)]

def emit(pcm, out: Path):
    lib = ctypes.CDLL(str(LIB))
    lib.host_k1_stm_reset(); lib.host_k1_stm_process.argtypes=[ctypes.POINTER(ctypes.c_float), ctypes.c_uint8, ctypes.c_int, ctypes.POINTER(K1StmResult)]
    win = np.hanning(NFFT).astype(np.float32); pos=t_ms=0; dt=int(round(1000*HOP/SR)); frames=[]
    lib.host_k1_stm_reset()
    while pos+NFFT <= len(pcm):
        seg = pcm[pos:pos+NFFT]*win; rms=float(np.sqrt(np.mean(seg*seg)))
        arr=(ctypes.c_float*NUM_FREQS)(*spec80(seg)); res=K1StmResult()
        lib.host_k1_stm_process(arr, NUM_FREQS, int(rms<1e-4), ctypes.byref(res))
        e=float(res.temporal_energy+res.spectral_energy)
        frames.append({"t_ms":t_ms,"ready":bool(res.ready),"temporal_energy":float(res.temporal_energy),
            "spectral_energy":float(res.spectral_energy),"spectral":[float(res.spectral[i]) for i in range(40)],"energy":e})
        pos+=HOP; t_ms+=dt
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for fr in frames: f.write(json.dumps(fr)+"\n")
    return {"frames":len(frames),"mean_energy":float(np.mean([x["energy"] for x in frames])) if frames else 0.0}

if __name__ == "__main__":
    import argparse
    a=argparse.ArgumentParser(); a.add_argument("wav"); a.add_argument("-o","--out",required=True); a.add_argument("--max-seconds",type=float,default=20)
    args=a.parse_args(); pcm=load_pcm(Path(args.wav), args.max_seconds)
    stats=emit(pcm, Path(args.out))
    print(json.dumps({"algorithm_id":ALGO_ID,"executable_hash":exe_hash(),**stats}))
