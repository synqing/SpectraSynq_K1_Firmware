#pragma once
/**
 * input.h
 * Routes UI gestures to Net sends. Maintains simple local stepping rules.
 */
#include <Arduino.h>

namespace Input {

void init();

// Tile actions
void onEffectNext();
void onBrightnessToggleStep();
void onParamStep(uint8_t index); // 1 or 2

} // namespace Input
