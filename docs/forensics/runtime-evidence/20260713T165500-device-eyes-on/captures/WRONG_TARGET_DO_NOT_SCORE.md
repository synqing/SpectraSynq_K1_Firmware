# Wrong-Target Capture Quarantine

[FACT] The `animals_128_*` and `dreams_128_*` artefacts in this directory were
captured from chip `F887A500` on port `12401`, not Captain's authoritative bench
test K1 `B489A500` on port `1401`.

[FACT] These artefacts are invalid for the DEVICE eyes-on gate and must not be
included in any Acc1, Acc2, octave-error, locked-fraction, or per-bucket result.

[FACT] A third `loreen_127` acquisition was interrupted immediately when the
target error was identified and did not produce a completed capture artefact.

