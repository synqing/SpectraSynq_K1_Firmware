#!/usr/bin/env bash
# Tight wrapper around `pio run -e <env>` for agent use.
# Accepts exactly one env argument and rejects any dangerous token.
# This wrapper exists because Devin `Exec(pio run -e ...)` permissions are
# prefix-based and can match appended arguments.
#
# Defense in depth: the allowlist grep below already rejects any argument
# that is not exactly one of the three allowed env names. The dangerous-token
# scan is a second layer in case the allowlist logic is ever loosened.

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "ERROR: exactly one env argument required" >&2
  exit 1
fi

ENV="$1"

# Primary gate: exact-match allowlist. grep -w matches whole words only,
# so any argument with appended flags/spaces is rejected here.
# k1_bench_ws2816_1313 added 2026-07-15: radio-free WS2816C-1313 LED-controller
# evaluation build. This wrapper still rejects upload/monitor/erase tokens below.
ALLOWED_ENVS="k1_prod_im73d k1_hardware k1_bench_reference k1_bench_im73d k1_bench_im73d_dsr16 k1_bench_ws2816_1313"
case "$ENV" in
  k1_prod_im73d|k1_hardware|k1_bench_reference|k1_bench_im73d|k1_bench_im73d_dsr16|k1_bench_ws2816_1313)
    : ;;
  *)
    echo "ERROR: env '$ENV' is not in allowed list: $ALLOWED_ENVS" >&2
    exit 1
    ;;
esac

# Secondary gate: reject dangerous tokens even if the allowlist is loosened.
if [[ "$ENV" == *"upload"* ]] || \
   [[ "$ENV" == *"--target"* ]] || \
   [[ "$ENV" == *"-t"* ]] || \
   [[ "$ENV" == *"erase"* ]] || \
   [[ "$ENV" == *"monitor"* ]] || \
   [[ "$ENV" == *"device"* ]] || \
   [[ "$ENV" == *";"* ]] || \
   [[ "$ENV" == *"|"* ]] || \
   [[ "$ENV" == *"&"* ]] || \
   [[ "$ENV" == *'`'* ]] || \
   [[ "$ENV" == *'$('* ]] || \
   [[ "$ENV" == *'${'* ]] || \
   [[ "$ENV" == *'<'* ]] || \
   [[ "$ENV" == *'>'* ]] || \
   [[ "$ENV" == *$'\n'* ]]; then
  echo "ERROR: env argument contains forbidden token" >&2
  exit 1
fi

# Execute the narrowly-scoped build command only.
exec pio run -e "$ENV"
