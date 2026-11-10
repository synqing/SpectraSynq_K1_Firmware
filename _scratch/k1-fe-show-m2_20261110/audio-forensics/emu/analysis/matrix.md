
### Edge A

| mode | level | guard | mean bright | motion | dyn range p95-p5 | r(RMS) lag0 | r best | lag (hops) | full-scale frames | hue bins | loud/quiet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 22 | fix | ON | 0.022 | 0.0016 | 0.085 | -0.289 | -0.289 | 0 | 0.000 | 10 | 0.36 |
| 22 | fix | OFF | 0.016 | 0.0012 | 0.066 | -0.495 | -0.495 | 1 | 0.000 | 7 | 0.12 |
| 22 | room | ON | 0.073 | 0.0061 | 0.166 | -0.335 | -0.330 | 40 | 0.000 | 15 | 0.51 |
| 22 | room | OFF | 0.075 | 0.0062 | 0.174 | -0.398 | -0.339 | 40 | 0.000 | 15 | 0.45 |
| 32 | fix | ON | 0.042 | 0.0363 | 0.033 | 0.424 | 0.519 | 36 | 0.000 | 12 | 1.33 |
| 32 | fix | OFF | 0.034 | 0.0223 | 0.027 | 0.374 | 0.451 | 34 | 0.000 | 14 | 1.20 |
| 32 | room | ON | 0.039 | 0.0347 | 0.066 | -0.320 | -0.300 | 35 | 0.000 | 14 | 0.72 |
| 32 | room | OFF | 0.026 | 0.0234 | 0.037 | -0.392 | -0.383 | 40 | 0.000 | 15 | 0.61 |
| 18 | fix | ON | 0.023 | 0.0090 | 0.037 | -0.597 | -0.302 | 40 | 0.000 | 13 | 0.53 |
| 18 | fix | OFF | 0.011 | 0.0034 | 0.034 | -0.749 | -0.735 | 26 | 0.000 | 14 | 0.04 |
| 18 | room | ON | 0.026 | 0.0090 | 0.045 | -0.544 | -0.294 | 40 | 0.000 | 14 | 0.51 |
| 18 | room | OFF | 0.028 | 0.0090 | 0.063 | -0.560 | -0.453 | 40 | 0.000 | 14 | 0.41 |

### Edge B

| mode | level | guard | mean bright | motion | dyn range p95-p5 | r(RMS) lag0 | r best | lag (hops) | full-scale frames | hue bins | loud/quiet |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 22 | fix | ON | 0.022 | 0.0016 | 0.085 | -0.286 | -0.286 | 0 | 0.000 | 14 | 0.36 |
| 22 | fix | OFF | 0.016 | 0.0012 | 0.065 | -0.498 | -0.498 | 1 | 0.000 | 9 | 0.12 |
| 22 | room | ON | 0.074 | 0.0059 | 0.170 | -0.320 | -0.311 | 40 | 0.000 | 14 | 0.53 |
| 22 | room | OFF | 0.076 | 0.0062 | 0.177 | -0.403 | -0.346 | 40 | 0.000 | 15 | 0.44 |
| 32 | fix | ON | 0.048 | 0.0411 | 0.039 | 0.453 | 0.534 | 36 | 0.000 | 7 | 1.36 |
| 32 | fix | OFF | 0.040 | 0.0257 | 0.035 | 0.406 | 0.474 | 35 | 0.000 | 12 | 1.24 |
| 32 | room | ON | 0.043 | 0.0377 | 0.061 | -0.241 | -0.219 | 35 | 0.000 | 14 | 0.81 |
| 32 | room | OFF | 0.027 | 0.0236 | 0.034 | -0.343 | -0.340 | 38 | 0.000 | 14 | 0.68 |
| 18 | fix | ON | 0.026 | 0.0101 | 0.040 | -0.586 | -0.286 | 40 | 0.000 | 11 | 0.55 |
| 18 | fix | OFF | 0.013 | 0.0037 | 0.037 | -0.751 | -0.739 | 27 | 0.000 | 11 | 0.05 |
| 18 | room | ON | 0.027 | 0.0091 | 0.044 | -0.574 | -0.313 | 40 | 0.000 | 14 | 0.52 |
| 18 | room | OFF | 0.028 | 0.0091 | 0.057 | -0.554 | -0.436 | 40 | 0.000 | 14 | 0.44 |

