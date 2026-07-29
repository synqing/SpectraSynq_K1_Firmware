# Track B — 512-point FFT STM evidence bundle

**Track:** WB-3 Track B (bench FFT producer, **mutually exclusive** with `K1_STM`).  
**Policy:** `docs/forensics/stm-producer/WB3_REFERENCE_ATTESTATION.md`, spike steps in `WB3_FFT512_FEASIBILITY.md`.

## Reference gate

**E5 / attestation:** **INDETERMINATE** until Track B checklist (TB-1…TB-6) in `WB3_REFERENCE_ATTESTATION.md` is satisfied or Captain waives in `WB3_COMPARATIVE_DECISION_RECORD.md`.

## Branch / worktree

- From `origin/main`: e.g. `bench/wb3-track-b-fft512`
- Never combine native `K1_STM` and FFT bench producer in one image

## Evidence checklist (per `<run-id>/`)

- [ ] `manifest.json` — reference hashes, fixture list, `flash_required`, rollback
- [ ] `reference_attestation.md` — copy of completed TB checklist
- [ ] `fft_microbench.csv` — optional host or on-device (see feasibility doc)
- [ ] `core0/` — treatment vs baseline per bench procedure
- [ ] `vp/` — reference vs candidate when reference valid
- [ ] `gate0_clangd.txt`

## Hardware

**This packet is scaffolding only** until an independent 512-point reference exists. No flash, playback, or FFT firmware integration in the 2026-07-29 doc session.
