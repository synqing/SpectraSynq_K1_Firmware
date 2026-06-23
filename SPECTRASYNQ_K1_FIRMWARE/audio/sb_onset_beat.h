#pragma once

#include "sb_audio_snapshot.h"

void sb_onset_beat_update(const SBAudioSnapshot& audio);
SBOnsetBeatEvent sb_onset_beat_read();
void sb_onset_beat_reset();

