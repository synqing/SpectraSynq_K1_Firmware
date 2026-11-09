#!/bin/zsh
cd ${0:A:h}/..
S=stream/loreen_75_155_120hz_v2.prsm
pgrep -lx afplay && { echo "afplay running; abort"; exit 1; }
.venv/bin/python player/show_player.py --stream $S --dry-run --silent-audio --pacing audio --log runs/c5-silent-pacing-audio.jsonl
.venv/bin/python player/log_stats.py runs/c5-silent-pacing-audio.jsonl > runs/c5-silent-pacing-audio.stats.json
.venv/bin/python player/show_player.py --stream $S --dry-run --silent-audio --pacing wall --log runs/c5-silent-pacing-wall.jsonl
.venv/bin/python player/log_stats.py runs/c5-silent-pacing-wall.jsonl > runs/c5-silent-pacing-wall.stats.json
.venv/bin/python player/pty_test.py runs/c5-pty-silent-pacing-audio --stream $S --silent-audio --pacing audio --seek 30:120 --seek 50:100
.venv/bin/python player/log_stats.py runs/c5-pty-silent-pacing-audio/player.jsonl > runs/c5-pty-silent-pacing-audio/log_stats.json
echo pacing_done
