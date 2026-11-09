#!/bin/zsh
# Quiet-machine C5 measurements (run after the emulator suites finish).
cd /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/lane-c-emu
until /usr/bin/grep -q "^exit=" logs/c4-v2-001.log; do sleep 10; done
.venv/bin/python player/show_player.py --stream stream/loreen_75_155_120hz_v2.prsm --dry-run --asset /Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3 --log runs/c5-dryrun-full-quiet.jsonl
.venv/bin/python player/log_stats.py runs/c5-dryrun-full-quiet.jsonl > runs/c5-dryrun-full-quiet.stats.json
.venv/bin/python player/pty_test.py runs/c5-pty-full-quiet --stream stream/loreen_75_155_120hz_v2.prsm --asset /Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3
echo quiet_done
