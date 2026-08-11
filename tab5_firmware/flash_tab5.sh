#!/bin/bash
# Wrapper script to fix PlatformIO riscv32 toolchain PATH issue

export PATH="/Users/spectrasynq/.platformio/tools/toolchain-riscv32-esp/bin:$PATH"

cd "$(dirname "$0")"
pio run -e tab5_p4 --target upload
