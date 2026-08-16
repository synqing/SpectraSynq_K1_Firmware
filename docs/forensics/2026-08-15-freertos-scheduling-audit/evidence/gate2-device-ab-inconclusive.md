# Gate 2 device A/B receipt — complete service matrix, product inconclusive

Date: 2026-08-15
Device: B489A500 / USB serial `B4:3A:45:A5:89:B4`
Port used explicitly: `/dev/cu.usbmodem12401`
Source checkpoint in every device build identity: `35de4e53`

## Verdict

```text
DEVICE_IDENTITY                    = PASS
NO_PLAYBACK_SERVICE_MATRIX         = COMPLETE_NEGATIVE_WITNESS
CAPTAIN_CONFIRMED_REAL_MUSIC       = PASS
REAL_MUSIC_SERVICE_MATRIX          = COMPLETE_NEGATIVE_WITNESS
GDFT_ONLY_TAIL_MARGIN              = FAIL_ALL_CANDIDATES
SEQUENTIAL_20S_PRODUCT_COMPARISON  = INCONCLUSIVE_BY_CAPTAIN
FULL_SEMANTIC_ACCEPTANCE           = NOT_VERIFIED
GATE2_SELECTION                    = BLOCKED_OPEN
GATE3_ENTRY                        = BLOCKED_BY_GATE2
BENCH_FINAL_STATE                  = CROSS0_BASELINE_RESTORED
```

No production GDFT flag changed. Cross40 and cross80 remained non-shippable probe
environments. The bench was restored to `k1_bench_scheduling_baseline_probe`; the
post-restore running identity was:

```text
BUILD: version=40103 git=35de4e53 epoch=1786778678 env=k1_bench_scheduling_baseline_probe
```

## Complete service matrix

Each replacement capture used a five-second device acquisition and a bounded 90-second
serial-export wait. In all six runs, the `APCAD_CAPTURE_BEGIN` count, exported row count
and `APCAD_CAPTURE_DONE` count are identical; device `dropped=0`. Therefore these are
complete captures rather than the prefixes produced by the superseded 15-second runs.

"No playback" means the host launched no audio player. It is not claimed as acoustic
silence. "Real music" used the same beginning of `Anchor Point` by Ahmed Spins / Stevo
Atambire through MacBook Pro Speakers after Captain explicitly confirmed it was audible
at a suitable level. Track SHA-256:
`02925982cf3900d1925fa0338db8e26432c265f7ca18ee93a06818dd4079a938`.

| Fixture | Cross | Complete rows | AP Hz | Active median | Active p95 | Active p99 | Frames over 7.5 ms | GDFT median | Newest-sample-to-publish p99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| no playback | 0 | 485 | 96.84 | 8,470 us | 10,537 us | 10,816 us | 485 | 7,134 us | 10,639 us |
| no playback | 40 | 667 | 133.33 | 5,445 us | 7,645 us | 7,941 us | 65 | 4,048 us | 7,874 us |
| no playback | 80 | 667 | 133.33 | 5,083 us | 7,317 us | 7,571 us | 10 | 3,693 us | 7,498 us |
| real music | 0 | 465 | 92.86 | 9,375 us | 11,425 us | 11,820 us | 465 | 7,174 us | 11,737 us |
| real music | 40 | 640 | 127.85 | 6,431 us | 8,534 us | 8,721 us | 162 | 4,095 us | 8,655 us |
| real music | 80 | 664 | 132.68 | 6,048 us | 8,040 us | 8,422 us | 134 | 3,778 us | 8,352 us |

Every complete capture has zero frame-index gaps, zero capture-sequence gaps, zero
timestamp-order failures, zero I2S failures and zero byte-count failures. Assumption ID
1 remains the truthful timestamp boundary: I2S read-return is the newest-sample estimate,
not a hardware sample timestamp.