### Input and guard trigger per case

| case | frames | raw peak max | raw peak p95 (window) | p95 loud 128-135 s | p95 quiet 137-143 s | peak_scaled >= 0.92 | peak_scaled mean | commands rejected |
|---|---|---|---|---|---|---|---|---|
| fix-m18-off | 2000 | 4096 | 3872 | 3992 | 1210 | 0.620 | 0.876 | ['0', '0', '0', '0', '0'] rejects=0 |
| fix-m18-on | 2000 | 4096 | 3872 | 3992 | 1210 | 0.297 | 0.809 | ['0', '0', '0', '0'] rejects=0 |
| fix-m22-off | 2000 | 4096 | 3872 | 3992 | 1210 | 0.620 | 0.876 | ['0', '0', '0', '0', '0'] rejects=0 |
| fix-m22-on | 2000 | 4096 | 3872 | 3992 | 1210 | 0.297 | 0.809 | ['0', '0', '0', '0'] rejects=0 |
| fix-m32-off | 2000 | 4096 | 3872 | 3992 | 1210 | 0.620 | 0.876 | ['0', '0', '0', '0', '0'] rejects=0 |
| fix-m32-on | 2000 | 4096 | 3872 | 3992 | 1210 | 0.297 | 0.809 | ['0', '0', '0', '0'] rejects=0 |
| room-m18-off | 2000 | 250 | 236 | 244 | 74 | 0.208 | 0.681 | ['0', '0', '0', '0', '0'] rejects=0 |
| room-m18-on | 2000 | 250 | 236 | 244 | 74 | 0.208 | 0.681 | ['0', '0', '0', '0'] rejects=0 |
| room-m22-off | 2000 | 250 | 236 | 244 | 74 | 0.208 | 0.681 | ['0', '0', '0', '0', '0'] rejects=0 |
| room-m22-on | 2000 | 250 | 236 | 244 | 74 | 0.208 | 0.681 | ['0', '0', '0', '0'] rejects=0 |
| room-m32-off | 2000 | 250 | 236 | 244 | 74 | 0.208 | 0.681 | ['0', '0', '0', '0', '0'] rejects=0 |
| room-m32-on | 2000 | 250 | 236 | 244 | 74 | 0.208 | 0.681 | ['0', '0', '0', '0'] rejects=0 |
| room-m32-on-rep | 2000 | 250 | 236 | 244 | 74 | 0.208 | 0.681 | ['0', '0', '0', '0'] rejects=0 |

### Byte identity

| pair | edge A | edge B | all bytes identical |
|---|---|---|---|
| room-m22-on vs room-m22-off | 1880/2000 frames differ, first hop 1600, mean abs diff 0.0810 | 1880/2000 frames differ, first hop 1600, mean abs diff 0.0808 | False |
| room-m32-on vs room-m32-off | 2000/2000 frames differ, first hop 1600, mean abs diff 0.0348 | 2000/2000 frames differ, first hop 1600, mean abs diff 0.0322 | False |
| room-m18-on vs room-m18-off | 2000/2000 frames differ, first hop 1600, mean abs diff 0.0341 | 2000/2000 frames differ, first hop 1600, mean abs diff 0.0315 | False |
| fix-m22-on vs fix-m22-off | 2000/2000 frames differ, first hop 1600, mean abs diff 0.0193 | 2000/2000 frames differ, first hop 1600, mean abs diff 0.0194 | False |
| fix-m32-on vs fix-m32-off | 2000/2000 frames differ, first hop 1600, mean abs diff 0.0532 | 2000/2000 frames differ, first hop 1600, mean abs diff 0.0588 | False |
| fix-m18-on vs fix-m18-off | 2000/2000 frames differ, first hop 1600, mean abs diff 0.0250 | 2000/2000 frames differ, first hop 1600, mean abs diff 0.0288 | False |
| room-m32-on vs room-m32-on-rep (determinism control) | identical (2000 frames) | identical (2000 frames) | True |
