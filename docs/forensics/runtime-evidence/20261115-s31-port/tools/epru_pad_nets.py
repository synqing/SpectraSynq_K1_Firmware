#!/usr/bin/env python3
"""Read-only: stream an EasyEDA Pro .epro2 and print pad -> net for chosen designators.

Takes the highest-ticket record per (doc, type, id). PCB doc: COMPONENT, ATTR (Designator),
PAD_NET. FOOTPRINT docs: PAD id -> pad number. Output JSON on stdout.
"""
import io
import json
import sys
import zipfile

archive, epru = sys.argv[1], sys.argv[2]
want = set(sys.argv[3].split(","))

docs = []  # (dochead, records{(type,id): (ticket, body)})
cur = None
with zipfile.ZipFile(archive) as z, z.open(epru) as fh:
    for raw in io.TextIOWrapper(fh, encoding="utf-8", errors="replace"):
        raw = raw.rstrip("\n")
        if "||" not in raw:
            continue
        head_s, body_s = raw.split("||", 1)
        try:
            head = json.loads(head_s)
        except Exception:
            continue
        body_s = body_s[:-1] if body_s.endswith("|") else body_s
        if head.get("type") == "DOCHEAD":
            cur = {"head": json.loads(body_s), "recs": {}}
            docs.append(cur)
            continue
        if cur is None:
            continue
        t = head.get("type")
        if t not in ("COMPONENT", "ATTR", "PAD_NET", "PAD"):
            continue
        key = (t, head.get("id"))
        tk = head.get("ticket", 0)
        try:
            body = json.loads(body_s) if body_s else None
        except Exception:
            body = None
        prev = cur["recs"].get(key)
        if prev is None or tk >= prev[0]:
            cur["recs"][key] = (tk, body)

fp_pads = {}
for d in docs:
    if d["head"].get("docType") == "FOOTPRINT":
        pads = {}
        for (t, i), (tk, b) in d["recs"].items():
            if t == "PAD" and isinstance(b, dict):
                pads[i] = b.get("num") if "num" in b else b.get("number")
        fp_pads[d["head"]["uuid"]] = pads

out = {}
for d in docs:
    if d["head"].get("docType") != "PCB":
        continue
    recs = d["recs"]
    desig = {}
    fp_attr = {}
    for (t, i), (tk, b) in recs.items():
        if t == "ATTR" and isinstance(b, dict) and b.get("key") == "Designator":
            desig[b.get("parentId")] = b.get("value")
        if t == "ATTR" and isinstance(b, dict) and b.get("key") == "Footprint":
            fp_attr[b.get("parentId")] = b.get("value")
    comps = {i: b for (t, i), (tk, b) in recs.items() if t == "COMPONENT" and isinstance(b, dict)}
    for (t, i), (tk, b) in recs.items():
        if t != "PAD_NET" or not isinstance(b, dict):
            continue
        ident = json.loads(i)
        cid, padid = ident[1], ident[3]
        name = desig.get(cid)
        if name not in want:
            continue
        comp = comps.get(cid, {})
        fp = fp_attr.get(cid) or (comp.get("attrs") or {}).get("Footprint")
        pads = fp_pads.get(fp)
        if pads is None or padid not in pads:
            continue  # binding to a pad the instance's footprint does not have (stale record)
        out.setdefault(name, []).append({"pad_id": padid, "num": pads[padid], "net": b.get("padNet"),
                                          "footprint": fp})
    out["_pcb_doc"] = d["head"].get("uuid")
for k, v in out.items():
    if isinstance(v, list):
        v.sort(key=lambda r: (int(r["num"]) if str(r["num"]).isdigit() else 999, str(r["num"])))
json.dump(out, sys.stdout, indent=1)
