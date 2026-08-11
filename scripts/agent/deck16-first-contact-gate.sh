#!/usr/bin/env bash
# deck16-first-contact-gate.sh — Step-1 identity + live digest echo for Deck16.
# Authority: docs/canon/SESSION_CANON_2026-08-09_deck16_ble_backend_haunt_latency.md
# Exit 0 = STEP1_PASS (both peers identified). Exit 2 = STEP1_STOP.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

BENCH_MAC_LC="b4:3a:45:a5:89:b4"
TAB5_MAC_LC="30:ed:a0:e0:c1:a0"
BENCH_CHIP="B489A500"
LIVE_REG_MD5="9b5db3fbb17438367adeaceb541db03b"
LIVE_LAYOUT_SHA="f8e40f6b1ba7b115bb5e9f7310ac69636e0a10c8e478f7584dd1d5547b941510"

echo "════════════════════════════════════════════════════════════"
echo " Deck16 first-contact gate (HF-14 / HF-26)"
echo "════════════════════════════════════════════════════════════"

echo ""
echo "── Live digests on disk (HF-14) ──"
K1_H="$ROOT/SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_identity_v1.h"
TAB_H="$ROOT/tab5_firmware/include/k1_deck_identity_v1.h"
for f in "$K1_H" "$TAB_H"; do
  if [[ ! -f "$f" ]]; then
    echo "STEP1_STOP: missing identity header: $f"
    exit 2
  fi
done

extract_md5() { rg -o 'K1_DECK_IDENTITY_REGISTRY_MD5_HEX "[0-9a-f]+"' "$1" | head -1 | rg -o '[0-9a-f]{32}'; }
extract_layout() {
  # Macro may be split across lines with a trailing backslash.
  python3 - "$1" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r'K1_DECK_IDENTITY_LAYOUT_SHA256_HEX\s*\\\s*\n\s*"([0-9a-f]{64})"', text)
if not m:
    m = re.search(r'K1_DECK_IDENTITY_LAYOUT_SHA256_HEX\s*"([0-9a-f]{64})"', text)
print(m.group(1) if m else "")
PY
}

K1_MD5="$(extract_md5 "$K1_H" || true)"
TAB_MD5="$(extract_md5 "$TAB_H" || true)"
K1_LAY="$(extract_layout "$K1_H" || true)"
TAB_LAY="$(extract_layout "$TAB_H" || true)"

echo "  K1  registry_md5=$K1_MD5"
echo "  Tab5 registry_md5=$TAB_MD5"
echo "  K1  layout_sha=$K1_LAY"
echo "  Tab5 layout_sha=$TAB_LAY"
echo "  expected registry=$LIVE_REG_MD5"
echo "  expected layout  =$LIVE_LAYOUT_SHA"

if [[ "$K1_MD5" != "$LIVE_REG_MD5" || "$TAB_MD5" != "$LIVE_REG_MD5" ]]; then
  echo "WARN: registry MD5 differs from Mirror-purge snapshot — re-verify before citing (HF-14)."
fi
if [[ "$K1_LAY" != "$LIVE_LAYOUT_SHA" || "$TAB_LAY" != "$LIVE_LAYOUT_SHA" ]]; then
  echo "WARN: layout SHA differs from Mirror-purge snapshot — re-verify before citing (HF-14)."
fi
if [[ "$K1_MD5" != "$TAB_MD5" || "$K1_LAY" != "$TAB_LAY" ]]; then
  echo "STEP1_STOP: K1 and Tab5 identity headers disagree — rebuild both from same tree."
  exit 2
fi

echo ""
echo "── USB enumerate (HF-26) ──"
pio device list 2>/dev/null || true
echo ""

set +e
python3 - <<'PY'
import sys
try:
    import serial.tools.list_ports as lp
except ImportError:
    print("STEP1_STOP: pyserial missing")
    sys.exit(2)

BENCH = "B4:3A:45:A5:89:B4"
TAB5 = "30:ED:A0:E0:C1:A0"
bench_port = None
tab5_port = None
aliens = []

for p in lp.comports():
    ser = (p.serial_number or "").upper()
    if not ser or ":" not in ser:
        continue
    print(f"  {p.device}  SER={ser}  {p.description}")
    if ser == BENCH:
        bench_port = p.device
    elif ser == TAB5:
        tab5_port = p.device
    else:
        if p.device.startswith("/dev/cu.usbmodem") or p.device.startswith("/dev/tty.usbmodem"):
            aliens.append((p.device, ser))

print("")
if bench_port:
    print(f"  bench_k1: PRESENT  port={bench_port}  chip_expect=B489A500")
else:
    print("  bench_k1: ABSENT")
if tab5_port:
    print(f"  tab5_p4:  PRESENT  port={tab5_port}  mac=30:ED:A0:E0:C1:A0")
else:
    print("  tab5_p4:  ABSENT")
for d, s in aliens:
    print(f"  alien:    {d} SER={s}  — do NOT substitute for Tab5/bench (HF-26)")

if not bench_port or not tab5_port:
    print("")
    print("STEP1_STOP: required peer(s) absent. Plug Tab5 P4 and/or bench K1; re-run.")
    print("Do not proceed to dark-fade / link / anti-haunt / full71 / C6 soak.")
    sys.exit(2)

print("")
print("STEP1_PORTS_OK")
print(f"DECK16_BENCH_PORT={bench_port}")
print(f"DECK16_TAB5_PORT={tab5_port}")
PY
PORTS_RC=$?
set -e
if [[ "$PORTS_RC" -ne 0 ]]; then
  exit 2
fi

# Upload guard on bench port only (read-only identity proof; no flash).
BENCH_PORT="$(python3 - <<'PY'
import serial.tools.list_ports as lp
for p in lp.comports():
    if (p.serial_number or "").upper() == "B4:3A:45:A5:89:B4":
        print(p.device)
        break
PY
)"

echo ""
echo "── Upload guard (bench only, no flash) ──"
python3 "$ROOT/scripts/platformio/k1_upload_guard.py" \
  --env k1_bench_im69d_ble \
  --upload-port "$BENCH_PORT"
GUARD_RC=$?
if [[ "$GUARD_RC" -ne 0 ]]; then
  echo "STEP1_STOP: upload guard failed for bench (expected chip $BENCH_CHIP)."
  exit 2
fi

echo ""
echo "STEP1_PASS"
echo "Next (manual, read-only): dark-fade silicon → link/admission → anti-haunt."
echo "Then ASK CAPTAIN Lane A (full71 FAIL burn-down) XOR Lane B (C6 exclusive soak)."
echo "Canon: docs/canon/SESSION_CANON_2026-08-09_deck16_ble_backend_haunt_latency.md"
exit 0
