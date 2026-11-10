"""Probe the headless PRISM minimal editor (127.0.0.1:7791) through the same HTTP API app.js uses."""
import hashlib, json, sys, urllib.request
BASE = "http://127.0.0.1:7791"
M2 = "/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-compose"
P = M2 + "/projects/ci_click_3s"
def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
st, b = req("GET", "/api/state"); print("GET /api/state", st, b.decode().strip())
bundle = json.load(open(P + "/out/pre_edit/run-a/showbundle.json"))
st, b = req("POST", "/api/replay", {"hz": 120, "bundle": bundle})
print("POST /api/replay", st, "sha256", hashlib.sha256(b).hexdigest(), "bytes", len(b))
st, b = req("POST", "/api/instrument/profile", {"profile_id": "prim8_natural_v1_bar_accent"})
print("POST /api/instrument/profile (edited id)", st, b.decode().strip())
st, b = req("POST", "/api/instrument/profile", {"profile_id": "prim8_natural_v1"})
print("POST /api/instrument/profile (v1)", st, b.decode().strip())
payload = {"contract": P + "/inputs/contract.json", "stem_features": P + "/inputs/stem_features.json",
           "profile": P + "/mapping/prim8_natural_v1.json", "out": M2 + "/editor_run/editor_compile_showbundle.json",
           "schema_sha": open(P + "/inputs/contract_schema.sha256").read().strip(),
           "compiler_commit": "cc00556d1df2f863c6a0d914ef613886b050a408"}
st, b = req("POST", "/api/instrument/compile", payload)
print("POST /api/instrument/compile (editor payload shape)", st, b.decode().strip())
