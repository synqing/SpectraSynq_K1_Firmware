# Addendum to Rev 2 — DJ notation as the M1 authoring format (9 Nov 2026, 19:55 AWST)

Source: https://filiph.net/dj-notation/ (Filip Hráček, v3 Sept 2020, CC-BY 3.0, commercial use welcomed — attribute in docs).

## Ruling (Operations Manager)
ADOPT as (a) the hand-authoring format for the M1 passage, (b) the default section→visual mapping vocabulary for P4.3, (c) directional evaluation data for section inference. DO NOT adopt as a data contract or timebase.

## Symbols → section cue classes
`-` beats only · `+` hits · `~` melody/no beats · `=` drone · `#` riff/tonal shift · `/` build · `\` breakdown · `<` fade in · `>` fade out · `!` detuned prefix · `(−m:ss)` timecode (remaining time).

## Lane C3 — change
Author the 60–90 s passage as ONE notation string with timecodes. Write `dj_notation_import.py`:
- Input: notation string + the identified asset (sha256, sample rate, sample count, duration). Reject if the asset identity is missing.
- Convert every timecode to an absolute SAMPLE index of that asset; remaining-time `(−m:ss)` resolved from the asset's true duration. Record the conversion. Emit section cues {start_sample, end_sample, symbol, cue_id} in strict order; overlapping/unordered timecodes are rejected, never reordered silently.
- Fixtures: one valid string; one with no timecodes (sections only, equal-split REJECTED — require timecodes for M1); one with out-of-order times; one with a timecode beyond asset duration; one with an unknown symbol.
- Section cues select mode / palette / edge role through the K1CT PARAM_SET path (or the typed serial command if PARAM_SET lacks the control — report which). The Prim8 stream still carries the continuous evidence; sections never replace it.

## Default section → visual mapping (P4.3 starting table, judged on the plate, under THE LAW)
| Symbol | Light |
|---|---|
| `-` | percussive gesture only; no harmonic colour movement |
| `+` | discrete hits: instant attack, long decay, otherwise negative space |
| `~` | harmonic colour flow, soft extent, no hit gestures |
| `=` | sustained body with pulse riding on it |
| `#` | hue-family shift event at section start; motion continuous |
| `/` | rising extent/intensity with deliberate anticipation (offline lookahead permitted) |
| `\` | decay into negative space; shorter attack suppression |
| `<` `>` | extent ramps in/out over the section |

## Risks recorded
- Not a contract: no units, overlapping semantics, subjective. Timebase conversion at import only.
- Remaining-time convention breaks across editions → bind to asset hash (A01).
- Sections alone = timer-shaped light (violates law #1). Mandatory pairing with continuous Prim8 evidence.
- Camelot key → palette family: P4 candidate, parked.

## Evaluation hook (P7)
Add ablation B0+S (prepared full-mix Prim8 + notation sections) vs B0. The 300-track Google Sheet is directional ground truth for section inference only; edition mismatch makes its timecodes unreliable for timing.
