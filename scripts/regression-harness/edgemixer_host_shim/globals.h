// Host stub for director/k1_edgemixer.cpp under -DK1_EDGE_PALETTE_HONOUR_V1.
// Device builds use the genuine system/globals.h. This file is never on the
// firmware include path.
#pragma once

struct K1ConfigShim {
  bool PALETTE_MODE_ENABLED;
};

inline K1ConfigShim CONFIG = {true};
inline bool SECONDARY_PALETTE_MODE_ENABLED = true;
