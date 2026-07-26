// SPDX-License-Identifier: GPL-3.0-only
// Copyright 2026 SpectraSynq
//
// k1_sync_link — dual-K1 sync transport probe (Phase 0, NON-SHIPPABLE).
// Compiled ONLY in the k1_sync_probe_* envs under -DSB_K1_SYNC_PROBE; the
// radio-isolation guard (scripts/ble_midi/guard_k1_radio_isolation.py) fails
// any production artefact containing this TU's symbols or UUIDs.
//
// Phase-0 scope: BLE custom GATT link (NimBLE dual-role on the leader) carrying
// a 33 Hz timestamped dummy-replay stream + RTT clock-sync bursts, instrumented
// by the wired GPIO cross-trigger oracle (scripts/dual_sync_probe/). Roles are
// fixed per env: -DK1_SYNC_ROLE_LEADER (main K1) / -DK1_SYNC_ROLE_FOLLOWER
// (bench K1). Lane authority: artifacts/k1_dual_sync_eval_2026-07-08/phase0-plan.md
#pragma once

#ifdef SB_K1_SYNC_PROBE

namespace k1_sync {

// K1-SyncLink GATT identity (leader advertises as "K1-SyncLink").
inline constexpr const char* kSyncServiceUuid = "53594E43-4B31-4544-9B1A-2026070800A1";
inline constexpr const char* kSyncStreamCharUuid = "53594E43-4B31-4544-9B1A-2026070800A2";  // leader -> follower notify
inline constexpr const char* kSyncClockCharUuid = "53594E43-4B31-4544-9B1A-2026070800A3";   // RTT clock-sync write/notify
inline constexpr const char* kSyncDeviceName = "K1-SyncLink";

void begin();  // init NimBLE role(s) per build flag; safe to call once from setup()
void poll();   // main-loop service hook (non-blocking)

// Replay the current application-ready lifecycle snapshot for a host capture
// that attached after the one-shot transition logs. Emits a fail-closed
// SYNC_STATUS line; LinkUp + Negotiated follow only when the snapshot is valid.
void status();

// True only while SyncLink is application-ready: both stream and clock
// subscriptions are established. A raw GAP connection is not sufficient.
bool is_linked();

// Host-plumbing fault tokens (bench only). These are NOT Gate-0 delay proof
// until F3 replaces the timestamp-only delay modes with a real pending queue:
//   "delay5"  — adds 5 ms to the printed consume stamp only (stamp-fake)
//   "delay20" — adds 20 ms to the printed consume stamp only (stamp-fake)
//   "drop10"  — follower drops ~10% of stream packets before apply
//   "off"     — clear injection
// Returns true if the mode string was recognised. Never persists, never touches
// cal or config. No-op on the leader (apply/drop happen on the follower).
bool set_fault(const char* mode);

}  // namespace k1_sync

#endif  // SB_K1_SYNC_PROBE
