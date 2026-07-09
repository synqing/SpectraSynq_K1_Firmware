#pragma once

#include "k1_audio_snapshot.h"

void k1_onset_beat_update(const K1AudioSnapshot& audio);
K1OnsetBeatEvent k1_onset_beat_read();
void k1_onset_beat_reset();

