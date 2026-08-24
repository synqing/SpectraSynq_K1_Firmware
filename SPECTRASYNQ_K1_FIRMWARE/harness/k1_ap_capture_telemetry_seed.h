#pragma once

// Source-seeded capture/telemetry seam for AP/Vision tests and notebooks.
// This wrapper keeps the portable lane aligned to existing host-only telemetry
// declarations in serial/k1_ap_capture_telemetry.h.

#include "../serial/k1_ap_capture_telemetry.h"

namespace k1 {
namespace harness {

// Optional compatibility alias for lane naming consistency.
inline constexpr bool kHasApTelemetryContract = true;

}  // namespace harness
}  // namespace k1

