# Preview R1.1 contract

This isolated mockup is a read-only decision surface. It does not modify the production Colour Lab and contains no transport, persistence or export path.

## Channel authority

- Primary and Secondary always keep separate frames, LED counts, pixel arrays, summaries and inspector values.
- Secondary `inherit` resolves Primary's effective look inside Secondary's own frame.
- `P=unknown, S=inherit` remains unknown and selects the pre-correction reference unless a separately explicit local draft simulation exists.
- `slot15Known=false` selects the pre-correction reference and says that slot-15 contents are unknown. It never claims a confirmed tune or known tune simulation.
- Both `P=15, S=inherit, slot15 unknown` and `P=15, S=15, slot15 unknown` are permanent evidence states.
- Equal pixels never collapse the two rows.

## Comparison

- **Output** compares exact cached RGB16 triplets and LED counts.
- **Preview basis** compares pattern provenance, targeting, correction provenance, pre/post selection, direct/inherited look relationship, effective look, slot knowledge, applied tune and render scale.
- `LED values match · Preview basis differs` is valid and intentionally represented.

## Inspector

- One persistent `selectedLed` state is shared by pointer, touch, keyboard arrows and the number input.
- Both channel values are read from the exact cached frames used by the canvases.
- A missing index says `Not present`; it never clamps or borrows another channel's value.
- Safety failure clears stale values. Product-policy failure retains valid local analysis while product-output boundaries remain blocked.

## Visual boundaries

- The diffusion view is a relative browser model only.
- No device/LUT readback or physical colour-match claim is made.
- Preview has navigation/handoff only. Source owns Test; Tune owns Apply and Save.
- No transfer curve, decorative motion, hue-wheel or wheel-spanning product visual exists here.
