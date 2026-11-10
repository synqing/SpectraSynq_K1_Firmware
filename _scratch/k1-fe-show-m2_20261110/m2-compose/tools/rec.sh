#!/bin/zsh
# rec.sh NAME CMD... — run once, record command line, combined output and exit code to raw/NAME.log
name=$1; shift
log=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-compose/raw/$name.log
{ print -r -- "\$ ${(q)@}"; "$@" 2>&1; print -r -- "exit $?"; } > $log
/bin/cat $log