The pre-registered Gate-0 service ceiling is p99 no greater than 80% of the 7.5 ms AP
arrival period: 6.0 ms. Cross0 cannot sustain the arrival period. Cross40 and cross80
recover most or all average cadence, but their real-music active p99 values are 8.721 ms
and 8.422 ms. All candidates therefore fail the service contract. Cross80 additionally
has the weakest spectral geometry: a 1,280 Hz maximum cell and 248.397 Hz worst
representable centre error. GDFT shortening alone does not close Gate 2.

## Superseded partial captures

The original six 15-second acquisitions are retained only as partial negative witnesses.
Their host dump timed out before `APCAD_CAPTURE_DONE`, leaving 388–1,043 buffered rows
unexported per run. Zero gaps within those prefixes did not prove complete capture. They
are not used in the table above and must not be promoted as service-matrix acceptance.
The capture script now marks an incomplete dump `F_incomplete_serial_dump` and exits
non-zero, preventing this failure from silently recurring.

## Product comparison authority

Captain confirmed the music was audible before any music-labelled capture. The same
20-second track beginning was then shown sequentially on one unit:

- Candidate A / cross0: musically convincing;
- Candidate B / cross40: about the same as A;
- Candidate C / cross80: no meaningful difference could be judged among all three.

Captain rejected the comparison as too short and structurally weak. The replacement
product-acceptance contract is at least two authorised K1 units running different builds
simultaneously, multiple real tracks, and approximately 30–60 minutes of observation.
Only one authorised K1 is present. This is a product-gate correction, not a perceptual
win or loss for any candidate.

## Complete capture artefacts

Only the six `gate2v3_*` filtered APCAD logs and summaries are admissible. Raw serial
duplicates are intentionally not promotion evidence.

```text
8b20a030641ce673a8623db1dde6fabd2e73be80ea8d143a7adb7a66d129f58e  music cross0 APCAD
442cef829e529cec3782d96d3dd2cc2c2c36b1570f0d1746da88101dc672182c  music cross40 APCAD
854a67a7aa5097d2b44295d5c7f3d5ea68fa98020c7b625401a582932ee6fed0  music cross80 APCAD
804a105653073b4467d956b68eae28670bd5a80fe6cbad6a1241b36ddee7cd75  no-playback cross0 APCAD
c75862eff1649c658294bb3ec114c618c91a209c81195bdb7e2bfc0667fc1138  no-playback cross40 APCAD
1fc34b4c924c8f32bab45c9eb5e34b4abfa134d3806f74f0c9513a780c44f3c1  no-playback cross80 APCAD

088d8f725944776ac1ff4fbfbcbdc945233c525f6d6c04613af0d17450273297  music cross0 summary
23c5196046b9437dc33019693fb49354a3a654a11130eec4f8e9c3b200c84662  music cross40 summary
537b6a4f5db556f22ee9dacfe0161ccb9a49582136b403d5ff17f17296868c76  music cross80 summary
08313bb56615434854eee58756b2846b9ce8db27c1469ace648960d908baa71e  no-playback cross0 summary
1b57d91d349245c7133a13071ce7d9aeec4f7998c4af31d9ee64be91b226760c  no-playback cross40 summary
e2c561a50d3b2ebe9f6e4032b545435c84da19bf15bfbfed170b915b58a9bc7f  no-playback cross80 summary
```

## Transport incident and boundaries

The first baseline upload at 921,600 baud wrote every flash region through 100% but lost
the final acknowledgement. Read-only bootloader identity plus the running `:build` and
`:chip_id` responses proved the intended image had landed, so no blind retry was made.
All three matrix environments now share a 460,800 baud upload transport; subsequent
guarded uploads completed normally. This setting changes no firmware timing variable.

The capture matrix does not prove full onset, beat, chord or visual semantic equivalence,
physical photon latency, or product preference. No calibration, generated audio, radio
enablement, priority change, task extraction, sample-rate/hop change, persistence
operation or production-unit upload occurred.
