#!/usr/bin/env python3
"""Off-flag byte-identity check for lane R1 (invariant I10, acceptance A6).

k1_build_provenance.py stamps git hash + wall-clock epoch into every translation unit, so raw .bin
files never match. This tool compares what the code IS:
  * every object file: content of each non-debug section (by name), relocations resolved to symbol
    names, and the defined-symbol set; debug sections, .comment and file symbols are ignored;
  * the linked firmware.elf: content of every allocated section.
`build` pins provenance (git short hash + epoch) through a harness-only shim (PYTHONPATH
sitecustomize + a git wrapper) so two builds of different commits can be compared at ELF level.

  tempo_lane_bytecheck.py build    --env ENV --out SNAPDIR [--repro-git abc1234 --repro-epoch 1700000000]
  tempo_lane_bytecheck.py snapshot --env ENV --out SNAPDIR          # copy the current build only
  tempo_lane_bytecheck.py compare  SNAP_A SNAP_B [--objects-only] [--json OUT]
Exit: 0 identical, 1 differs, 2 bad input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IGNORED_PREFIXES = (".debug", ".comment", ".xt.prop", ".xt.lit", ".note")
SHT_SYMTAB, SHT_STRTAB, SHT_RELA, SHT_REL, SHT_NOBITS, SHT_GROUP = 2, 3, 4, 9, 8, 17
SHF_ALLOC = 0x2


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Elf32:
    def __init__(self, data: bytes):
        if data[:4] != b"\x7fELF" or data[4] != 1 or data[5] != 1:
            raise ValueError("not an ELF32 little-endian file")
        self.d = data
        (self.e_type, _, _, _, _, self.shoff, _, _, _, _, self.shentsize, self.shnum,
         self.shstrndx) = struct.unpack_from("<HHIIIIIHHHHHH", data, 16)
        self.sh = [struct.unpack_from("<IIIIIIIIII", data, self.shoff + i * self.shentsize) for i in range(self.shnum)]
        strtab = self.sh[self.shstrndx]
        self.names = [self._str(strtab[4], s[0]) for s in self.sh]

    def _str(self, off: int, idx: int) -> str:
        end = self.d.index(b"\0", off + idx)
        return self.d[off + idx:end].decode(errors="replace")

    def content(self, i: int) -> bytes:
        s = self.sh[i]
        return b"" if s[1] == SHT_NOBITS else self.d[s[4]:s[4] + s[5]]

    def symbols(self):
        for i, s in enumerate(self.sh):
            if s[1] != SHT_SYMTAB:
                continue
            strsec = self.sh[s[6]]
            out = []
            for k in range(s[5] // 16):
                name, value, size, info, other, shndx = struct.unpack_from("<IIIBBH", self.d, s[4] + 16 * k)
                out.append((self._str(strsec[4], name), value, size, info, shndx))
            return out
        return []

    def ignored(self, i: int) -> bool:
        n = self.names[i]
        return any(n.startswith(p) for p in IGNORED_PREFIXES) or "debug" in n


def canon_object(path: Path) -> dict:
    e = Elf32(path.read_bytes())
    syms = e.symbols()

    def symname(idx: int) -> str:
        name, value, size, info, shndx = syms[idx]
        if (info & 0xF) == 3 and shndx < e.shnum:  # STT_SECTION
            return "§" + e.names[shndx]
        return name
    sections, relocs = {}, {}
    for i, s in enumerate(e.sh):
        name, typ = e.names[i], s[1]
        if i == 0 or e.ignored(i) or typ in (SHT_SYMTAB, SHT_STRTAB, SHT_GROUP):
            continue
        if typ in (SHT_RELA, SHT_REL):
            target = e.names[s[7]]
            if any(target.startswith(p) for p in IGNORED_PREFIXES) or "debug" in target:
                continue
            ent = 12 if typ == SHT_RELA else 8
            rows = []
            for k in range(s[5] // ent):
                if typ == SHT_RELA:
                    off, info, add = struct.unpack_from("<IIi", e.d, s[4] + ent * k)
                else:
                    (off, info), add = struct.unpack_from("<II", e.d, s[4] + ent * k), 0
                rows.append((off, info & 0xFF, symname(info >> 8), add))
            relocs.setdefault(target, []).extend(rows)
            continue
        sections.setdefault(name, []).append((typ, s[5], _sha(e.content(i))))
    defined = sorted((n, size, info & 0xF, info >> 4, e.names[shndx] if 0 < shndx < e.shnum else str(shndx))
                     for n, value, size, info, shndx in syms
                     if n and (info & 0xF) not in (3, 4) and shndx != 0)
    return {"sections": {k: sorted(v) for k, v in sections.items()},
            "relocs": {k: _sha(json.dumps(sorted(v)).encode()) for k, v in relocs.items()},
            "symbols": _sha(json.dumps(defined).encode())}


def canon_elf(path: Path) -> dict:
    e = Elf32(path.read_bytes())
    return {e.names[i]: [s[1], s[3], s[5], _sha(e.content(i))] for i, s in enumerate(e.sh)
            if i and (s[2] & SHF_ALLOC) and not e.ignored(i)}


SITECUSTOMIZE = '''
import os, sys, time, importlib.util
_e = os.environ.get("K1_REPRO_EPOCH")
if _e:
    def _fixed():
        return float(_e)
    time.time = _fixed
# Chain-load the interpreter's own sitecustomize (Homebrew's PlatformIO relies on it).
_here = os.path.dirname(os.path.abspath(__file__))
for _d in sys.path:
    if not _d or os.path.abspath(_d) == _here:
        continue
    _f = os.path.join(_d, "sitecustomize.py")
    if os.path.isfile(_f):
        _spec = importlib.util.spec_from_file_location("_k1_orig_sitecustomize", _f)
        _spec.loader.exec_module(importlib.util.module_from_spec(_spec))
        break
'''
GIT_WRAPPER = '''#!/bin/sh
if [ "$1" = "rev-parse" ] && [ "$2" = "--short" ] && [ "$3" = "HEAD" ] && [ -n "$K1_REPRO_GIT" ]; then
  echo "$K1_REPRO_GIT"; exit 0
fi
exec "{real}" "$@"
'''


def cmd_build(a) -> int:
    env = dict(os.environ)
    shim = Path(tempfile.mkdtemp(prefix="k1repro"))
    if a.repro_git or a.repro_epoch:
        (shim / "sitecustomize.py").write_text(SITECUSTOMIZE)
        real_git = shutil.which("git")
        g = shim / "bin" / "git"
        g.parent.mkdir()
        g.write_text(GIT_WRAPPER.format(real=real_git))
        g.chmod(g.stat().st_mode | stat.S_IEXEC)
        env["PYTHONPATH"] = str(shim) + os.pathsep + env.get("PYTHONPATH", "")
        env["PATH"] = str(shim / "bin") + os.pathsep + env["PATH"]
        env["K1_REPRO_GIT"] = a.repro_git or ""
        env["K1_REPRO_EPOCH"] = str(a.repro_epoch or "")
        if a.repro_epoch:
            env["SOURCE_DATE_EPOCH"] = str(a.repro_epoch)  # GCC pins __DATE__/__TIME__ (framework TUs)
    log = Path(a.out).with_suffix(".build.log")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w") as fh:
        r = subprocess.run(["bash", "scripts/agent/pio-build.sh", a.env], cwd=ROOT, env=env, stdout=fh,
                           stderr=subprocess.STDOUT)
    stamp = [ln for ln in log.read_text(errors="replace").splitlines() if "[k1-build-provenance]" in ln]
    print(f"build {a.env} exit={r.returncode} {stamp[-1] if stamp else 'no provenance line'}")
    if r.returncode != 0:
        return 2
    return cmd_snapshot(a)


def cmd_snapshot(a) -> int:
    src = ROOT / ".pio/build" / a.env
    out = Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    files = {}
    for p in sorted(src.rglob("*.o")) + [src / "firmware.elf", src / "firmware.bin"]:
        if p.is_file():
            rel = p.relative_to(src)
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out / rel)
            files[str(rel)] = _sha(p.read_bytes())
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    (out / "snapshot.json").write_text(json.dumps({"env": a.env, "git_head": git, "files": files}, indent=1))
    print(f"snapshot {out} objects={sum(1 for f in files if f.endswith('.o'))}")
    return 0


def cmd_compare(a) -> int:
    A, B = Path(a.a), Path(a.b)
    objs_a = {str(p.relative_to(A)) for p in A.rglob("*.o")}
    objs_b = {str(p.relative_to(B)) for p in B.rglob("*.o")}
    if not objs_a or not objs_b:
        print("no objects in a snapshot")
        return 2
    diffs = []
    for rel in sorted(objs_a | objs_b):
        if rel not in objs_a or rel not in objs_b:
            diffs.append({"object": rel, "why": "present in only one snapshot"})
            continue
        ca, cb = canon_object(A / rel), canon_object(B / rel)
        if ca != cb:
            secs = sorted(k for k in set(ca["sections"]) | set(cb["sections"])
                          if ca["sections"].get(k) != cb["sections"].get(k))
            rel_d = sorted(k for k in set(ca["relocs"]) | set(cb["relocs"]) if ca["relocs"].get(k) != cb["relocs"].get(k))
            diffs.append({"object": rel, "sections": secs[:20], "relocs": rel_d[:20],
                          "symbols_differ": ca["symbols"] != cb["symbols"]})
    elf = {}
    if not a.objects_only:
        ea, eb = canon_elf(A / "firmware.elf"), canon_elf(B / "firmware.elf")
        elf = {k: (ea.get(k), eb.get(k)) for k in sorted(set(ea) | set(eb)) if ea.get(k) != eb.get(k)}
    doc = {"a": str(A), "b": str(B), "objects_compared": len(objs_a & objs_b), "objects_differing": diffs,
           "elf_alloc_sections_differing": sorted(elf), "objects_only": a.objects_only}
    if a.json:
        Path(a.json).write_text(json.dumps(doc, indent=1))
    print(f"objects compared={doc['objects_compared']} differing={len(diffs)}")
    for d in diffs[:15]:
        print("  OBJ", d)
    if not a.objects_only:
        print(f"elf alloc sections differing={len(elf)} {sorted(elf)[:12]}")
    return 0 if not diffs and not elf else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--env", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--repro-git")
    b.add_argument("--repro-epoch", type=int)
    s = sub.add_parser("snapshot")
    s.add_argument("--env", required=True)
    s.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    c.add_argument("--objects-only", action="store_true")
    c.add_argument("--json")
    a = p.parse_args(argv)
    return {"build": cmd_build, "snapshot": cmd_snapshot, "compare": cmd_compare}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
