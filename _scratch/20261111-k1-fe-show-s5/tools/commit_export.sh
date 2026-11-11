#!/bin/bash
# Commit an export onto a branch with a private index (handover §6). Never touches the shared checkout.
# usage: commit_export.sh <export dir> <parent sha> <branch> <message file> [create]
#   Prints the diff stat against the parent (READ IT), then the new commit id.
#   "create" makes a new branch at the commit; otherwise the branch must currently be at <parent>.
set -euo pipefail
R=$HOME/SpectraSynq_K1_Firmware
X=$1; P=$(/usr/bin/git -C $R rev-parse "$2^{commit}"); B=$3; MSG=$4; MODE=${5:-}
export GIT_INDEX_FILE=$(mktemp -u /private/tmp/claude-501/-Users-spectrasynq-SpectraSynq-K1-Firmware/ec33f5ee-3de9-426e-947b-161993bcf799/scratchpad/idx.XXXXXX)
GG=(/usr/bin/git --git-dir=$R/.git --work-tree=$X)
"${GG[@]}" read-tree $P
"${GG[@]}" add -A -- SPECTRASYNQ_K1_FIRMWARE platformio.ini scripts tools tests docs
echo "--- diff --stat vs parent $P"
"${GG[@]}" diff --cached --stat $P | tail -40
T=$("${GG[@]}" write-tree)
C=$("${GG[@]}" commit-tree $T -p $P -F $MSG)
if [ "$MODE" = "create" ]; then
  /usr/bin/git -C $R update-ref refs/heads/$B $C ""
else
  /usr/bin/git -C $R update-ref refs/heads/$B $C $P
fi
rm -f $GIT_INDEX_FILE
echo $C > $X-git/HEAD
GIT_DIR=$X-git GIT_WORK_TREE=$X GIT_INDEX_FILE=$X-git/index /usr/bin/git read-tree $C
echo "COMMIT $C on $B (parent $P)"
