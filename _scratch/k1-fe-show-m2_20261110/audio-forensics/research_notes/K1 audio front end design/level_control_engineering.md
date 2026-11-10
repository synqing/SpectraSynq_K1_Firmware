# Level control engineering for an embedded microphone front end (K1 audio front end design)

Scope: what the IM69D130 microphone and the ESP32-S3 PDM-to-PCM path physically deliver, how loud real listening places are, and what the audio-processing, broadcast, hearing-aid, machine-listening and camera industries have learned about automatic level control that keeps dynamics. External research only; no firmware was read. Compiled 10 November 2026.

Conventions used below. dBFS means the level of a sine relative to a full-scale sine (a full-scale sine is 0 dBFS). Counts means signed 16-bit PCM units (full scale is 32,767). Where a number is my own arithmetic from cited inputs, it sits under **Inferences** and the working is shown. "Search excerpt" means the quoted text came from a search-engine result page and I could not open the full source (the site blocked automated access).

---

## 1. Microphone physics and the ESP32-S3 PDM-to-PCM path

### Takeaway
The IM69D130 puts digital full scale at about 130 dB SPL. It stays below 1 % distortion up to 128 dB SPL. Its noise floor is about 25 to 29 dB(A) SPL, depending on clock mode. No realistic venue clips the microphone. A plain 16-bit word, with no extra gain, already covers the microphone's whole usable range to within about 3 to 7 dB of its noise floor. A fixed x21.6 gain (+26.7 dB) applied before a 16-bit clamp adds no resolution. Instead it moves the clipping point down to about 103 dB SPL (sine peak). With typical music crest factors, that means clipping once music reaches roughly 83 to 93 dB SPL RMS, which is loud-party and club level.

