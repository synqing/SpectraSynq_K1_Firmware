---
abstract: "Captain correction 2026-09-08: prior PCM stimulus run had background music. Clock/DMA/SRC/soak/ST25 remain valid. Any L/R, FR, THD, amplitude, crosstalk, or Line-vs-MIC claim from that run is CONTAMINATED_BACKGROUND_PLAYBACK / INADMISSIBLE_FOR_SIGNAL_CHARACTERISATION."
---

# Contaminated stimulus correction

Captain: during a prior stimulus evaluation, normal music continued while the test stimulus played. The fixture was not the only source.

Stamp also written at
`docs/forensics/runtime-evidence/20260907T-pcm1808-st25-bringup/CONTAMINATED_STIMULUS_STAMP.md`
(new file; original receipts not rewritten).

## VALID (keep)

| Artefact | What remains admissible |
|---|---|
| `PCMCLK_RECEIPT.txt` clock block | LRCK 47,985.9 Hz, BCLK 3,069,048.5 Hz, ratio 63.957, mode `48K_MASTER_I2S24`, DMA-rate 47,997.9 stereo frames/s |
| `pcmclk-boot.txt` / `pcmclk-reset.txt` transport lines | I2S1 init PASS, SRC count invariant PASS, err/short/clip counters **as then defined** |
| `PCM-R1-SOAK-60s.txt` | 60 s stream soak `PASS_STREAM=1`, err=0 short=0 clip=0. **Not** a signal characterisation. Host `dma_hz≈46782` is the open P1 question, not a clock disproof. |
| `PCM-SOAK-10MIN.txt` | 10 min stream soak `PASS_STREAM=1`, err=0 short=0 clip=0, host `dma_hz=46823.5`. Same caveat. |
| `ST25ID_RECEIPT.txt` + boot logs | SPI identity `0x31`, family ST25R3916B, PASS. RFAL/tag still unproven. |
| Restore dump | `restore-pre-pcm-probe-0x0-2MB.bin` sha256 `1e2744256eaaaf170f18600f5daafc39bc33bce1521bd1067f92f48a6a3a3a8e` re-hashed this session MATCH. |

## CONTAMINATED / INADMISSIBLE_FOR_SIGNAL_CHARACTERISATION

Any stimulus-dependent claim from that run, including:

- physical LEFT/RIGHT DMA slot map
- frequency response
- amplitude response
- THD / THD+N
- SINAD / SNR
- crosstalk / channel separation
- clean fixture latency / correlation
- Line-In versus MIC parity

`PCMCLK_RECEIPT.txt` already recorded that Mac `afplay` on a Multi-Output Device did not move PCM RMS versus baseline. That is **not** a channel-map result. It is an analog-path / routing failure **and** a contaminated fixture.

Existing `tools/pcm1808/fixtures/*.wav` from 2026-09-07 are **unguarded** (no 2 s silence bands). Do not reuse them for P3. P3 must generate hashed guarded fixtures and prove Mac→AUX with a quiet-tone-quiet sequence.

## Fixture-integrity rule (mandatory from this session)

```
STOP unrelated playback
  → capture pre-stimulus quiet guard
  → verify no programme-bearing signal
  → play exactly ONE fixture
  → capture post-stimulus quiet guard
  → accept or reject
```

Guarded WAV shape: 2 s silence + stimulus + 2 s silence. If either guard contains unrelated programme, reject the measurement.

Label every P3 metric `END_TO_END_LINE_LANE_METRIC` (source + cable + PCM module + S3 capture). Not an intrinsic PCM1808 silicon metric.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | agent:grok | Annotate contaminated stimulus; do not delete 20260907 evidence. |
