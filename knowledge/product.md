---
title: SpectraSynq K1 — Product Context
status: draft
last_verified: 2026-07-13
sources:
  - CLAUDE.md
  - AGENT_OS.md
owner: knowledge-curator
---

# Product Context

SensoryBridge K1 is a **music-to-visual translation system** for dual-channel
edge-lit Light Guide Plate hardware — not generic audio-reactive LEDs.

## North star

Perceptual impact and musical relevance exceed architecture elegance. Visual
correctness, musical responsiveness, and colour clarity are non-negotiable.

## Core capabilities

- Real-time Goertzel GDFT spectral analysis (80 bins → 24 perceptual bands)
- Beat/tempo PLL, per-band onset detection, chord saliency
- Dual-core: Core 0 audio (hard real-time); Core 1 visual render (~100 FPS)
- Dual-channel independent effects on WS2812B edge lighting

## Hardware

ESP32-S3-DevKitC-1-N16R8 reference platform. See
[`docs/hardware/device-build-registry.md`](../docs/hardware/device-build-registry.md)
for device↔env pairing.

## Doctrine

Before AP/VP or pipeline changes, invoke `/sensorybridge-doctrine`. Architecture
is subordinate to perceptual impact.
