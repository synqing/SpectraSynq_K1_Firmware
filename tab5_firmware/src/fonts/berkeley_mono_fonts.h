#pragma once

/**
 * Berkeley Mono — instrument / word ladder (21 / 24 / 34 / 55).
 * Display hero numerals are Countach via deck_type.h DECK_TYPE_DISPLAY_55 — NOT Mono.
 */

#include "deck_fonts.h"

#define BERKELEY_LABEL_SMALL   &berkeley_mono_21
#define BERKELEY_LABEL_MEDIUM  &berkeley_mono_34
#define BERKELEY_LABEL_LARGE   &berkeley_mono_34
#define BERKELEY_VALUE_SMALL   &berkeley_mono_55
#define BERKELEY_VALUE_MEDIUM  &berkeley_mono_55
#define BERKELEY_VALUE_LARGE   &berkeley_mono_55
/* Misnamed legacy macro: large instrument Mono only — never Countach / display hero. */
#define BERKELEY_HERO          &berkeley_mono_55
