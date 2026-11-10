# Hearing and loudness science for the K1 audio front end

Scope: external literature only. Covers what the ear does about level, how loudness and brightness are scaled, what engineered auditory front ends do, and which time scales of level change listeners hear versus adapt away. Compiled 10 November 2026. Anything not confirmed against a primary or standards source is marked UNVERIFIED. Numbers I derived by arithmetic from cited values are marked "(derived)".

---

## 1. Cochlea: compression, outer hair cells, efferent reflex, middle-ear reflex. Is "AGC" the right description?

### Takeaway
The cochlea applies a near-instantaneous, frequency-specific compressive nonlinearity: about 0.2–0.3 dB of output per dB of input near the characteristic frequency (CF), over roughly 40–90 dB SPL, at the base of the cochlea. It squeezes about 120 dB of input into 30–40 dB of mechanical vibration. This is a static compressive curve (outer hair cell feedback), not a time-averaged gain control, so level differences are compressed but never removed. The only true slow feedback gain controls are the medial olivocochlear (MOC) reflex, with onset about 25 ms and time constants of roughly 70 ms to 25 s, and the middle-ear (stapedius) reflex, which acts only above about 70–100 dB SPL and mainly at low frequencies. Both are partial (about 10–30 dB at most), not normalising.

### Cited Findings
- Basal basilar-membrane (BM) responses to CF tones are highly compressive. In chinchilla at a 10 kHz site, response magnitude grew by only 28 dB for a 96 dB increase in stimulus level. Average growth was as low as 0.2 dB/dB at CF, measured between 40 and 90 dB SPL, and lower just above CF. — [Robles & Ruggero 2001, Physiol Rev 81:1305, §II.A.1](https://pmc.ncbi.nlm.nih.gov/articles/PMC3590856)
- Conclusion of the same review: basal BM input/output functions are "highly compressive (0.2–0.3 dB/dB) at frequencies around CF", which "allows the cochlea to translate the enormous range (120 dB) of auditory stimuli into a range of vibrations (30–40 dB) suitable for transduction by the inner hair cells." — [Robles & Ruggero 2001, §XI](https://pmc.ncbi.nlm.nih.gov/articles/PMC3590856)
- At the base, compression is confined to near CF. Vibrations grow linearly (1 dB/dB) at frequencies below about 0.7 CF. — [Robles & Ruggero 2001, §IV.B](https://pmc.ncbi.nlm.nih.gov/articles/PMC3590856)
- At apical (low-frequency) sites the nonlinearity is not well established. Some studies report linear responses, some weak compression, and one a weak expansive nonlinearity. Apical tuning is broader: Q10 is 1.6 at a basal site versus 0.9 at an apical site in chinchilla. — [Robles & Ruggero 2001, §IV.B](https://pmc.ncbi.nlm.nih.gov/articles/PMC3590856)
- The compression comes from outer-hair-cell mechanoelectrical transduction. The hair-cell receptor-potential versus displacement curve is compressive and saturating (a second-order Boltzmann). Through electromechanical feedback onto the BM, it produces the compressive growth at CF, two-tone suppression and intermodulation distortion. Because it acts on the receptor potential cycle by cycle, it is an instantaneous nonlinearity, not a time-averaged gain. — [Robles & Ruggero 2001, §IX.E](https://pmc.ncbi.nlm.nih.gov/articles/PMC3590856)
- Efferent (MOC) activation, by electrical stimulation in animals, causes a CF-specific loss of sensitivity and linearisation of BM vibration. It shifts the steep part of the velocity–intensity curve up by as much as 30 dB. Attenuation is largest at 50–75 dB SPL and may exceed 10 dB even at 90 dB SPL. — [Robles & Ruggero 2001, §IX.C](https://pmc.ncbi.nlm.nih.gov/articles/PMC3590856)
- Human MOC reflex time course, measured with stimulus-frequency otoacoustic emission suppression in 9 ears: onset and offset delays about 25 ms. It builds up like a saturating exponential with τ = 277 ± 62 ms and decays with τ = 159 ± 54 ms. In the best-SNR ears the onset split into fast (~70 ms), medium (~330 ms) and slow (~25 s) components, and the decay showed an under-damped overshoot. — [Backus & Guinan 2006, J Acoust Soc Am 119:2889](https://doi.org/10.1121/1.2169918) (values as reported in the abstract and secondary summaries)
- MOC build-up estimates depend on the analysis window: 70–90 ms with a 40 ms window versus 23–39 ms with a 20 ms window. — [Frontiers in Neuroscience 2021 review](https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2021.746821/full)
- Middle-ear acoustic reflex, in humans the stapedius only. It mainly attenuates low frequencies. When triggered 20 dB above reflex threshold it cuts transmission to the cochlea by about 15 dB. Vocalisation-induced reflex gives about 20 dB. Contraction latency is about 10 ms, but maximum tension may take 100 ms or more. Other reports give about 150 ms latency at threshold and 25–35 ms at high SPL. Because of this latency it cannot protect against sudden intense sounds. — [Wikipedia: Acoustic reflex, citing primary sources](https://en.wikipedia.org/wiki/Acoustic_reflex) (secondary source)
- Normal acoustic-reflex thresholds are commonly cited as about 70–100 dB SPL. Reflex latency depends on frequency, intensity and the eliciting stimulus's rise and fall time. — [Grason-Stadler clinical guide](https://www.grason-stadler.com/guides/acoustic-reflexes) (secondary; threshold figure from the search summary, not re-read in full)
- Bilateral acoustic reflexes are present in 85.3% of people aged 18–30 (N = 3,280) and in 74.6% of all persons (N = 15,106). — [Wikipedia: Acoustic reflex, citing Flamme et al. NHANES](https://en.wikipedia.org/wiki/Acoustic_reflex)

### Inferences
- "Automatic gain control" fits the MOC and stapedius reflexes, which are slow feedback loops with time constants. It does not fit the main cochlear compression, which is a memoryless compressive curve. What the cochlea discards is level resolution at high levels (0.2–0.3 dB/dB near CF), not level differences. A +10 dB chorus still produces about +2 to +3 dB more BM vibration at CF (derived: 10 × 0.2–0.3), and up to +10 dB for components below 0.7 CF.
- What the periphery preserves: the sign and order of level changes across time, cross-frequency level differences (compression is per place), and onsets, because the compressive curve is instantaneous and the slow reflexes have about 25 ms delay and 70–330 ms build-up.
- The MOC and stapedius loops provide at most about 10–30 dB of attenuation, and only at moderate-to-high levels (stapedius above about 70–100 dB SPL). They are protective or anti-masking range shifts, not normalisation to a reference level.
- Most of the K1's 12.8 kHz-sampled band (below 6.4 kHz) maps to the mid and apical cochlea, where compression is weaker or uncertain (from Robles §IV.B). Basal 0.2 dB/dB figures should not be applied uniformly to low-frequency bins.

### Gaps
- Magnitude of the human MOC effect in dB of equivalent attenuation (as opposed to OAE suppression) was not retrieved. UNVERIFIED.
- Primary measurements of acoustic-reflex threshold and attenuation by frequency were not read. The values above are from secondary sources.

---

## 2. Neural adaptation: onset emphasis and adaptation to the mean level. Is absolute level perceived?

### Takeaway
Auditory-nerve fibres show rapid (about 1–10 ms) and short-term (about 10–100 ms, typically quoted near 60 ms) adaptation, which emphasises onsets. On top of that, both the auditory nerve and midbrain shift their level-coding range towards the most common recent level. In the auditory nerve the shift is only 0.05–0.47 dB per dB of mean-level change (mean 0.25–0.34). It develops over about 100–400 ms. In the inferior colliculus it takes about 160 ms after an increase and about 330 ms after a decrease, plus a slow component of tens of seconds. The system therefore partly, not fully, discounts a sustained level change, and acts as a high-pass filter on level. Behaviourally, listeners discriminate about 1 dB across a 100–120 dB range but can identify absolute level in only about 7 categories, saturating at about a 20 dB range. Relative level is coded very well; absolute level is coded coarsely but not discarded.

### Cited Findings
- The "dynamic range problem": listeners respond behaviourally over 100–120 dB SPL and discriminate level differences of about 1 dB across almost the whole range. Yet most auditory-nerve fibres change firing rate over only 20–40 dB and saturate well below the top of the behavioural range. — [Wen, Wang, Dean & Delgutte 2009, J Neurosci 29(44), Introduction](https://pmc.ncbi.nlm.nih.gov/articles/PMC2774902)
- In cat auditory nerve, the level range over which firing rate grows steeply shifts toward the most probable levels of a dynamic stimulus. — [Wen et al. 2009](https://pmc.ncbi.nlm.nih.gov/articles/PMC2774902)
  - Stimulus: level redrawn every 50 ms from a distribution with a high-probability region (HPR).
  - Size of the shift: the L50 midpoint moved 0.16–0.47 dB/dB for CF tones (mean 0.34) and 0.05–0.39 dB/dB for broadband noise (mean 0.25).
  - No auditory-nerve fibre came close to the 1 dB/dB slope that would keep the fibre's dynamic range aligned with the HPR (paraphrase of the authors' statement).
  - The shift was larger when the HPR was higher above threshold.
- Correction: the broadband-noise SPLs in Wen et al. 2009 were misreported because of a programming error. The authors state the adaptation-shift measures are unaffected. — [Wen et al. 2012 erratum, via search summary](https://dspace.mit.edu/handle/1721.1/55979)
- In a follow-up "dual adaptation" model, dynamic-range adaptation in the auditory nerve occurs as rapidly as firing-rate adaptation, over 100–400 ms, and the two time constants are correlated. — [Wen, Wang & Delgutte 2012, J Neurophysiol 108:69](https://doi.org/10.1152/jn.00055.2012) (via abstract summary)
- In guinea-pig inferior colliculus, the population's level coding adapts to the stimulus level statistics, becoming most accurate near the most common levels. — [Dean, Harper & McAlpine 2005, Nat Neurosci, doi:10.1038/nn1541](https://www.nature.com/articles/nn1541)
- Inferior colliculus time course (Dean, Robinson, Harper & McAlpine 2008, J Neurosci 28:6430). — [Dean et al. 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC6670892)
  - Stimulus: level reset every 50 ms. The HPR was 51 ± 6 or 75 ± 6 dB SPL (80% of draws), and the two distributions alternated every 5 s.
  - Adaptation to an increase in mean level: average time constant 160 ms.
  - Adaptation to a decrease: median 331.8 ms. Adaptation to an increase is faster than to a decrease.
  - Some neurons also showed a slow adaptation over tens of seconds.
  - The time course was independent of how fast levels varied, but related to the neuron's CF.
- Dean et al. 2008 interpret adaptation as subtracting an exponentially weighted average of recent level. This "renders neural output into a high-pass-filtered version of the stimulus": responses do not follow slow level variations. Faster adaptation (e.g. τ = 15 ms) raises the corner frequency. Their environmental recordings showed level varying over 90 dB, with changes lasting from tens of milliseconds to several seconds. — [Dean et al. 2008, Discussion, Fig. 7](https://pmc.ncbi.nlm.nih.gov/articles/PMC6670892)
- A later study reports a median firing-rate time constant of about 160 ms (IQR 74–204 ms) after a quiet-to-loud switch. — [Robinson, Harper & McAlpine 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5123015) (via search summary)
- Auditory-nerve rapid and short-term adaptation (Westerman & Smith 1984, Hear Res 15:249). — [doi:10.1016/0378-5955(84)90032-7](https://doi.org/10.1016/0378-5955(84)90032-7); values as reported by later papers citing it, e.g. [Zhang & Carney 2005](https://urmcpublic-lb1.urmc.rochester.edu/MediaLibraries/URMCMedia/labs/carney-lab/documents/articles/ZhangCarney-JASA-2005.pdf)
  - Time constants are quoted as "on the order of 5–10 ms and 60 ms", with recovery about 40 ms. Other papers give the classes as rapid τ ≈ 1–10 ms and short-term τ ≈ 10–100 ms.
  - Zhang & Carney 2005 model this as a double exponential with rapid and short-term components.
  - The original 1984 fitted values were not checked: UNVERIFIED.
- In classic short-term adaptation, firing rate drops without a change in sensitivity or dynamic range. This is why dynamic-range adaptation was reported as a distinct phenomenon. — [Wen et al. 2009, Introduction](https://pmc.ncbi.nlm.nih.gov/articles/PMC2774902)
- Absolute identification of loudness: with about 7 or more signals over a range of about 20 dB or more, the information transmitted "is not much increased by increasing either variable" (Miller 1956; Braida & Durlach 1972). Luce et al. propose a roving "attention band" about 10–15 dB wide. — [Luce, Green & Weber 1976, Percept Psychophys 20:49](https://link.springer.com/article/10.3758/BF03198705)

### Inferences
- The auditory system cancels only about a quarter to a third of a sustained change in mean level at the auditory nerve (0.25–0.34 dB/dB). A +12 dB room-volume step would still leave about +8 to +9 dB of the step in the AN code after adaptation (derived: 12 × (1 − 0.25–0.34)). A front end that normalises to 1 dB/dB (full normalisation) removes more level information than the auditory periphery does.
- Adaptation is asymmetric (faster for increases) and runs on several time scales at once (about 5–10 ms, about 60 ms, about 160–330 ms, and tens of seconds). No single time constant describes it.
- Absolute level is perceived, but coarsely (about 7 categories, i.e. 2–3 bits). Relative level within a recent window is resolved to about 1 dB. A display matching perception should keep relative contrast within roughly the last few seconds accurate, and may treat absolute level as a coarse cue.

### Gaps
- Inferior-colliculus shift slope in dB/dB (Dean et al. 2005) was not retrieved, so I cannot say whether the midbrain normalises more fully than the auditory nerve. UNVERIFIED.
- Whether these neural adaptations reduce perceived loudness of continuous music (perstimulatory loudness adaptation) was not researched within budget. See Gaps in section 6.

---

## 3. Loudness scaling (sones, phons, Stevens' law) and broadcast loudness metering (BS.1770 / R128 / LRA). Typical dynamics by genre.

### Takeaway
Loudness grows as a power function of intensity with exponent about 0.3 (0.6 re sound pressure). Stevens reported 0.67 re pressure for a 3 kHz tone. So +10 dB is heard as about twice as loud (1 sone = 40 phon; each +10 phon doubles sones). Broadcast metering (ITU-R BS.1770 / EBU R128) measures loudness on three windows: momentary 400 ms, short-term 3 s, and gated integrated over a whole programme. Loudness Range (LRA) is the 10th-to-95th-percentile spread of 3-s short-term loudness after gating. Published LRA figures for music are mostly practitioner measurements: pop, rock and EDM about 3–10 LU (typically 5–7), classical about 10–20 LU. Psychoacoustic loudness models also smooth instantaneous loudness with AGC-like attack/release filters: about 22 ms attack and 50 ms release for short-term loudness (one note), then slower smoothing for long-term loudness (a phrase).

### Cited Findings
- Sones and phons: 1 sone = 40 phon (a 1 kHz tone at 40 dB SPL). Loudness in sones is very nearly a power function of intensity with exponent 0.3, so each +10 phon (+10 dB at 1 kHz) almost exactly doubles loudness. Mapping: 1, 2, 4, 8, 16, 32, 64 sone = 40, 50, …, 100 phon. — [Wikipedia: Sone, citing Stevens](https://en.wikipedia.org/wiki/Sone)
- Stevens' exponent table: loudness 0.67 against sound pressure of a 3000 Hz tone (equivalent to about 0.33 against intensity, derived from I ∝ p²). — [Wikipedia: Stevens's power law, table "Exponents reported by Stevens"](https://en.wikipedia.org/wiki/Stevens%27s_power_law)
- Time-varying loudness model (Glasberg & Moore lineage, as used by Moore et al. 2016). Instantaneous specific loudness comes from the excitation pattern via a compressive nonlinearity "intended roughly to represent the compression that occurs in the cochlea (Robles & Ruggero 2001)". — [Moore, Glasberg, Varathanathan & Schlittenlacher 2016, Trends in Hearing](https://pmc.ncbi.nlm.nih.gov/articles/PMC5318944)
  - Short-term specific loudness is a running average "resembling the way that a control signal is generated in an automatic gain control circuit", with αa = 0.045 (attack) and αr = 0.02 (release) per 1 ms frame. This corresponds to time constants of about 22 ms attack and about 50 ms release (derived: τ = −1/ln(1−α) ms).
  - Long-term loudness is a second AGC-like smoother on the short-term loudness, again with separate attack and release constants.
- Short-term loudness corresponds to "a short segment of sound such as a single word in speech or a single note in music". Long-term loudness corresponds to "a whole sentence or a musical phrase". — [Glasberg & Moore 2002 as summarised in Frontiers in Neuroscience 2016](https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2016.00183/full) (via search summary)
- ISO 532-3:2023 standardises the Moore–Glasberg–Schlittenlacher method, including short-term and long-term loudness. — [ISO 532-3:2023 catalogue](https://iteh.es/catalog/standards/iso/9071eb5a-01ef-4f5c-8690-3c4d8c837568/iso-532-3-2023)
- EBU R128 / EBU Mode metering. — [Wikipedia: EBU R 128](https://en.wikipedia.org/wiki/EBU_R_128)
  - Windows: Momentary (M) is a 400 ms sliding window. Short-term (S) is a 3 s sliding window. Integrated (I) runs over the whole programme.
  - Update rates: at least 10 Hz for short-term, at least 1 Hz for integrated.
  - Integrated loudness uses an absolute gate at −70 LUFS and a relative gate 10 LU below the current integrated value. M and S are ungated.
- Loudness Range (EBU Tech 3342, v4 Nov 2023). — [EBU Tech 3342](https://tech.ebu.ch/docs/tech/tech3342.pdf)
  - LRA "quantifies the variation in a time-varying loudness measurement … on a macroscopic time-scale".
  - Input: BS.1770 loudness with a 3 s sliding window, sampled at 10 Hz or faster (overlap at least 2.9 s).
  - Gating: absolute −70 LUFS, then relative −20 LU below the absolute-gated level.
  - LRA is the 95th percentile minus the 10th percentile. The 10% floor stops a fade-out dominating; the 95% ceiling stops a single loud event (e.g. a gunshot) dominating.
  - Example: the film *The Matrix* has LRA 25 LU.
  - Compliance signals show LRA tracks section level differences in dB directly: two 20 s tones 10 dB apart give LRA 10 ± 1 LU, 5 dB apart give 5 ± 1, 20 dB apart give 20 ± 1. A commercial-like segment gives about 5 LU; a movie/drama-like segment about 15 LU.
- Genre LRA figures (practitioner, not peer-reviewed). — [Yamaha Pro Audio Hub](https://hub.yamaha.com/proaudio/recording/what-is-loudness); [Production Expert](https://www.production-expert.com/home-page/2017/12/14/tutorial-in-music-mastering-what-is-loudness-range?format=amp); [Auphonic](https://us.auphonic.com/blog/2019/08/19/dynamic-range-processing/) (which page gave which number was not individually verified)
  - Classical: about 20 LU, or a 10–20 LU band; widest, followed by jazz.
  - Pop and rock: "usually +5 to +7 LU", or pop 4–8 and rock 5–10 LU.
  - EDM: 4–8 LU. One measured sample averaged 5.9 LU, range 3.0–9.9 LU.
  - Another sample: pop averaged 6.4 LU (10 songs, range 3.7–12), rock 5.6 LU, electronic 7.2 LU (one track 15.2 LU), country 3.6–14.9 LU.
- An LRA of 6–12 LU "shows that a track has a considerable difference in loudness between the various sections". — [Production Expert](https://www.production-expert.com/home-page/2017/12/14/tutorial-in-music-mastering-what-is-loudness-range?format=amp) (practitioner guidance)
- LRA was designed around broadcast programmes. One source warns that only pure speech programmes give reliable, comparable LRA values. — [Auphonic blog](https://us.auphonic.com/blog/2019/08/19/dynamic-range-processing/) (via search summary)

### Inferences
- A verse-to-chorus or breakdown-to-drop contrast of X dB shows up as up to X LU of LRA, per the Tech 3342 tone tests. Mainstream pop, rock and EDM LRA of about 3–10 LU therefore means section contrasts of the order of 3–10 dB at the 3 s scale. That is roughly 1.2–2× in perceived loudness (derived: 2^(X/10)), clearly audible given the about 1 dB discrimination limit in section 2.
- The broadcast meter's own time-scale hierarchy (400 ms, 3 s, whole programme) and the psychoacoustic one (22/50 ms per note, slower per phrase) agree. Note-level and phrase-level level changes are part of what listeners judge as loudness. Only the whole-programme level is a normalisation target in broadcast practice.

### Gaps
- ISO 226:2023 equal-loudness contour values were not retrieved. That loudness growth is steeper at low frequencies (contours converging at high levels) is UNVERIFIED here.
- Long-term loudness (LTL) attack and release constants in the Moore–Glasberg model were not extracted (equations seen, values not). UNVERIFIED.
- No peer-reviewed corpus figure for the verse-to-chorus loudness difference in dB was found. Van Balen et al. 2013 (ISMIR) analysed 649 songs' section features including loudness, but its PDF could not be parsed. — [Van Balen et al. 2013](https://archives.ismir.net/ismir2013/paper/000180.pdf)
- Peer-reviewed LRA-by-genre statistics (e.g. Skovenborg 2012, AES 132nd Convention paper 8616, cited by Tech 3342) were not retrieved.

---

## 4. Brightness scaling and the loudness–brightness correspondence. What dB-to-luminance mapping makes "twice as loud" look "twice as bright"?

### Takeaway
Brightness grows as a power of luminance with exponent about 0.33 for an extended (5°) target in the dark, and about 0.5 for a point source or brief flash. CIE L* uses a cube root of relative luminance, with an effective exponent near 0.43 including its offset. Stevens and Marks (1965) found by direct cross-modality matching that brightness and loudness have about the same exponent relative to stimulus energy. Equal subjective magnitude therefore needs luminance roughly proportional to sound intensity: about 0.9–1.0 dB of luminance per dB of sound for an extended source in the dark, and about 0.6–0.67 dB per dB for a point source. "Twice as loud" (+10 dB) then needs about ×8 luminance for an extended target, or about ×4 for a point source. People spontaneously pair louder with brighter, in explicit matching and in speeded-classification tasks.

### Cited Findings
- Stevens' brightness exponents: 0.33 for a 5° target in the dark; 0.5 for a point source; 0.5 for a brief flash; 1.0 for a point source briefly flashed. Lightness of grey papers (reflectance) is 1.2. Loudness is 0.67 against sound pressure of a 3 kHz tone. — [Wikipedia: Stevens's power law, Stevens' table](https://en.wikipedia.org/wiki/Stevens%27s_power_law)
- Stevens & Marks 1965 (PNAS 54:407): observers matched the brightness of a light to the loudness of a noise, and vice versa, at various intensities. The results follow the power law and "suggest that brightness and loudness have approximately the same exponents relating them to stimulus energy." — [Stevens & Marks 1965, PMC record](https://pmc.ncbi.nlm.nih.gov/articles/PMC219679) (abstract text via search summary; full scanned text not read)
- CIE L* = 116·f(Y/Yn) − 16, where f(t) = t^(1/3) for t > (6/29)³ ≈ 0.008856 and linear below. L* is 0 for black and 100 for white. The cube root with the offset gives an effective power of about 0.43 for photopic vision. — [Wikipedia: CIELAB colour space](https://en.wikipedia.org/wiki/CIELAB_color_space)
- People map auditory loudness onto visual luminance in explicit matching tasks (Marks 1974; Root & Ross 1965) and in implicit association tests (Marks 1987). — [Lancaster University review, "Cross Sensory Correspondences"](https://eprints.lancs.ac.uk/id/eprint/76988/1/Cross_Sensory_Correspondences.pdf) (via search summary)
- Marks 1987: visual discrimination was faster and more accurate when an accompanying sound matched it in intensity (congruent loud with bright) than when it mismatched. A later replication found the loudness-congruence effect in a brightness classification task but not in a lightness (surface reflectance) task. — [Hubbard review on synaesthesia and cross-modal correspondences](https://uh.edu/~tkoozin/cognition/HubbardSynes.pdf); replication reported in [Attention, Perception & Psychophysics](https://link.springer.com/content/pdf/10.3758/s13414-018-01639-7.pdf) (attribution of the replication to this specific paper is UNVERIFIED)
- Marks 1974 also reported pitch–brightness correspondences: high tones with brighter greys, low tones with darker. — [Hubbard review](https://uh.edu/~tkoozin/cognition/HubbardSynes.pdf)

### Inferences (derived formulae)
- Equal-magnitude matching: if loudness N ∝ I^a (I = sound intensity) and brightness B ∝ Y^b (Y = luminance), then N ∝ B requires Y ∝ I^(a/b). In decibels: ΔY_dB = (a/b)·ΔL_dB.
  - Extended source in the dark, a = 0.3 (sone rule) or 0.335 (Stevens 0.67 re pressure), b = 0.33: a/b ≈ 0.9–1.0. About 1 dB of luminance per dB of sound, i.e. luminance ∝ sound intensity (∝ p²).
  - Point source or brief flash, b = 0.5: a/b ≈ 0.6–0.67 dB per dB.
  - "Twice as loud" = +10 dB (sone rule). "Twice as bright" = ×2^(1/0.33) ≈ ×8.2 luminance (+9.1 dB) for an extended target, or ×2^(1/0.5) = ×4 (+6.0 dB) for a point source.
  - Equivalent mapping: Y = Y_ref · 10^(k·(L − L_ref)/10), with k ≈ 0.9–1.0 for an extended source and 0.6–0.67 for a point source. Perceived brightness then doubles per +10 dB, as loudness does.
- An edge-lit diffusing plate is an extended source rather than a point source. The 0.33 (extended) exponent is therefore the more relevant reference (inference: its luminous area and viewing conditions were not measured). Room ambient light changes the brightness exponent (Stevens & Stevens 1963, "Brightness function: effects of adaptation", is cited by Stevens & Marks 1965 but was not read).
- LED drive (PWM duty) is proportional to luminance, a physical quantity, so perceived brightness ≈ duty^0.33–0.5. With k ≈ 1 the light needs as many dB of luminance range as the sound has dB of level range. An 8-bit linear duty range of 255:1 spans 10·log10(255) ≈ 24 dB of luminance (derived), so at k ≈ 0.9–1.0 it can show only about 24–27 dB of sound-level range (about 40 dB at k = 0.6). This bounds how much raw sound dynamic range can be shown before a slow normaliser or compressive mapping is needed.

### Gaps
- The exact exponent fitted in Stevens & Marks 1965 (slope of the brightness–loudness matching function) was not read from the original. Only the abstract's "approximately the same exponents re energy" is confirmed.
- The Weber fraction for brightness (luminance discrimination) was not retrieved. UNVERIFIED.
- Brightness exponents for self-luminous extended sources under room (non-dark) adaptation were not retrieved.

---

## 5. Engineered auditory front ends: CARFAC, PCEN, log-mel with fixed floor, RASTA, adaptive whitening. Built for recognition or for faithful dynamics?

### Takeaway
Every adaptive front end examined here is built to make a downstream recogniser or detector invariant to level, channel and stationary background. Each removes slow level changes by design.
- **CARFAC:** a cochlear model. It pairs instantaneous outer-hair-cell compression with a four-stage AGC (2, 8, 32 and 128 ms) that also smooths gain across neighbouring channels.
- **PCEN:** divides each channel by its own smoothed energy (default 400 ms) raised to α = 0.98, then root-compresses. A sustained level change is reduced to about 2% of its dB size, deliberately "discarding … slow changes in loudness".
- **RASTA:** band-passes log-spectral trajectories (about 1–16 Hz) to strip slow channel effects.
- **Adaptive whitening:** divides each bin by a slowly decaying per-bin peak (aubio default: 60 dB decay over 250 s) to sharpen onset detection.
- **Log-mel with a fixed floor:** the only one that keeps absolute and relative level (as a dB shift), at the cost of skewed, correlated statistics.

None of these is designed to display musical dynamics faithfully. Recognition front ends treat level as nuisance variation.

### Cited Findings
CARFAC (Lyon; open-source, Google):
- CARFAC stands for "Cascade of Asymmetric Resonators with Fast-Acting Compression". — [CARFAC_Design.m header](https://github.com/google/carfac/blob/master/matlab/CARFAC_Design.m)
- Default AGC parameters. — [CARFAC AGC_params_default.m](https://github.com/google/carfac/blob/master/matlab/AGC_params_default.m)
  - 4 stages with time constants 0.002·4^(0:3) s = 2, 8, 32, 128 ms.
  - AGC_stage_gain = 2 ("gain from each stage to next slower stage"). Total DC gain 1+2+4+8 = 15 ("Add up 1, 2, 4, 8, giving 15 by default", CARFAC_Design.m).
  - Decimation [8, 2, 2, 2].
  - Spatial spread across channels: AGC1_scales = 1.0·√2^(0:3) and AGC2_scales = 1.65·√2^(0:3), "in units of channels", "spread more toward base". Implemented as a 3-point FIR smoother across channels (AGC1 smooths base to apex, AGC2 back).
  - AGC_mix_coeff = 0.5.
- The AGC feeds back into the cascade, moving the poles and zeros (damping) of the resonator stages. Its gain changes are applied as changes to the cochlear-amplifier damping, not as a separate output gain. — [Lyon et al. 2024, "The CARFAC v2 Cochlear Model…", §2.7](https://arxiv.org/html/2404.17490v1)
- Default CAR (filter-cascade) parameters. — [CAR_params_default.m](https://github.com/google/carfac/blob/master/matlab/CAR_params_default.m)
  - Fast "velocity nonlinearity": velocity_scale 0.1, v_offset 0.04.
  - Damping range min_zeta 0.10 to max_zeta 0.35.
  - Channel spacing 0.5 ERB per step; lowest pole 30 Hz.
- Default two-capacitor inner-hair-cell adaptation: tau1_out 0.5 ms, tau1_in 0.2 ms, tau2_out 1 ms, tau2_in 10 ms, smoothing tau_lpf 80 µs. — [IHC_params_default.m](https://github.com/google/carfac/blob/master/matlab/IHC_params_default.m)
- CARFAC v2 was produced for research and machine-hearing use. Its changes include fixing a DC quadratic-distortion anomaly, reducing high-frequency neural synchrony, and adding a reduced-cochlear-amplifier (hearing-impairment) option. It is also integrated into the Auditory Model Toolbox. — [Lyon et al. 2024 abstract](https://arxiv.org/abs/2404.17490)

PCEN (Wang et al. 2017; Lostanlen et al. 2019):
- Introduced as a trainable front end for robust, far-field keyword spotting. — [Wang, Getreuer, Hughes, Lyon & Saurous 2017 (arXiv:1607.05666)](https://arxiv.org/abs/1607.05666)
- The source for the remaining PCEN findings is [Lostanlen et al. 2019, "Per-Channel Energy Normalization: Why and How", IEEE SPL 26(1)](https://www.justinsalamon.com/uploads/4/3/9/4/4394963/lostanlen_pcen_spl2018.pdf).
- Formula:
  - PCEN(t,f) = (E(t,f)/(ε + M(t,f))^α + δ)^r − δ^r
  - M(t,f) = s·E(t,f) + (1 − s)·M(t − τ, f), a first-order IIR low-pass with time scale T.
- Each parameter:
  - T (or s): "the transition threshold between a stationary regime of background and a transient regime of foreground". It should be above the periods of foreground amplitude modulation and below those of background.
  - α (AGC exponent, 0–1): in the active regime, multiplying E by C multiplies the gain-normalised G by about C^(1−α). α closer to 1 cancels more background.
  - ε: a silent/active threshold, with "no effect as long as it is set below unit roundoff".
  - δ and r: dynamic-range compression. In the loud regime PCEN ≈ G^r, so a factor C becomes about C^(r(1−α)). Recommended r = 1/2 indoors and r = 1/4 outdoors.
- Default parameters (librosa, identical to Wang et al.): T = 400 ms (s ≈ 0.025 at τ = 23 ms), ε = 10⁻⁶, α = 0.98, δ = 2, r = 1/2. Bird-detection settings: T = 60 ms, α = 0.8, δ = 10, r = 0.25.
- What it throws away: PCEN "enhances transient events (bird calls) while discarding stationary noise (insects) as well as slow changes in loudness (vehicle)" (Fig. 1 caption).
  - With α = 1 and ε = 0, PCEN is invariant to any fixed filtering of the waveform by the room or device (Proposition III.3).
  - It Gaussianises magnitudes and decorrelates frequency bands, converting soundscapes into something close to additive white Gaussian noise for classifiers.
- Documented drawbacks:
  - Five parameters that may need to be frequency-dependent.
  - α = 1 can skew magnitude distributions to the right.
  - T must be re-tuned whenever the time-frequency resolution changes.
  - The optimal T depends on chirp rate and reverberation (rule of thumb T·c·Q = K, with K ≈ 1 in dry rooms and above 10 in highly reverberant ones).

Log-mel:
- Log-mel "maps all magnitudes to a decibel-like scale". Its magnitudes are skewed (Shapiro–Wilk p < 0.005 against normality on three datasets) and strongly cross-correlated between non-adjacent bands. — [Lostanlen et al. 2019, §II](https://www.justinsalamon.com/uploads/4/3/9/4/4394963/lostanlen_pcen_spl2018.pdf)

RASTA:
- RASTA (Hermansky & Morgan 1994, IEEE Trans. Speech Audio Process. 2(4):578–589, doi:10.1109/89.326616) band-pass filters the time trajectories of log-spectral (critical-band) values for speech recognition robust to channel distortion. — [IEEE record via search](https://data.zhenzhi.com/details/1/1000196660)
- The filter architecture and most parameters were set ad hoc. Only its single pole was chosen, by minimising word-recognition error. — [Hermansky & Fousek 2005, Interspeech](https://www.isca-archive.org/interspeech_2005/hermansky05_interspeech.html) (via search summary)
- RASTA-type band-pass behaviour passes modulation rates of about 1–16 Hz. — [Intelligibility of speech with filtered time trajectories (secondary)](https://typeset.io/pdf/intelligibility-of-speech-with-filtered-time-trajectories-of-1fmgtb472z.pdf)
- Cepstral mean subtraction over a 165 ms window implies high-pass filtering at about 1 Hz. — [ICPhS 1995 paper](https://www.coli.uni-saarland.de/Phonetics/icphs/ICPhS1995/13_ICPhS_1995_Vol_3/p13.3_042.pdf)

Adaptive whitening (Stowell & Plumbley 2007, ICMC):
- Each STFT bin's magnitude is normalised by a recent per-bin maximum, so each bin's dynamic range stays similar over time. This improves onset detection functions without training. — [Stowell & Plumbley 2007, ICMC (Surrey record)](https://openresearch.surrey.ac.uk/esploro/outputs/conferencePresentation/Adaptive-whitening-for-improved-real-time-audio/99513962202346); [ISMIR 2012 follow-up](https://archives.ismir.net/ismir2012/paper/000049.pdf)
- Reference implementation (aubio): P[k] ← max(|X[k]|, max(r·P[k], floor)), then |X[k]| ← |X[k]|/P[k]. The decay is r = 0.001^((hop/fs)/relax_time), meaning the stored peak falls 60 dB over relax_time. Defaults: relax_time = 250 s (allowed about 20–500 s), floor = 10⁻⁴ (allowed 10⁻⁶ to 0.2). — [aubio awhitening.c](https://github.com/aubio/aubio/blob/master/src/spectral/awhitening.c)

### Inferences
- **PCEN arithmetic at defaults (derived from the asymptotic forms above):**
  - A sustained +20 dB change (energy ×100) lasting much longer than T = 400 ms changes G by 100^0.02 ≈ ×1.096 (+0.4 dB). After r = 0.5 compression the output changes by about +0.2 dB. So 98–99% of a sustained level change in dB is removed within a few hundred milliseconds.
  - A transient much faster than T passes through and is compressed only by the exponent r.
  - PCEN is therefore an onset and transient enhancer that erases section contrast unless T is made very long and α small.
- **CARFAC:** with the slowest AGC stage at 128 ms, the model's gain control tracks level changes slower than about 0.1–0.5 s. Its AGC acts by changing cochlear damping over a limited range (zeta 0.10–0.35), so compression is partial, not full normalisation. The overall compression ratio was not retrieved. It is a faithful model of the periphery, but the periphery's output is not perceived loudness: loudness models add later integration (section 3).
- **Adaptive whitening:** with relax_time = 250 s, the per-bin divisor is close to the running maximum of the whole track. Within-track level structure below each bin's peak is largely preserved, and level is expressed relative to that bin's own loudest moment. That flattens the spectral balance across bins, which is not the same as perceived timbre.
- **RASTA:** removes components slower than about 1 Hz from log-spectral trajectories, which includes phrase and section contrast. It is a recognition device.
- **Log-mel with a fixed floor:** the only front end here whose output moves 1 dB per dB of input at all time scales. It preserves the absolute and relative level that the light mapping in section 4 needs, but by itself it has no protection against room-volume changes.

### Gaps
- Lyon's "Human and Machine Hearing" (2017) chapters on CARFAC AGC and the overall input/output compression ratio (dB/dB) of CARFAC were not retrieved. UNVERIFIED.
- The exact RASTA transfer function (often quoted with a pole at 0.98) was not confirmed from the 1994 paper. UNVERIFIED.
- The original Stowell & Plumbley 2007 PDF was unreachable (404). The formula is from the aubio reference implementation by a co-author's community (Brossier), not the paper itself.

---

## 6. Time scales: which level changes listeners hear as musical, and which the ear adapts away

### Takeaway
The literature gives a consistent ladder.
- **About 1–50 ms:** onset emphasis. Neural rapid and short-term adaptation; loudness attack about 22 ms and release about 50 ms per note.
- **About 0.1–0.5 s:** beat and accent scale. Music's amplitude-modulation spectrum peaks near 2 Hz. Momentary loudness uses 400 ms. Neural mean-level adaptation runs at 160–330 ms, and the MOC reflex at 70–330 ms.
- **About 3 s to tens of seconds:** phrase and section scale. Short-term loudness and LRA use 3 s blocks. Long-term loudness covers a phrase. Slow neural and MOC components run at about 25 s to tens of seconds.
- **Minutes:** whole-programme loudness, the only quantity broadcast practice normalises.

The ear's adaptive processes are partial at every scale. Even the slowest leave most of a sustained level change in the code, and listeners still hear section contrast as loudness. The data support preserving level contrast up to at least the phrase and section scale (seconds to about a minute), and treating only programme-level or room-level offsets as something perception discounts. Because absolute identification is limited to about 7 categories, absolute level is a weak cue even for listeners.

### Cited Findings
- Over 39 hours of Western music recordings, music's temporal (amplitude) modulation spectrum shows a broad but consistent peak around 2 Hz. Speech, across 9 languages, peaks around 5 Hz (4–5 Hz across versions). — [Ding, Patel, Chen, Butler, Luo & Poeppel 2017, Neurosci Biobehav Rev 81:181](https://read.qxmd.com/read/28212857/temporal-modulations-in-speech-and-music); [bioRxiv preprint](https://www.biorxiv.org/content/10.1101/059683.full.pdf)
- Loudness-model integration: short-term loudness (one note) uses about 22 ms attack and 50 ms release (derived from αa = 0.045, αr = 0.02 at 1 ms). Long-term loudness (one phrase) is a further slower smoothing. — [Moore et al. 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5318944); [Frontiers 2016 summary of Glasberg & Moore 2002](https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2016.00183/full)
- Broadcast windows: momentary 400 ms ("instantaneous loudness"), short-term 3 s ("more averaged, less event-dependent"), integrated over the whole programme. — [Wikipedia: EBU R 128](https://en.wikipedia.org/wiki/EBU_R_128). LRA is computed from 3 s windows and described as variation "on a macroscopic time-scale". — [EBU Tech 3342](https://tech.ebu.ch/docs/tech/tech3342.pdf)
- Neural mean-level adaptation: 160 ms after increases and about 330 ms after decreases (inferior colliculus), plus a slow component over tens of seconds. — [Dean et al. 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC6670892). Auditory nerve: 100–400 ms. — [Wen et al. 2012](https://doi.org/10.1152/jn.00055.2012)
- In Dean et al.'s environmental recordings, level changes spanned "rapid, transient increases or decreases that lasted a few tens of milliseconds, to slower fluctuations lasting several seconds". Adaptation turns the neural response into a high-pass-filtered version of level. — [Dean et al. 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC6670892)
- MOC reflex: about 25 ms delay; components of about 70 ms, 330 ms and 25 s. — [Backus & Guinan 2006](https://doi.org/10.1121/1.2169918)
- The size of adaptation is partial: auditory-nerve range shift of 0.05–0.47 dB/dB, never 1 dB/dB. — [Wen et al. 2009](https://pmc.ncbi.nlm.nih.gov/articles/PMC2774902)
- Absolute identification of loudness saturates at about 7 categories over about a 20 dB range. — [Luce, Green & Weber 1976](https://link.springer.com/article/10.3758/BF03198705). Relative discrimination is about 1 dB across 100–120 dB. — [Wen et al. 2009](https://pmc.ncbi.nlm.nih.gov/articles/PMC2774902)
- Broadcast normalisation targets only integrated (whole-programme) loudness. R128 "ties the use of compression to artistic and aesthetic decisions" rather than to getting a louder mix, and does not restrict within-programme dynamics. — [Wikipedia: EBU R 128](https://en.wikipedia.org/wiki/EBU_R_128)

### Inferences
| Time scale | Musical meaning | What the ear does | Preserve or normalise for a display (perception-based) |
|---|---|---|---|
| 1–50 ms | attack, transient, onset | rapid/short-term AN adaptation emphasises onsets; loudness attack ~22 ms, release ~50 ms | preserve; onsets are emphasised, not removed |
| 50 ms–1 s | note and beat accents (music modulation peak ~2 Hz) | MOC and neural mean-level adaptation begin (160–330 ms) but are partial (≤0.47 dB/dB at the AN) | preserve; accents are heard as loudness differences |
| 2–60 s | phrase and section contrast (verse/chorus, breakdown/drop; LRA 3–10 LU pop/EDM, ~20 LU classical) | slow neural and MOC components (tens of seconds; 25 s), still partial | preserve; listeners hear 3–10 dB section contrasts as 1.2–2× loudness |
| minutes and beyond | track-to-track mastering level, room volume | absolute level coded coarsely (~7 categories); broadcast practice normalises only here | normalise; this is where perception and industry practice both discount level |

### Gaps
- No direct study was found of how quickly listeners stop perceiving a sustained level step in music (perstimulatory loudness adaptation, induced loudness reduction). UNVERIFIED for music at living-room to venue levels.
- No source was found for typical living-room versus venue playback SPL differences in dB. UNVERIFIED.

---

## Implications for a sound-to-light instrument

These are science-level implications drawn from the findings above. They are not firmware recommendations.

1. **The ear is not a normalising AGC.** Its main level processor is an instantaneous compressive curve (0.2–0.3 dB/dB at basal CF over about 40–90 dB SPL, weaker at low frequencies). Its true feedback gain controls (MOC about 70 ms–25 s, stapedius above about 70–100 dB SPL) and neural range adaptation (160–400 ms, tens of seconds) are all partial: 0.05–0.47 dB per dB at the auditory nerve. A chain that normalises the waveform to its own recent peak (1 dB/dB) removes more level information than the auditory system does. "Loud chorus no brighter than quiet section" is the expected result of such a chain, and contradicts what listeners hear.
2. **Loudness is still heard after all this adaptation:** +10 dB sounds about twice as loud, and +6 dB about 1.5×. Mainstream pop, rock and EDM carry about 3–10 LU of section-level contrast and classical up to about 20 LU, measured on 3 s blocks. Those contrasts sit at the phrase and section scale (2–60 s), which the auditory literature and broadcast practice both treat as signal, not nuisance.
3. **A perceptually matched brightness law exists.** With brightness exponent about 0.33 (extended source in the dark) and loudness exponent about 0.3–0.335 re intensity, equal subjective magnitude needs Y ∝ I^(0.9–1.0): about 1 dB of luminance per dB of sound. Equivalently, luminance × about 8 per +10 dB, so brightness doubles each time loudness doubles. For a point-like or flashed source the slope is about 0.6–0.67 dB per dB (×4 per +10 dB). Stevens & Marks (1965) confirmed by direct matching that brightness and loudness share about the same exponent re energy. Marks (1987) showed louder-with-brighter congruence speeds perception.
4. **The light's own range bounds the mapping.** At about 1 dB per dB, a linear 8-bit luminance range (255:1, about 24 dB) displays only about 24–27 dB of sound-level range. Something must absorb the remainder: slow offsets (room volume, track mastering) plus any of the music's own dynamics beyond that range. Perception literature points to the slowest scale (minutes, programme level) as the part listeners discount. Absolute level is identified only to about 7 categories, while 1 dB relative differences are heard.
5. **The engineered front ends surveyed are recognition tools.** PCEN (default T = 400 ms, α = 0.98) removes about 98% of any sustained level change in dB within a few hundred milliseconds and keeps only transients. RASTA removes changes slower than about 1 Hz. CARFAC's AGC tops out at a 128 ms time constant. Adaptive whitening (250 s relax) divides by each bin's running peak. All are designed for level invariance, which is the opposite goal to displaying dynamics. Of the forms surveyed, only a log-magnitude (dB) representation with a fixed reference preserves level 1:1 at every time scale.
6. **The time-scale ladder from the literature:**
   - preserve onsets (1–50 ms);
   - preserve accents (50 ms–1 s; music's modulation peak about 2 Hz);
   - preserve section contrast (2–60 s);
   - discount only programme or room level (minutes).
   Where adaptation is used, the auditory system's own pattern is fast to adapt to increases (about 160 ms), slower to decreases (about 330 ms), and always partial.
