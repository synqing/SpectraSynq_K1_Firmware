#!/usr/bin/env bash
# deck_fonts.sh — deterministic LVGL font assets for P4 deck (Countach + Berkeley).
# Countach sources are TRIAL OTFs (bench eval only). Regenerate from licensed
# binaries after Captain purchase.
#
# OPTICAL LAW: lv_font_conv --size is NOT optical pixel height. Hero ink is
# measured on native_sdl stills (digit box_h ∈ [36,40]); see
# _scratch/precision_bay_r1/optical_gate_font_ladder_r1/probes/countach_probe_log.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/src/fonts"
BPP=4
CONV=(lv_font_conv --no-compress --no-prefilter --bpp "${BPP}" --format lvgl --lv-include lvgl.h)

COUNTACH_DIR="${COUNTACH_DIR:-${HOME}/Downloads/countach-font-family}"
BOLD="$(ls -1 "${COUNTACH_DIR}"/Countach-Bold-TRIAL-*.otf 2>/dev/null | head -1 || true)"
BOLD_IT="$(ls -1 "${COUNTACH_DIR}"/Countach-BoldItalic-TRIAL-*.otf 2>/dev/null | head -1 || true)"
MONO_TTF="${ROOT}/src/fonts/BerkeleyMono-Regular.ttf"

# Spec subset: 0x20,0x25,0x2D,0x30-0x39,0x41-0x5A,0xB7
# TRIAL OTFs lack 0x25 (%) and 0xB7 (middot) — convert intersection only;
# regenerate full subset from licensed binaries after purchase.
COUNTACH_RANGE='0x20,0x2D,0x30-0x39,0x41-0x5A'
COUNTACH_STATE_RANGE='0x20,0x41-0x5A'
# Instrument register: printable ASCII. Middot (0xB7) absent in this TTF —
# deck_ui uses ASCII hyphen/dot separators where needed.
MONO_RANGE='0x20-0x7E'

# Live hero --size (enum name DISPLAY_55 / file countach_bolditalic_55.c).
# Optical band locked by P1.1 probe: digit box_h ∈ [36,40] at size 55 (lh 39).
HERO_CONV_SIZE="${HERO_CONV_SIZE:-55}"

die() { echo "deck_fonts.sh: $*" >&2; exit 1; }

command -v lv_font_conv >/dev/null || die "lv_font_conv not found (npm i -g lv_font_conv)"
[[ -n "${BOLD}" && -f "${BOLD}" ]] || die "Countach Bold TRIAL OTF missing under ${COUNTACH_DIR}"
[[ -n "${BOLD_IT}" && -f "${BOLD_IT}" ]] || die "Countach BoldItalic TRIAL OTF missing under ${COUNTACH_DIR}"
[[ -f "${MONO_TTF}" ]] || die "BerkeleyMono-Regular.ttf missing at ${MONO_TTF}"

mkdir -p "${OUT}"

echo "deck_fonts.sh: Bold=${BOLD}"
echo "deck_fonts.sh: BoldItalic=${BOLD_IT}"
echo "deck_fonts.sh: Mono=${MONO_TTF}"
echo "deck_fonts.sh: bpp=${BPP}"
echo "deck_fonts.sh: HERO_CONV_SIZE=${HERO_CONV_SIZE} (--size ≠ optical px)"

conv_countach() {
  local size="$1" face="$2" range="$3" name="$4"
  "${CONV[@]}" --size "${size}" --font "${face}" -r "${range}" \
    --lv-font-name "${name}" -o "${OUT}/${name}.c"
  echo "  wrote ${name}.c"
}

conv_mono() {
  local size="$1" name="$2"
  "${CONV[@]}" --size "${size}" --font "${MONO_TTF}" -r "${MONO_RANGE}" \
    --lv-font-name "${name}" -o "${OUT}/${name}.c"
  echo "  wrote ${name}.c"
}

echo "== Countach Bold Italic LIVE hero (unified mode+palette; file name stays *_55) =="
# Canon: Bold Italic digits only. Range = space/hyphen/digits.
NUMERAL_RANGE='0x20,0x2D,0x30-0x39'
conv_countach "${HERO_CONV_SIZE}" "${BOLD_IT}" "${NUMERAL_RANGE}" countach_bolditalic_55

# Archive conversions (BI40/BI89 / legacy Bold) — OFF by default; not live filter assets.
if [[ "${GEN_ARCHIVE:-0}" == "1" ]]; then
  echo "== ARCHIVE (GEN_ARCHIVE=1): BI 40/89 + legacy Bold faces =="
  conv_countach 89 "${BOLD_IT}" "${NUMERAL_RANGE}" countach_bolditalic_89
  conv_countach 40 "${BOLD_IT}" "${NUMERAL_RANGE}" countach_bolditalic_40
  conv_countach 89 "${BOLD}" "${COUNTACH_RANGE}" countach_bold_89
  conv_countach 55 "${BOLD}" "${COUNTACH_RANGE}" countach_bold_55
  conv_countach 34 "${BOLD}" "${COUNTACH_RANGE}" countach_bold_34
  conv_countach 34 "${BOLD_IT}" "${COUNTACH_STATE_RANGE}" countach_bolditalic_34
else
  echo "== ARCHIVE skipped (set GEN_ARCHIVE=1 to emit BI40/BI89 + legacy Bold) =="
fi

echo "== Berkeley Mono (ALL words + instrument; 21/24/34/55) =="
conv_mono 21 berkeley_mono_21
conv_mono 24 berkeley_mono_24
conv_mono 34 berkeley_mono_34
conv_mono 55 berkeley_mono_55

# Header declaring the live ladder (no mono 89; BI40/BI89 not live).
cat > "${OUT}/deck_fonts.h" <<'EOF'
#pragma once
/**
 * Deck font declarations — Countach Bold Italic (hero numerals) + Berkeley Mono (all words).
 * Generated/updated by tools/deck_fonts.sh. Do not hand-edit glyph .c files.
 *
 * LICENCE: Countach assets currently from TRIAL OTFs — bench eval flashes only.
 * After Captain licence lands, re-run deck_fonts.sh against licensed binaries.
 *
 * Canon: Countach Bold Italic = mode/palette index numerals ONLY (unified DISPLAY_55).
 *        Berkeley Mono        = every word (names, labels, keys, brand, state).
 * Optical: --size ≠ ink px; hero digit box_h target [36,40] (see optical_scale_ladder_r1.json).
 */

#include <lvgl.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Live hero numerals — Countach Bold Italic (digits + hyphen + space) */
LV_FONT_DECLARE(countach_bolditalic_55);

/* Instrument / all words — Berkeley Mono ladder 21/24/34/55 */
LV_FONT_DECLARE(berkeley_mono_21);
LV_FONT_DECLARE(berkeley_mono_24);
LV_FONT_DECLARE(berkeley_mono_34);
LV_FONT_DECLARE(berkeley_mono_55);

#ifdef __cplusplus
}
#endif
EOF

echo "deck_fonts.sh: wrote deck_fonts.h"
echo "deck_fonts.sh: DONE"
