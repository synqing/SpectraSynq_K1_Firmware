#!/bin/bash
# Export a commit into the session scratchpad with a private git dir (handover §6). Never touches the shared checkout.
# usage: mkexport.sh <name> <sha>
set -euo pipefail
R=$HOME/SpectraSynq_K1_Firmware
SP=/private/tmp/claude-501/-Users-spectrasynq-SpectraSynq-K1-Firmware/ec33f5ee-3de9-426e-947b-161993bcf799/scratchpad
NAME=$1; SHA=$(/usr/bin/git -C $R rev-parse "$2^{commit}")
X=$SP/$NAME
if [ -e "$X" ]; then echo "exists: $X" >&2; exit 1; fi
mkdir -p $X
/usr/bin/git -C $R archive $SHA | tar -x -C $X
/usr/bin/git init -q --bare $X-git
echo $R/.git/objects > $X-git/objects/info/alternates
echo $SHA > $X-git/HEAD
GIT_DIR=$X-git GIT_WORK_TREE=$X GIT_INDEX_FILE=$X-git/index /usr/bin/git read-tree $SHA
mkdir -p $X/.pio/libdeps
for e in k1_hardware k1_main_rpl_show_bench k1_main_rpl_im69d k1_fe k1_fe_emu k1_main_rpl_emu k1_main_rpl_emu_tempo_probe k1_bench_im69d_led150; do
  if [ -d $R/.pio/libdeps/$e ]; then cp -Rc $R/.pio/libdeps/$e $X/.pio/libdeps/; else echo "no libdeps cache for $e" >&2; fi
done
GIT_DIR=$X-git GIT_WORK_TREE=$X GIT_INDEX_FILE=$X-git/index GIT_OPTIONAL_LOCKS=0 /usr/bin/git status --porcelain | head -5
echo "EXPORT $X = $SHA"
