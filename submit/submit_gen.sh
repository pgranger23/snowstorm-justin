#!/bin/bash
# Phase 1 of a SnowStorm production: generate the events once, into a Rucio
# dataset that phase 2 then runs over many times with different detector
# parameters.
#
# Usage:  NJOBS=20 NUM_EVENTS=50 OUTPUT_DATASET=my-gen-sample ./submit_gen.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

NJOBS=${NJOBS:-20}
NUM_EVENTS=${NUM_EVENTS:-50}
SAMPLE=${SAMPLE:-dune10kt_1x2x6}
GEN_FCL=${GEN_FCL:-prodgenie_nu_dune10kt_1x2x6.fcl}
DUNE_VERSION=${DUNE_VERSION:-v10_16_00d00}
DUNE_QUALIFIER=${DUNE_QUALIFIER:-e26:prof}
RSS_MIB=${RSS_MIB:-4000}
WALL_SECONDS=${WALL_SECONDS:-20000}
LIFETIME_DAYS=${LIFETIME_DAYS:-30}
SCOPE=${SCOPE:-usertests}
OUTPUT_DATASET=${OUTPUT_DATASET:-snowstorm-gen-dune10kt-1x2x6}
JOBSCRIPT_GIT=${JOBSCRIPT_GIT:-}

if ! command -v justin >/dev/null 2>&1; then
  set +eu
  source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh >/dev/null 2>&1
  setup justin
  set -eu
fi

justin get-token

if [ -n "$JOBSCRIPT_GIT" ]; then
  JOBSCRIPT_ARGS=(--jobscript-git "$JOBSCRIPT_GIT")
else
  JOBSCRIPT_ARGS=(--jobscript "$ROOT/jobscripts/gen.jobscript")
fi

JUSTIN_CMD="justin"
if [ "${TEST:-0}" = "1" ]; then JUSTIN_CMD="justin-test-jobscript"; NJOBS=1; fi

$JUSTIN_CMD simple-workflow \
  --monte-carlo "$NJOBS" \
  "${JOBSCRIPT_ARGS[@]}" \
  --env NUM_EVENTS="$NUM_EVENTS" \
  --env GEN_FCL="$GEN_FCL" \
  --env SAMPLE="$SAMPLE" \
  --env DUNE_VERSION="$DUNE_VERSION" \
  --env DUNE_QUALIFIER="$DUNE_QUALIFIER" \
  --rss-mib "$RSS_MIB" \
  --wall-seconds "$WALL_SECONDS" \
  --lifetime-days "$LIFETIME_DAYS" \
  --scope "$SCOPE" \
  --output-pattern "*_gen.root:$OUTPUT_DATASET" \
  --output-pattern "*.logs.tgz" \
  --description "SnowStorm phase 1: shared generation for $SAMPLE"
