# Explainer stages 2 and 3 report
Sections added: id s2 (Stage 2: one silence test, section 10), id s3 (Stage 3: the loud guard stops cutting, section 11, incl. "Where we are"). Placed after verify, before compare.
Numbers (all read from files at build time by build_explainer2.py, or copied from the plan):
- S2 old % music hops silent, 15 cases: emu/analysis-s2/s2.json (music_share); new 0 in 15: emu/analysis-s2/s2-fast-release.json (music_silent)
- S2 time to silence 5.40-7.63 s: s2-fast-release.json stop_to_silent_s; 5 s wait: plan section 6
- S2 bench 0 of 85, 2.03 s: 20261111-k1-fe-show-s4/bench/s2final_bench.json; 23 of 82 old vs 0 of 81 new: bench/s2_bench_ab.json; "16 to 21 of 88": plan section 6 S2 evidence row
- Thresholds 16 / 25 counts^2, dwell 5 s, 0.3 s release: plan section 6 (S2 built and accepted rows)
- S3 emulator 1,926 / 2,000 / 2,000 vs 0: 20261111-k1-fe-show-s4/s3/s3-compare.txt (lines 1-3)
- S3 bench trim 100 of 110 below 1, min 0.374 -> 0 of 110, 1.000; light 3.96 -> 6.97; breakdown 1.95 -> 1.98; ratio 2.03 -> 3.52: bench/s3_bench.json
- Where we are: plan sections 4 and 6
Other edits: eyebrow, summary tile and bullet, limits bullet reworded to stages 1-3 built; roadmap rows 2 and 3 marked built, flashed, measured. Fixed CSS appended to explainer2.css.
Screenshots (this folder): s2_1280_light.png, s3_1280_light.png, s2_500_light.png, s3_500_light.png, s2_500_dark.png, s3_500_dark.png, full_1280.png, full_500.png. scrollWidth equals viewport at 1280 and 500 (no horizontal scroll), light and dark.
Fixed after looking: axis labels ("80 % of music hops..." now "80 %"), overlapping dot-strip labels removed, dot-strip scaled to chart size, added old/new colour legend.
sha256 of final html: 40a0d2013e859fe5e4d92f30c82a21278b66b76fefc915e0a91e12a35d4c5694