### Cited Findings
**IM69D130 datasheet, v1.0, 19 December 2017** ([Infineon datasheet PDF](https://www.infineon.cn/content/dam/infineon/row/public/documents/24/49/infineon-im69d130-datasheet-en.pdf))
- Sensitivity: −37 / −36 / −35 dBFS (min / typ / max) at 1 kHz and 94 dB SPL, in **all operating modes**. Calibrated to ±1 dB (Table 1, p. 5; description, p. 1).
- Acoustic overload point (AOP): 130 dB SPL at THD = 10 %, in all operating modes (Table 1, p. 5).
- THD (2nd to 5th harmonics, 1 kHz): 0.5 % at 94 dB SPL, 1.0 % at 128 dB SPL, 2.0 % at 129 dB SPL, 10 % at 130 dB SPL (Table 1, p. 5). The front page says "distortion does not exceed 1% even at sound pressure levels of 128dBSPL" (p. 1).
- Dynamic range: 105 dB (p. 1).
- SNR and noise floor by PDM clock (Table 1, p. 5; A-weighted):
  - 3.072 MHz: SNR 69 dB(A), noise floor −105 dBFS(A).
  - 2.4 MHz: 68 dB(A), −104 dBFS(A).
  - 1.536 MHz: 66 dB(A), −102 dBFS(A).
  - 768 kHz: 64 dB(A), −101 dBFS(A), measured over a **20 Hz to 8 kHz bandwidth**. The other modes use 20 Hz to 20 kHz.
- Equivalent noise floor: "low equivalent noise floor of 25dBSPL (SNR 69dB(A))" (p. 1). This is the 3.072 MHz figure.
- Low-frequency roll-off: −3 dB at 28 Hz, relative to 1 kHz. Free-field response tolerance at 25 Hz is −2 to −5 dB, and at 60 Hz it is +0.5 to −1.5 dB (Table 1 p. 5; Table 2 p. 6).
- Group delay: 70 µs at 250 Hz, 6 µs at 1 kHz. ADC latency is 6 µs at 1 kHz (Table 1; features list p. 1).
- Clock-defined operating modes, min / typ / max (Table 4, p. 7):
  - 2.9 / 3.072 / 3.3 MHz.
  - 2.1 / 2.4 / 2.65 MHz.
  - 1.05 / 1.536 / 1.9 MHz.
  - 400 / 768 / 950 kHz.
  - Standby at 250 kHz or below.
  - Duty cycle must be 40–60 % below 2.65 MHz.
- Supply current: 980 µA at 3.072 MHz, 620 µA at 1.536 MHz, 300 µA at 768 kHz (Table 5, p. 8).
- Infineon lists "Recordings in a discotheque or at a rock concert" as a target use case (p. 2).

**ESP-IDF I2S PDM RX driver** ([ESP-IDF ESP32-S3 I2S guide](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/i2s.html); [i2s_pdm.h](https://github.com/espressif/esp-idf/blob/master/components/esp_driver_i2s/include/driver/i2s_pdm.h))
- `I2S_PDM_DSR_8S` sets the PDM clock to the PCM sample rate × 64. `I2S_PDM_DSR_16S` sets it to the PCM sample rate × 128. The default macro uses `DSR_8S` (ESP-IDF guide, "PDM RX Mode in PCM Format"; `I2S_PDM_RX_CLK_DEFAULT_CONFIG`).
- PCM sample rate in PDM2PCM mode "usually ranges 16KHz ~ 48KHz". In raw PDM mode the rate is 1.024 to 6.144 MHz (i2s_pdm.h, `sample_rate_hz` comment).
- PDM mode supports a data width of **16 bits only**: "only support 16 bits for PDM mode" (i2s_pdm.h, `data_bit_width`).
- On chips that define `SOC_I2S_SUPPORTS_PDM_RX_HP_FILTER`, the RX slot config has three extra fields:
  - `hp_en`: hardware high-pass filter on or off.
  - `hp_cut_off_freq_hz`: "range 23.3Hz ~ 185Hz", default 35.5 Hz.
  - `amplify_num`: "only a multiplier of the digital PCM data, not the gain of the analog signal", range 1 to 15, default 1.

  Source: i2s_pdm.h, `i2s_pdm_rx_slot_config_t` and `I2S_PDM_RX_SLOT_PCM_FMT_DEFAULT_CONFIG`.
- The **ESP32-S3** capability file defines `SOC_I2S_SUPPORTS_PDM`, `PDM_RX`, `PDM2PCM` and `SOC_I2S_PDM_MAX_RX_LINES (4)`. It does **not** define `SOC_I2S_SUPPORTS_PDM_RX_HP_FILTER` ([esp32s3 soc_caps.h](https://github.com/espressif/esp-idf/blob/master/components/soc/esp32s3/include/soc/soc_caps.h)). The ESP32-P4 file does define it, at line 328 ([esp32p4 soc_caps.h](https://github.com/espressif/esp-idf/blob/master/components/soc/esp32p4/include/soc/soc_caps.h)).
- General PDM practice: digital-microphone interfaces usually provide a power-of-two gain shift that is set to match microphone sensitivity. NXP gives `gainshft = 6` for i.MX RT600 at 24 bits, and XMOS describes an optional shift or attenuation. Both are search excerpts ([NXP AN12590](https://www.NXP.com/docs/en/application-note/AN12590.pdf); [XMOS PDM interface](https://www.xmos.com/documentation/XM-014600-PC/html/doc/user_guide/audio/1_PDM%20microphone%20interface.html)).

### Inferences
- **What digital levels correspond to in SPL.** At −36 dBFS for 94 dB SPL, 0 dBFS = 94 + 36 = **130 dB SPL** (±1 dB from the sensitivity tolerance). This matches the 130 dB SPL AOP. The other points follow:

  | dBFS | dB SPL |
  |---|---|
  | −20 | 110 |
  | −40 | 90 |
  | −60 | 70 |
  | −80 | 50 |

  This assumes the ESP32-S3 PDM2PCM filter maps the microphone's full scale to 16-bit full scale with unity gain. That is **UNVERIFIED** (see Gaps).
- **Sine peak in counts at each level:**

  | dB SPL | Peak counts |
  |---|---|
  | 55 | ≈ 6 |
  | 70 | ≈ 33 |
  | 85 | ≈ 184 |
  | 94 | ≈ 519 |
  | 100 | ≈ 1,036 |
  | 110 | ≈ 3,277 |
  | 120 | ≈ 10,362 |
  | 128 (1 % THD) | ≈ 26,028 |

- **The K1's measured 270-count peak** is −41.7 dBFS peak, a sine-equivalent peak of 88 dB SPL. Music played at 70 to 72 dB SPL RMS, with a sample crest factor of about 16 to 20 dB, would produce peaks of about 230 to 290 counts. So the bench reading fits living-room playback, under the unity-gain assumption.
- **K1 clock mode.** At 12.8 kHz PCM with `DSR_8S`, the PDM clock is 12,800 × 64 = **819.2 kHz**. That falls in the IM69D130's 400–950 kHz low-power mode: SNR 64 dB(A), noise floor −101 dBFS(A), equivalent to about 29 dB(A) SPL, 300 µA. `DSR_16S` would give 1.6384 MHz, in the 1.05–1.9 MHz mode: SNR 66 dB(A), −102 dBFS(A), about 28 dB(A) SPL. Sensitivity and AOP are the same in every mode. So clock mode moves the noise floor by about 1 to 4 dB and never moves the clipping point. 12.8 kHz is also below Espressif's stated typical 16–48 kHz PCM range (support is not ruled out, but it is outside the documented typical range).
- **The 16-bit floor sits just above the microphone's noise floor.**
  - Ideal 16-bit quantisation gives 6.02 × 16 + 1.76 = **98.1 dB** SNR for a full-scale sine. That puts the quantisation floor at about −98 dBFS over 0 to 6.4 kHz, equivalent to about **32 dB SPL**.
  - The microphone's own floor is −101 to −105 dBFS(A), or 25 to 29 dB(A) SPL.
  - So the 16-bit floor is only about 3 to 7 dB above the microphone's A-weighted floor (A-weighting makes the microphone floor look slightly lower than its unweighted value).
  - Living-room music at 55 to 75 dB SPL RMS sits about 23 to 43 dB above the 16-bit floor wideband.
- **Per-bin headroom from the Goertzel analysis.** Each Goertzel bin sees only noise within its own bandwidth, giving a processing gain of about 10·log10((fs/2) / (fs/N)). At 12.8 kHz that is +15 dB for N = 64, +21 dB for N = 256 and +27 dB for N = 1,024. The K1's actual N per bin is not known to me. **Conclusion:** 16-bit PCM without extra gain does not lose musically relevant resolution at living-room levels, provided later arithmetic is done in 32-bit integer or float rather than re-truncated to 16 bits.
- **The fixed gain stage, not the microphone, is what clips.**
  - Multiplying integer samples by 8 × 2.7 = 21.6 (+26.7 dB) adds no information. The quantisation step and the noise floor scale up by the same factor.
  - Clamping at 16 bits after that gain clips any raw sample above 32,767 / 21.6 ≈ 1,517 counts (−26.7 dBFS). That is a sine peak of **103.3 dB SPL**.
  - With music crest factors of 10, 15 or 20 dB, clipping starts at about **93, 88 or 83 dB SPL RMS**.
  - Those levels are a loud home party, and below every measured club average (Section 2). The microphone itself stays linear (under 1 % THD) to 128 dB SPL, about 25 dB higher.
- Because the ESP32-S3 driver exposes no hardware high-pass filter (see the capability files above), DC and sub-sonic removal on the K1 must be done in software. Rumble below the 28 Hz roll-off still reaches the PCM partly attenuated (−2 to −5 dB at 25 Hz). That rumble can dominate a wideband peak detector.

### Gaps
- The ESP32-S3 Technical Reference Manual was not checked for the PDM2PCM filter's internal gain, fixed high-pass or DC behaviour, or the exact mapping of PDM full scale to 16-bit full scale. The unity-gain mapping assumed above is **UNVERIFIED**. The 270-count measurement is consistent with it, but that is not proof.
- I found no Infineon application note giving the IM69D130's unweighted noise spectrum in numbers (Figure 7 is a plot only).
- Whether the K1 build really runs `DSR_8S` at 12.8 kHz is from the brief, not verified.

---

## 2. Typical sound levels, crest factor and bass content

### Takeaway
- **Clubs and concerts:** measured averages are about 94 to 97 dB LAeq, with ranges of 82 to 106 dB. Older reviews give a mean of 103 dBA. WHO's voluntary venue limit is 100 dB LAeq over 15 minutes.
- **Homes:** no controlled study of home listening level was found. Hobbyist reports cluster at about 70 to 85 dB.
- **Crest factor:** modern pop masters run a peak-to-loudness ratio of about 9 to 10 LU. Bass-heavy club music carries much more low-frequency energy than A-weighting shows.

### Cited Findings
- **Toronto:** more than 60 nightclubs measured; "The overall average sound level in all of the nightclubs was 96 dBA". The highest levels were around main dance floors. Sound systems were 10,000 to 40,000 W ([Canadian Audiologist 2015, "Occupational Noise Exposure in Nightclubs"](https://canadianaudiologist.ca/occupational-noise-exposure-in-nightclubs/)).
- **Australia, NAL NOISE database (Beach et al. 2013):**
  - Nightclubs: 82–106 dB LAeq, mean 96.
  - Pop concerts: 85–105 dB LAeq, mean 95.
  - Small live gigs: 86–102 dB LAeq, mean 94.

  Source: [Frontiers in Psychology 2019, "Time to Listen"](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.00607/full).
- **Earlier surveys:** 1970s discotheques averaged 97 dB (Bickerdike and Gregory 1980). Clark's 1991 review gave a mean of 103.4 dBA for discotheques and rock concerts (same Frontiers source).
- **Patron preferences:** Belgian patrons preferred 98 dB LAeq to 103 dB LAeq (Gilles et al. 2014). About two-thirds of silent-disco patrons were satisfied at 89 to 93 dB LAeq (same Frontiers source).
- **WHO standard:** the Global Standard for Safe Listening Venues and Events caps the average at **100 dB LAeq over 15 minutes**, with live monitoring. It is voluntary ([WHO World Hearing Day infographic](https://worldhearingday.org/wp-content/uploads/2022/03/MLS_WHD_Infographic_WHO-LOGO_aw.pdf); news coverage, [Free Malaysia Today, 3 March 2022](https://www.freemalaysiatoday.com/category/leisure/health/2022/03/03/who-sets-new-safe-limit-for-music-venues)). Averaging windows differ by country: 100 dBA over 1 minute in Austria and 100 dBA over 1 hour in Belgium (search excerpt, [ProSoundWeb](https://www.prosoundweb.com/?p=171351)).
- **Bass and weighting:**
  - C-weighting, unlike A-weighting, captures the high low-frequency levels of electronic music such as techno (search excerpt, [Saade bachelor thesis, HS Düsseldorf](https://opus4.kobv.de/opus4-hs-duesseldorf/files/4180/Bachelorarbeit_Saade.pdf)).
  - The same thesis proposed 118 dB LCeq,15min and 99 dB LAeq,30min as limits its surveyed audience accepted (search excerpt).
- **Home listening:** forum reports range from about 70 dB with peaks near 90, to 78–80 dB at the listening position, to 85–95 dB. A hi-fi blog calls 75–78 dB "a common target for intentional and critical listening" and 72 dB or softer typical of late-night listening. These are anecdotal (search excerpts: [whatsbestforum](https://whatsbestforum.com/threads/sound-levels-in-your-listening-space.38366/); [Residential Systems on CEDIA reference level](https://www.residentialsystems.com/features/home-theater/rethinking-reference-level-in-residential-audio)).
- **Crest factor of modern pop.** A study of 120 Billboard Year-End Hot 100 singles measured the peak-to-loudness ratio (PLR: true peak minus integrated loudness) ([Țînț and Drăgulin 2025, Bull. Transilvania Univ. Brașov VIII 18(67)](https://webbut.unitbv.ro/index.php/Series_VIII/article/download/11335/6760/20717)):
  - PLR fell from 12.6 LU (1990) to 10.6 LU (2000) to **9.3 LU (2010 and 2020)**.
  - Mean integrated loudness was −12.5 LUFS (1990), −8.0 LUFS (2010) and −8.8 LUFS (2020).
  - 103 of the 120 tracks exceeded 0 dBTP, reaching up to +3.4 dBTP.
  - The authors link the PLR decline to "low-end-heavy" mixes using up headroom.
- **Crest factor as a measure:** crest factor is peak minus average level in dB. "Average" can mean VU, RMS or loudness, so the number depends on the meter ([Meterplugs, "Crest Factor, PSR and PLR"](https://www.meterplugs.com/blog/2017/05/18/crest-factor-psr-and-plr.html)). PSR is the same idea measured over a 3-second short-term loudness window (same source).

### Inferences
- **Level span the K1 must cover.** Room RMS level runs from about 55 dB SPL (quiet home) to about 106 dB SPL (loudest measured club average). That is a span of about 50 dB. Adding a club peak crest of about 10 to 15 dB, the extreme sample peak is about 120 dB SPL, or −10 dBFS on the IM69D130. Still 8 to 10 dB below its 1 % THD point.
- **Crest factor at the microphone.** PLR of about 9 LU is measured with K-weighting against the true peak of the master file. Acoustic capture adds loudspeaker and room effects, and the K1 does not K-weight. So the sample crest factor seen at the microphone is plausibly 12 to 20 dB. This fits the 270-count check in Section 1, but it is not measured.
- **Bass and peak detectors.** Low-frequency energy dominates the peak and RMS of club music. A wideband peak or RMS detector will therefore be driven by the kick drum and sub-bass. That matches the pumping mechanism described in Section 3.

### Gaps
- No peer-reviewed survey of domestic music listening levels was found. The brief's 55 to 75 dB SPL range for living rooms is not confirmed by a primary source.
- Measured LCeq minus LAeq figures by genre were not obtained (an IOA 2024 genre table was referenced but not accessible).
- Festival front-of-house levels specifically were not found beyond the concert means above (85 to 105, mean 95 dB LAeq).

---

## 3. Automatic gain control theory and its failure modes

### Takeaway
A level controller has four parts:
- a **detector** (peak, RMS or percentile);
- a **static curve** (threshold, ratio, knee);
- **time constants** (attack, release, hold);
- a **topology** (feedforward or feedback).

Fast wideband gain control "breathes" and "pumps". Fast multi-band control flattens the spectrum. The proven fix for both is to let a slow loop set the overall level and to use a fast path only for sudden intense events, with gain increases rate-limited or frozen during pauses.

### Cited Findings
- **Design dimensions.** Giannoulis, Massberg and Reiss (2012) compare "RMS and peak-based approaches, feedforward and feedback designs, and linear and log domain level detection". They explain why the designs sound different and give "recommendations for high performance compressor design" (J. Audio Eng. Soc. 60(6) 399–408; abstract via [OpenAlex](https://api.openalex.org/works?search=Digital%20Dynamic%20Range%20Compressor%20Design) / [AES E-Library](https://www.aes.org/e-lib/browse.cfm?elib=16354)).
- **Definitions** ([Moore 2008, "The choice of compression speed in hearing aids", Trends in Amplification 12:103, PMC4111434](https://pmc.ncbi.nlm.nih.gov/articles/PMC4111434/)):
  - **Attack time** is how long the output takes to settle within 3 dB of its final value after a step increase in level.
  - **Release (recovery) time** is the time to come back within 4 dB after a step decrease.
- **Two classes of AGC** (same source):
  - "Automatic volume control" (AVC) has a slow release, "usually t_r is between 500 ms and 20 s". It is intended to relieve the user of adjusting the volume.
  - "Fast-acting" or "syllabic" compressors have "t_a is 0.5–20 ms and t_r is 5–200 ms".
- **Pumping and breathing.** "If the gain changes significantly during the speech itself, or during the pauses in the speech, then 'breathing' or 'pumping' noises may be heard ... To reduce this problem, both t_a and t_r should be long."
  - A short attack (1–10 ms) with a moderate release (300–2,000 ms) protects against transients. But the aid "effectively goes 'dead' for a while" after a loud transient.
  - "a recovery time of more than 1,000 ms may be needed" to avoid breathing.

  Source: Moore 2008.
- **Multi-band compression flattens the spectrum.** "In a multichannel hearing aid with fast-acting compression in many channels, the spectrum is flattened, reducing spectral contrasts ... short-term changes in the spectral pattern of sounds may be distorted because the pattern of gains across frequency changes rapidly with time" (Moore 2008). With few channels, "steady background noises may appear to be modulated by 'foreground' sounds" (same source).
  - Bor, Souza and Wright (2008, JSLHR) processed vowels through 1 to 16 compression channels. Spectral contrast fell significantly as channel count rose, for 6 of 8 vowels, and reduced contrast went with poorer vowel identification (search excerpt, [ASHA DOI 10.1044/1092-4388(2008/07-0009)](https://pubs.asha.org/doi/10.1044/1092-4388(2008/07-0009)); summary at [Canadian Audiologist, "Multi-channel compression"](https://canadianaudiologist.ca/multi-channel-compression-feature/)).
- **Gain rising in silence ("noise pumping").** A patent describes how "the increased gain of the AGC will result in noise pumping where the amplification of the noise is increased to an unacceptable level" during pauses (search excerpt, [US 5,329,243](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/5329243)).
- **Gating and freezing in broadcast processors** (search excerpts; full manuals blocked):
  - Omnia's Input AGC uses a "gate threshold" that slows the AGC release by a factor of 3, and a "freeze threshold" that stops it altogether. Range −90 to 0 dB ([Omnia 9 manual, ManualsLib](https://www.manualslib.com/manual/849874/Omnia-Omnia-9.html?page=49); [Omnia.11 manual p. 63](https://www.manualslib.com/manual/728731/Omnia-11.html?page=63)).
  - Orban's OPTIMOD-TV 8182A advises setting the GATE THRESHOLD "so that medium- to low-level passages cause the GATE lamp to flash on and off, thus slowing down the release time as the program gets softer". It offers a linear release or an exponential one that "automatically becomes faster as the release process proceeds" ([Orban 8182A manual p. 58](https://www.manualslib.com/manual/1199227/Orban-8182a.html?page=58)).
  - Telos Volt documents the gate as freezing the AGC in place, with a "return to zero" (RTZ) level control that sets where the gain drifts during gating ([Telos Alliance, "Adjusting the Volt's Wideband AGC Gating"](https://docs.telosalliance.com/docs/adjusting-the-volts-wideband-agc-gating)).
- **Asymmetric slew limits as an alternative to fixed time constants.** ADRO's maximum gain decrease is about 9 dB/s and its maximum increase about 3 dB/s. "This difference allows the gain to be decreased reasonably quickly ... but avoids increases in gain during brief pauses ... thus avoiding the 'pumping' noises" (Moore 2008).
- **Multi-stage chains and closed loops** (search excerpts; the cascaded-AGC literature is thin):
  - A DSP Concepts AGC example says that in a two-stage design "a loud low frequency signal (like a drum beat) can cause the entire signal to reduce in level" (pumping). It adds a separate fast limiter stage ([DSP Concepts AWE Designer AGC example](https://documentation.dspconcepts.com/awe-designer/8.2.D.4/automatic-gain-control-example)).
  - Closed-loop AGC trades "speed of response, overshoot, stability, and even possible oscillation" ([Analogic Tips AGC FAQ part 2](https://www.analogictips.com/the-why-where-and-how-of-automatic-gain-control-part-2-faq/)).
  - Long-time-constant AGC or squelch faults can cause low-frequency oscillation ("motorboating") ([Wikipedia, Motorboating](https://en.wikipedia.org/wiki/Motorboating_(electronics))).

### Inferences
- **The K1 chain cascades several level loops on the same signal:**
  1. a waveform normalised to its own recent peak;
  2. a four-band AGC;
  3. a "loud guard" keyed to the normalised peak.

  Each later stage sees a signal whose level the earlier stage has already removed. Two consequences follow:
  - The four-band AGC sees a peak-normalised signal, so it cannot react to true loudness changes, and compounds the spectral flattening Moore and Bor describe.
  - The loud guard triggers on "normalised peak often near 1". That condition is true **by construction** after peak normalisation, whatever the room level.

  This explains the bench symptom (34 % cut at living-room volume with no clipping) without needing any acoustic cause. This is my mechanism analysis of the brief's description; it has not been tested.
- **The noise gate can strand the gain.** A gate that freezes the gain keeps whatever gain the last loud passage set. Two outcomes follow:
  - If the room then plays quieter, the gain stays low until the gate opens again and release resumes.
  - If the gate threshold sits between breakdown and chorus levels, gain adapts only on loud passages.

  Broadcast processors handle this with a three-stage policy: release slows (gate), then stops (freeze), then optionally drifts toward a neutral "return to zero" gain. The RTZ drift is the fix for stranded gain.
- **Flattening matches the K1 symptom.** Per-band AGC with a fixed target (0.25) is, by definition, a per-band normaliser. In steady state each band's output level is independent of its input level, so "a loud chorus is no brighter than a quiet breakdown" is the designed steady-state behaviour of this stage, not a fault in its tuning.
- **Peak detection on bass-heavy music.** A wideband peak detector on club music is ruled by sub-bass. Any gain or guard keyed to that peak will pump on the kick drum. This is the DSP Concepts drum-beat case.

### Gaps
- I could not open Giannoulis et al. (2012). Its specific recommendations are **UNVERIFIED** in these notes. From memory, they are: feedforward topology, a smoothed decoupled peak detector in the log domain after the gain computer, and the fact that feedback designs cannot realise an infinite ratio. Look-ahead (delaying the audio so gain reductions can begin before the transient) is standard limiter practice, but I found no primary source for it in this session.
- No primary paper was found that quantifies limit cycles or hunting in cascaded audio AGC loops. Statements about cascade interaction above are reasoned from single-loop sources.
- No source uses the phrase "stuck gain after silence". The pathology is inferred from freeze-gate behaviour and the RTZ control.

---

## 4. Noise-floor estimation (minimum statistics, percentile trackers) under continuous music

### Takeaway
Minimum statistics assumes that each frequency band drops to the true noise floor at least once in a window of about 0.5 to 1.5 s. Continuous music breaks that assumption. The "noise" estimate then rides up to the quietest musical level in each band, so subtracting or normalising by it removes sustained musical content. The TensorFlow Lite Micro "noise reduction" stage is not a minimum tracker at all. It subtracts an exponential moving average of the signal itself.

### Cited Findings
- **Martin (2001):** R. Martin, "Noise Power Spectral Density Estimation Based on Optimal Smoothing and Minimum Statistics," IEEE Trans. Speech Audio Process. 9(5), 504–512, DOI 10.1109/89.928915 ([dblp](https://dblp.org/rec/journals/taslp/Martin01); [RWTH IKS listing](https://www.iks.rwth-aachen.de/publikationen/publications-detail//martin01c/)).
  - It needs no voice activity detector.
  - It tracks per-band minima of a smoothed power spectrum, with an optimal time-varying smoothing parameter.
  - Because the minimum is biased low, it multiplies by a bias-compensation factor.
- **Window and lag** ([Sundar Rangachari, MS thesis, UT Dallas (Loizou lab)](https://ecs.utdallas.edu/loizou/thesis/sundar_ms_thesis.pdf), §2.1):
  - The window must "bridge the broadest peak in any speech signal". Windows of "approximately 0.8–1.4 s gave good results".
  - With rising noise, "the minimum search lagged behind by 2L frames". Splitting the window into U sub-windows of V frames cuts the maximum delay to L + V frames.
  - Citing Cohen, "window lengths of 0.5–1.5 s were found to be optimum". A window that is too small "may result in overestimation of noise if the window length was less than the width of the speech peak itself". A very long window delays tracking of rising noise.
- **Window length controls bias both ways.** It biases the estimate upward during continuous speech and downward when noise rises. Doblinger's continuous minimum tracking lowers delay but ignores speech presence. Cohen's IMCRA gates the update on a speech-presence probability (search excerpts; [TU Delft, Erkelens 2008](https://sps.ewi.tudelft.nl/pubs/erkelens08tasl.pdf); [Sundar thesis](https://ecs.utdallas.edu/loizou/thesis/sundar_ms_thesis.pdf)).
- **TFLM micro frontend noise reduction**, for each channel and frame ([noise_reduction.c](https://github.com/tensorflow/tensorflow/blob/master/tensorflow/lite/experimental/microfrontend/lib/noise_reduction.c); [noise_reduction_util.c](https://github.com/tensorflow/tensorflow/blob/master/tensorflow/lite/experimental/microfrontend/lib/noise_reduction_util.c)):
  - `estimate = smoothing·signal + (1 − smoothing)·estimate`.
  - Output is `max(signal − estimate, min_signal_remaining·signal)`.
  - Defaults: `even_smoothing = 0.025`, `odd_smoothing = 0.06` (alternating channels), `min_signal_remaining = 0.05`, `smoothing_bits = 10`.

### Inferences
- **Continuous music** never lets a band fall to the acoustic noise floor within 1.5 s. A minimum-statistics floor then equals the music's own local minimum in that band. Sustained pads, bass lines and reverberant tails are classed as "noise". Normalising or gating against that floor removes them, leaving only onsets. That is useful for onset detection, but harmful as a loudness reference. The tracker also lags rising level by up to L + V frames (about 1 to 3 s).
- **TFLM defaults.** With the TFLM smoothing defaults and a 10 ms hop, the moving average has time constants of about 395 ms (s = 0.025) and 162 ms (s = 0.06). After about half a second of music the "noise" estimate is the music's own running mean, and the output is only the excess above that mean (floored at 5 % of the input).
- **Where a noise-floor estimate is valid on the K1.** Microphone self-noise is fixed by the datasheet (about 25 to 29 dB(A) SPL). Below that, the K1 needs no adaptive estimator to know where the microphone floor is. The "noise" worth tracking is room noise (HVAC, chatter). It is meaningful only during real musical silence, which the rest of the system already has to detect.

### Gaps
- No source measured minimum-statistics or percentile-tracker bias on real music (as opposed to continuous speech). The music-specific behaviour above is inferred.
- Martin's own full text was not accessible. Parameter values above come from a thesis that summarises Martin.

---

## 5. Proven architectures that preserve dynamics

### Takeaway
Three fields reach the same answer:
- **Hearing aids:** a slow loop sets overall level (seconds), and a fast loop acts only on sudden large excesses (more than about 8 dB above the running level).
- **Broadcast:** gated slow input AGC, then compression, then a peak limiter.
- **Loudness normalisation** (EBU R128): one static gain per programme, chosen so the loudness range inside the programme is untouched.

### Cited Findings
- **Dual front-end AGC** (Moore and Glasberg 1988, Br. J. Audiol. 22:93–104; Moore, Glasberg and Stone 1991; Stone, Moore, Alcántara and Glasberg 1999), as described by Moore 2008 ([PMC4111434](https://pmc.ncbi.nlm.nih.gov/articles/PMC4111434/)):
  - Two control signals: "one with long attack and recovery times and the other with shorter attack and recovery times".
  - "Normally, the operation of the system is determined by the slow-acting control signal."
  - The digital version has a "hold-off time" during which the gain "does not change at all when the input level drops". The source prints this as "500–500 ms", apparently a typo.
  - "If there is a sudden increase in sound level, so that the momentary output level increases by more than 8 dB above the 'running' level determined by the slow system, then the fast-acting control signal rapidly reduces the gain ... If the increase in sound level is brief, the gain returns to the original value determined by the overall level."
- **Moore and Glasberg 1988:** the slow control voltage had a 5 s recovery time and held the average speech level at the output constant (search excerpt of the abstract, [informahealthcare DOI 10.3109/03005368809077803](https://informahealthcare.com/doi/abs/10.3109/03005368809077803)).
- **Advantages of slow systems** such as dual front-end and ADRO (Moore 2008): "The temporal envelope of the speech is hardly distorted; envelope fluctuations at syllabic rates are preserved."
- **Stone et al. 1999** compared four schemes in wearable digital aids ([JASA 106:3603, DOI 10.1121/1.428213](https://doi.org/10.1121/1.428213)):
  - DUAL-HI: slow dual front-end, threshold 63 dB SPL, ratio 30.
  - DUAL-LO: threshold 55 dB SPL, ratio 3, "intended to give some impression of the levels of sounds in the environment".
  - FULL-4: fast four-channel full-dynamic-range compression.
  - DUAL-4: a combination of the two.

  APHAB questionnaire scores showed "no clear differences between the four systems".
- **Gatehouse et al. results** (summarised by Moore 2008): slow compression "generally leads to higher listening comfort than fast compression". The benefit of fast compression varies by individual.
- **Fast versus slow in a speech study.** Fast-acting (10 ms / 100 ms) and slow-acting (50 ms / 3,000 ms) compression, at several channel counts, had no significant effect on speech recognition (search excerpt, [University of Manchester research portal](https://research.manchester.ac.uk/en/publications/effect-of-the-number-of-amplitude-compression-channels-and-compre/)).
- **Broadcast input AGC** with gate and freeze thresholds, release shapes and RTZ: see Section 3 citations (Omnia, Orban 8182A, Telos Volt).
- **EBU R128-2023** ([EBU R 128 PDF](https://tech.ebu.ch/docs/r/r128.pdf)):
  - It notes that "peak normalisation of audio signals has led to considerable loudness differences between programmes".
  - Programme loudness is normalised to **−23.0 LUFS**, with ±1.0 LU tolerance where the target is not practically achievable (for example live programmes).
  - Maximum true peak is −1 dBTP.
  - Loudness Range (EBU Tech 3342) "may be used to evaluate the loudness variation of a programme ... and the dynamic integrity of a distribution path".
  - Loudness is measured with level gating (EBU Tech 3341).

### Inferences
- **Slow-loop time constant.** The level a music-to-light front end should follow is the room's programme level. In AVC terms that means seconds to tens of seconds (Moore: 0.5 to 20 s; dual front-end: 5 s recovery plus hold-off).
- **What a slow loop keeps.** Verse-versus-chorus differences of a few dB over 10 to 30 s survive a slow loop. They do not survive a fast per-band normaliser.
- **Fast protection path.** A fast path is needed only for genuine excess (more than about 8 dB over the running level), and should release back to the slow loop's gain.
- **R128 as the cleanest dynamics-preserving model.** Measure, apply one gain, do nothing else. A live device cannot know the "programme" in advance, so the practical equivalent is a very slow, gated loudness estimate driving one wideband gain or offset. In a calibrated system the "gain" can be an offset in the dB domain rather than a sample multiply.

### Gaps
- No Orban white paper on OPTIMOD gain riding with stated time constants was retrieved. The usual broadcast chain order (slow AGC, then multiband compressor, then limiter) and "tens of seconds" AGC time constants are **UNVERIFIED** here beyond the Omnia, Orban 8182A and Telos manual excerpts.
- No ReplayGain specification was retrievable (hydrogenaud.io blocked access). ReplayGain's details (per-track or per-album single gain, 89 dB SPL reference) are **UNVERIFIED**.

---

## 6. On-device machine-listening front ends (TFLM micro frontend, PCAN, PCEN)

### Takeaway
PCEN and its fixed-point TFLM version (PCAN) divide each channel by a smoothed copy of itself raised to α ≈ 0.95–0.98. That deliberately removes almost all loudness information (a 40 dB level change becomes about 0.8 dB at α = 0.98) and suppresses stationary energy. This is ideal for keyword spotting and the opposite of what a light show needs for "loud chorus brighter than quiet breakdown". It is cheap on a microcontroller: a lookup table, a 64-bit multiply and a shift per channel per frame.

### Cited Findings
- **PCEN** ([Wang et al. 2017, "Trainable frontend for robust and far-field keyword spotting", arXiv:1607.05666](https://arxiv.org/abs/1607.05666)):
  - Formula: PCEN = (E/(ε + M)^α + δ)^r − δ^r, with M(t) = (1 − s)·M(t−1) + s·E(t).
  - Defaults s = 0.025, α = 0.98, δ = 2, r = 0.5. "s = 0.025 translates to a 40-frame time constant", with a 10 ms frame shift and 25 ms window.
  - Described as "an automatic gain control based dynamic compression" that "emphasizes changes relative to recent spectral history and adapts to channel effects including loudness".
- **Lostanlen et al. (2019)** ([IEEE Signal Processing Letters, DOI 10.1109/LSP.2018.2878620](https://doi.org/10.1109/lsp.2018.2878620); [author PDF](https://www.justinsalamon.com/uploads/4/3/9/4/4394963/lostanlen_pcen_spl2018.pdf)):
  - PCEN "enhances transient events ... while discarding stationary noise ... as well as slow changes in loudness" (Fig. 1 caption).
  - It "Gaussianizes distributions of magnitudes while decorrelating frequency bands".
  - The time constant T is "the transition threshold between a stationary regime" and a transient one.
  - librosa defaults: T = 400 ms (s ≈ 0.025 at a 23 ms hop), ε = 10⁻⁶, α = 0.98, δ = 2, r = 1/2. The authors used T = 60 ms for bird detection.
  - PCEN is "a computationally efficient frontend".
- **TFLM PCAN gain control** ([pcan_gain_control.c](https://github.com/tensorflow/tensorflow/blob/master/tensorflow/lite/experimental/microfrontend/lib/pcan_gain_control.c); [pcan_gain_control_util.c](https://github.com/tensorflow/tensorflow/blob/master/tensorflow/lite/experimental/microfrontend/lib/pcan_gain_control_util.c)):
  - Per channel: `gain = WideDynamicFunction(noise_estimate, lut)`, `snr = (signal·gain) >> snr_shift`, `signal = PcanShrink(snr)`.
  - The gain table approximates 2^gain_bits · (x + offset)^(−strength). Defaults: strength 0.95, offset 80.0, gain_bits 21.
  - The table is built once at start-up with `powf`, as a piecewise-quadratic segment per power of two. At run time the work is integer only.
  - `PcanShrink` squares small values and is linear-minus-offset for large ones. It is a fixed-point stand-in for the root compression.
  - PCAN is **off by default** (`enable_pcan = 0`).
  - The noise estimate PCAN divides by is the noise-reduction stage's moving average ([frontend_util.c](https://github.com/tensorflow/tensorflow/blob/master/tensorflow/lite/experimental/microfrontend/lib/frontend_util.c)).
- **TFLM noise reduction:** see Section 4. A moving average with s = 0.025 or 0.06, subtracted, and floored at 5 %.

### Inferences
- **Loudness removal, worked through.** When M ≫ ε, scaling the input by C scales the AGC output by C^(1−α). At α = 0.98, a 40 dB change (C = 100) becomes 100^0.02 ≈ 1.096, or **0.8 dB**. At the TFLM strength of 0.95 it becomes 2 dB. A PCEN- or PCAN-style front end therefore erases the very quantity a light show needs to show loudness, and with T = 400 ms it does so within about one bar of music.
- **What the K1's four-band AGC resembles.** Its fixed target of 0.25, applied per band, is in effect a crude α = 1 version of PCEN with few bands. The flattening seen on the bench is what this family is designed to do.
- **Cost on the ESP32-S3.** PCAN-style processing for 80 bins at 133 frames per second is about 10,600 lookup-multiply-shift operations per second. That is negligible on an ESP32-S3. Cost is not a reason to choose or avoid it; behaviour is.
- **Where PCEN does fit.** It is a good **onset or novelty detector** input (transients enhanced, stationary energy removed) running *alongside* a calibrated loudness path, not in place of one.

### Gaps
- TFLM default framing (window and hop) and filterbank channel count were not fetched from `window_util.c` or `filterbank_util.c`. The 25 ms / 10 ms framing comes from the PCEN paper's keyword-spotting set-up. The TFLM defaults themselves are **UNVERIFIED**.
- No published ESP32 benchmark of the TFLM micro frontend was retrieved.

---

## 7. Cross-domain analogue: camera auto-exposure and tone mapping

### Takeaway
- **Exposure.** Camera auto-exposure measures a weighted average (the scene "key"), moves exposure over several frames toward a target with a deadband to avoid oscillation, and offers **exposure compensation** as the user's control and **AE lock** as a freeze.
- **Tone mapping.** A *global* tone curve keeps the order of brightness levels and has no halos. *Local* operators gain local contrast but create halos at strong edges. That is the image counterpart of per-band AGC pumping and spectral flattening.

### Cited Findings
- **Android Camera2** ([CaptureResult reference](https://developer.android.com/reference/android/hardware/camera2/CaptureResult#CONTROL_AE_STATE)):
  - AE states include SEARCHING, CONVERGED, LOCKED and FLASH_REQUIRED.
  - `CONTROL_AE_LOCK`: when true, "the AE algorithm is locked to its latest parameters, and will not change exposure settings until the lock is set to false".
  - `CONTROL_AE_EXPOSURE_COMPENSATION` is an "Adjustment to auto-exposure (AE) target image brightness" in EV steps (for example 0.333 EV per step; "One EV represents a doubling of image brightness"). It applies "even when ... aeLock == true". After a change, "camera device may take several frames to reach the newly requested exposure target", during which the state is SEARCHING.
  - `CONTROL_AE_REGIONS` carry metering weights from 0 to 1,000 per area. With all weights zero, the camera returns to default metering.
- **Patent literature on AE loops** (design claims, not benchmarks; search excerpts):
  - Convergence speed "should be fast but limited to avoid unwanted video oscillations". "As the stability region grows, convergence can be made faster."
  - Chipsets "commonly adjust exposure after two or three frames, allowing the prior setting time to take effect".
  - Some designs use centre-weighted metering and lower the AE target to limit highlight over-exposure.
  - "A sequence of strong flashlight bursts may be enough to render a surveillance camera inoperable for a significant stretch of time."

  Sources: [US 8,325,890](https://patents.google.com/patent/US8325890); [USPTO 11653100](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11653100); [USPTO 10757342](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10757342).
- **Reinhard et al. 2002, "Photographic Tone Reproduction for Digital Images"** ([Utah tech report UUCS-02-001](https://www.cs.utah.edu/docs/techreports/2002/pdf/UUCS-02-001.pdf)):
  - The scene key is the **log-average luminance**, L̄w = exp(mean(log(δ + Lw))). It is mapped to middle grey a = 0.18, the "key value", which the user can vary (0.045, 0.09, 0.36, 0.72).
  - The global operator is L/(1 + L), followed by optional automatic dodging-and-burning (local).
  - The paper notes that other local methods leave halo-like artefacts (paraphrased).
- **Global versus local tone mapping:**
  - Global operators are faster and produce fewer artefacts, but local operators keep local contrast better (paraphrased).
  - Local tone mappings no longer guarantee the global order of luminance, so ways of avoiding halo artefacts have to be designed in explicitly (paraphrased).

  Sources (search excerpts): [arXiv 1808.09411](https://arxiv.org/pdf/1808.09411v1.pdf); [Springer, Optical Review 2020](https://link.springer.com/article/10.1007/s10043-020-00604-w).

### Inferences
These are the analogue mappings, all my inference:

| Camera concept | Audio-to-light equivalent |
|---|---|
| Log-average luminance (key) | A slow, gated, log-domain loudness estimate (dB SPL Leq over seconds) |
| Middle grey (0.18) | A target LED brightness for "typical loudness in this room" |
| Exposure compensation | A user "sensitivity" offset in dB on that target, still applied while auto is locked |
| AE lock / CONVERGED | Freeze the slow loop during silence or once settled |
| Deadband or stability region | Do not move gain for small loudness deviations, so musical swings within ±x dB stay visible as brightness swings |

- **Global versus local, applied to audio.** A *global* tone curve (one wideband dB-to-brightness map, the same for all bands) keeps "chorus brighter than breakdown" and "bass louder than treble" orderings. *Local* or per-band normalisation is the audio counterpart of local tone mapping. It boosts local contrast, but breaks the global order: a quiet band can end up brighter than a loud one, and an image halo has its audio counterpart in pumping around strong events.
- **Convergence time.** Cameras converge in a few frames because the light *changes scene*. A music front end's "scene" (room and system gain) changes rarely, so its auto-exposure equivalent can be far slower (seconds to tens of seconds) than camera AE.

### Gaps
- No peer-reviewed survey with numeric AE convergence times (for example in milliseconds or frames for phone cameras) was retrieved. The figures above are patent claims.

---

## 8. Mapping a calibrated signal into a fixed-range display: options and trade-offs

### Takeaway
Because the IM69D130 has a fixed, calibrated sensitivity (±1 dB), every bin's magnitude converts directly to an absolute dB SPL. The options for mapping those levels to brightness, from most to least dynamics-preserving, are:
1. a fixed logarithmic scale;
2. a fixed scale plus a user offset;
3. a slow auto-ranging window (floor and ceiling tracked over tens of seconds);
4. per-band normalisation.

Each step adds adaptivity and removes some absolute level information.

### Cited Findings
- **Absolute calibration** is supported by the datasheet's ±1 dB sensitivity tolerance and the same sensitivity in every power mode ([IM69D130 datasheet](https://www.infineon.cn/content/dam/infineon/row/public/documents/24/49/infineon-im69d130-datasheet-en.pdf), Table 1).
- **Fixed absolute targets.** Broadcast normalises to a fixed absolute target (−23 LUFS) and judges dynamics by Loudness Range ([EBU R 128](https://tech.ebu.ch/docs/r/r128.pdf)).
- **Slow AVC** relieves the user of volume adjustment while preserving syllabic-rate envelope fluctuations ([Moore 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC4111434/)).
- **Stone et al. 1999's DUAL-LO** setting (ratio 3) was explicitly designed to "give some impression of the levels of sounds in the environment". That is a partial-compression middle ground between fixed and fully normalised ([DOI 10.1121/1.428213](https://doi.org/10.1121/1.428213)).
- **Per-band normalisation flattens spectral contrast**, the more so as channel count rises ([Moore 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC4111434/); Bor et al. 2008, search excerpt via [ASHA](https://pubs.asha.org/doi/10.1044/1092-4388(2008/07-0009))). PCEN-type normalisation discards slow loudness changes ([Lostanlen et al. 2019](https://doi.org/10.1109/lsp.2018.2878620)).
- **Key-based exposure.** A log-average "key" mapped to a target with a user-set key value is the photographic counterpart of slow auto-ranging plus offset ([Reinhard et al. 2002](https://www.cs.utah.edu/docs/techreports/2002/pdf/UUCS-02-001.pdf)). Android exposes exposure compensation as the user control on top of auto-exposure ([Android Camera2](https://developer.android.com/reference/android/hardware/camera2/CaptureResult#CONTROL_AE_EXPOSURE_COMPENSATION)).

### Inferences
The trade-offs below are my synthesis of the sources above.

1. **Fixed logarithmic scale** (for example 50 to 110 dB SPL maps to 0 to 100 % brightness).
   - Pros: no adaptation, so no pumping, no hunting and no stuck gain. Loudness and spectral contrast are perfectly preserved. Deterministic and testable.
   - Cons: a 60 dB room-level span (Section 2) compressed into one fixed range leaves quiet rooms dim and loud rooms saturated.
2. **Fixed scale plus user offset** (the exposure-compensation model).
   - Pros: everything in option 1, plus a one-time placement adjustment.
   - Cons: needs a user action when the room level changes a lot (party versus background music).
3. **Slow auto-ranging window.** Floor and ceiling track a gated loudness percentile over 10 to 60 s, with asymmetric slew (fast down, slow up, ADRO-style), freeze in silence and drift back to a neutral offset.
   - Pros: adapts to the room. Keeps verse/chorus and spectral contrast at time-scales shorter than the window. One wideband offset keeps the spectral order.
   - Cons: after a level change the display is wrong for seconds (camera "SEARCHING"). Sustained loud sections slowly lose some brightness advantage, so the window length decides how much "song-scale" dynamics survive. Needs a fast protection path for sudden excess (dual front-end idea).
4. **Per-band normalisation** (per-band AGC, PCEN).
   - Pros: every band always uses the full display range. Good for onset or novelty visuals.
   - Cons: removes loudness and spectral contrast by design. Pumps around strong events. Interacts badly when cascaded with other level loops. This is the K1's current behaviour.

A hybrid is common across the cited fields: a slow wideband loop sets the range, and per-band or novelty features (PCEN-like) are added as *separate* visual parameters rather than as the brightness reference.

### Gaps
- No published study of sound-to-light or music-visualiser level mapping (as opposed to hearing aids, broadcast or imaging) was found in this session. The trade-offs above transfer from those adjacent fields and are not measured on light shows.

---

## Design implications for an embedded sound-to-light front end

Each item is drawn from the cited findings above. Items marked (inference) are my reasoning.

1. **No front-end gain is needed for resolution or protection.**
   - The IM69D130 is linear (under 1 % THD) to 128 dB SPL, about 22 dB above the loudest measured club average (106 dB LAeq).
   - Its noise floor (25 to 29 dB(A) SPL) sits roughly at the 16-bit floor (about 32 dB SPL).
   - The x21.6 pre-clamp multiply adds no information and causes the only clipping in the chain, from about 83 to 93 dB SPL RMS music (inference from datasheet numbers).
   - Remove the multiply. Or apply it only after widening to 32-bit or float, with no 16-bit clamp.
2. **Treat the microphone as calibrated.** Convert to absolute dB SPL using −36 dBFS = 94 dB SPL (±1 dB). The ESP32-S3 PDM2PCM unity-gain assumption must be checked once, with a 94 dB SPL calibrator or a reference meter, before relying on absolute values (Gap, Section 1).
3. **The clock mode is a noise choice, not a level choice.** At 12.8 kHz, `DSR_8S` puts the microphone in its 768 kHz-class mode (SNR 64 dB(A)). `DSR_16S` gives the 1.536 MHz-class mode (66 dB(A), twice the current). Sensitivity and AOP do not change.
4. **Do DC and sub-sonic removal in software.** The ESP32-S3 driver exposes no hardware high-pass filter, which is an ESP32-P4 feature. Rumble below the microphone's 28 Hz roll-off would otherwise dominate any wideband peak or RMS detector, and bass-heavy music already dominates such detectors.
5. **Use at most one adaptive level loop, and make it slow, gated and wideband.**
   - Follow the hearing-aid and broadcast pattern: release or recovery in seconds to tens of seconds; gain increases rate-limited (ADRO's 3 dB/s up versus 9 dB/s down is a concrete precedent); hold or freeze during silence; slow return to a neutral offset so the gain cannot strand.
   - Cascading a self-peak normaliser, a per-band AGC and a peak-keyed guard is the configuration the sources warn against. The guard keyed to a normalised peak triggers by construction (inference).
6. **Never use per-band normalisation as the brightness reference.**
   - Fast multi-channel compression flattens spectral contrast (Moore 2008; Bor et al. 2008). PCEN or PCAN with α ≈ 0.95–0.98 reduces a 40 dB loudness change to 0.8 to 2 dB.
   - Use one global dB-to-brightness curve, the tone-mapping lesson, so that loud stays brighter than quiet and the spectral order is kept.
7. **Keep a fast path only for real excess, and only as protection.**
   - Dual front-end rule: act only when the momentary level exceeds the slow running level by more than about 8 dB, then return to the slow loop's gain.
   - On a light instrument that "protection" is optional (no hearing risk). It mainly guards visual saturation, so a soft-knee ceiling in the brightness map may replace it (inference).
8. **Give the user an exposure-compensation-style control.** A single "sensitivity" offset in dB on the target brightness, applied even while the auto loop is frozen (Android Camera2 model). Within ±x dB of the target the loop should not move (a deadband), so musical swings show as brightness swings.
9. **Use noise-floor estimators only for what they are good at.** Minimum statistics and moving-average subtraction misclassify sustained music as noise (0.5 to 1.5 s windows, 2L lag). Use them, or PCEN, to derive *onset or novelty* features in parallel. Do not use them to normalise loudness. The microphone floor itself is a datasheet constant.
10. **Cost is not a constraint.** Fixed-point PCAN-style per-bin gain for 80 bins at 133 Hz is about 10^4 simple operations per second (inference). Any of the four mapping options fits on an ESP32-S3. The choice should be made on behaviour (Section 8), not compute.
11. **Validation targets that follow from the sources:**
    - A 6 dB step in room level (verse to chorus) must produce a visible, lasting brightness change for at least the slow-loop time constant.
    - A spectral-tilt change (bass-heavy versus bright) must survive in the colour or band mapping.
    - No gain change may occur during a 2 s musical silence (hold or freeze).
    - No clipping may occur at 115 dB SPL peak input, which is −15 dBFS on this microphone.
