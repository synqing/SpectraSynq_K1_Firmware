# HAL scaffold (S3-Resident / driver boundary)

## Role

`hal/` owns output-specific code that must stay near board hardware:
- LED pixel representation and emission surface
- SPI transport to the new portable-core link
- Build/peripheral-specific serial or timer boundaries

## Priority

The immediate high-cost portability work is not the DSP core; it is the
`CRGB`/`FastLED` type surface and how it reaches real strip output.

## Current evidence to preserve

- `k1_sync_link.h/.cpp` is a parked BLE GATT probe (`SB_K1_SYNC_PROBE`) and not the new portable link.
- Any new inter-MCU transport should be separate from that file set and begin as a greenfield SPI seam.

## First files to land under this folder

- `pixel_port.h` (abstract pixel API and conversion contract)
- `spi_link.h` (frame serialisation and frame queue interface)
- `spi_link_mock.h` (host/desktop parity harness)
