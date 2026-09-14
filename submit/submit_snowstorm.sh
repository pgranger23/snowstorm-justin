#!/bin/bash
# Submit a SnowStorm-style DUNE FD HD 1x2x6 production to justIN.
#
# One workflow covers the whole parameter space: every job throws its own
# detector-parameter point from its Monte Carlo counter, so there is no
# per-configuration submission and no configuration grid to maintain.
#
# Two modes:
#   MC generation:  NJOBS=<n>            (generate events from scratch)
#   pre-existing:   MQL="files from ..."  (run over files already in MetaCat;
#                   cheaper, since generation is shared across throws)
#
# SEED is required in both. It is the only thing tying a file to its parameter
# point, together with the file's own name -- so the same inputs plus the same
# seed reproduce the sample exactly, in any workflow, at any time.
#
# Usage:  SEED=mysample-2026a ./submit_snowstorm.sh
#         SEED=... MQL="files from dune:all where ... limit 10" ./submit_snowstorm.sh
#         SEED=... TEST=1 ./submit_snowstorm.sh   (justin-test-jobscript, one job)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

# Run the jobscript straight from GitHub by tag, so the sample records which
# version produced it and nobody has to copy files around:
#   JOBSCRIPT_GIT=pgranger23/snowstorm-justin/jobscripts/snowstorm.jobscript:v0.1.0
JOBSCRIPT_GIT=${JOBSCRIPT_GIT:-}

if [ -z "${SEED:-}" ]; then
  echo "SEED must be set: it is what makes the sample reproducible." >&2
  echo 'e.g. SEED=fdhd-recomb-2026a ./submit_snowstorm.sh' >&2
  exit 1
fi

NJOBS=${NJOBS:-2000}
MQL=${MQL:-}
NUM_EVENTS=${NUM_EVENTS:-50}
DUNE_VERSION=${DUNE_VERSION:-v10_16_00d00}
DUNE_QUALIFIER=${DUNE_QUALIFIER:-e26:prof}

RSS_MIB=${RSS_MIB:-4000}
WALL_SECONDS=${WALL_SECONDS:-40000}
MAX_DISTANCE=${MAX_DISTANCE:-30}
LIFETIME_DAYS=${LIFETIME_DAYS:-30}

# Outputs go to Rucio-managed storage, NOT to an https:// scratch URL.
# This is not a stylistic choice: justin-wrapper-job only calls
# updateMetadataTmp() -- the function that merges the <file>.json sidecar into
# MetaCat -- in the Rucio branch. An https:// destination is a bare WebDAV PUT
# and the thrown parameters would never be catalogued.
OUTPUT_DATASET=${OUTPUT_DATASET:-snowstorm-dune10kt-1x2x6}
SAMPLE=${SAMPLE:-dune10kt_1x2x6}
GEN_FCL=${GEN_FCL:-prodgenie_nu_dune10kt_1x2x6.fcl}
SCOPE=${SCOPE:-usertests}

# Which dial definition to ship. Point DIALS_FILE at your own copy to change
# the parameter model; its content determines the dial hash that ends up in
# every output file name, so two different dial files can never be confused.
DIALS_FILE=${DIALS_FILE:-$ROOT/dials/recomb_lifetime_v1.json}
DIALS_NAME=$(basename "$DIALS_FILE")

if ! command -v justin >/dev/null 2>&1; then
  set +eu
  source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh >/dev/null 2>&1
  setup justin
  set -eu
fi

justin get-token

# Ship the sampler and dial definition to the grid via RCDS.
# The returned path is content-addressed, so it doubles as a version stamp for
# the dial definition: a given FCL_DIR always means one exact parameter model.
CFGTAR=$(mktemp -d)/snowstorm.tar
tar cf "$CFGTAR" -C "$ROOT/bin" snowstorm_params.py
tar rf "$CFGTAR" -C "$(cd "$(dirname "$DIALS_FILE")" && pwd)" "$DIALS_NAME"
FCL_DIR=$(justin-cvmfs-upload "$CFGTAR")
echo "sampler uploaded to $FCL_DIR"
a=2; until stat "$FCL_DIR" >/dev/null 2>&1; do echo "waiting for RCDS..."; sleep $a; a=$((a<60?a*2:60)); done

if [ -n "$JOBSCRIPT_GIT" ]; then
  JOBSCRIPT_ARGS=(--jobscript-git "$JOBSCRIPT_GIT")
else
  JOBSCRIPT_ARGS=(--jobscript "$ROOT/jobscripts/snowstorm.jobscript")
fi

JUSTIN_CMD="justin"
if [ "${TEST:-0}" = "1" ]; then
  # Note: justin-test-jobscript always hands out counter 000001, so a test run
  # only ever exercises one point of the parameter space.
  JUSTIN_CMD="justin-test-jobscript"
  NJOBS=1
fi

# --monte-carlo invents counters; --mql takes real input files. In MQL mode the
# jobscript must not be given GEN_FCL, so that it uses the file justIN hands it
# and derives the throw from that file's name.
# Note the ${x[@]+"${x[@]}"} idiom below: under `set -u`, expanding an empty
# array is an error in bash before 4.4, which the gpvms still run.
if [ -n "$MQL" ]; then
  INPUT_ARGS=(--mql "$MQL")
  GEN_ARGS=()
else
  INPUT_ARGS=(--monte-carlo "$NJOBS")
  GEN_ARGS=(--env GEN_FCL="$GEN_FCL")
fi

$JUSTIN_CMD simple-workflow \
  "${INPUT_ARGS[@]}" ${GEN_ARGS[@]+"${GEN_ARGS[@]}"} \
  "${JOBSCRIPT_ARGS[@]}" \
  --env FCL_DIR="$FCL_DIR" \
  --env DIALS="$DIALS_NAME" \
  --env NUM_EVENTS="$NUM_EVENTS" \
  --env DUNE_VERSION="$DUNE_VERSION" \
  --env DUNE_QUALIFIER="$DUNE_QUALIFIER" \
  --env SEED="$SEED" \
  --env SAMPLE="$SAMPLE" \
  ${PASS:+--env PASS="$PASS"} \
  --rss-mib "$RSS_MIB" \
  --wall-seconds "$WALL_SECONDS" \
  --max-distance "$MAX_DISTANCE" \
  --lifetime-days "$LIFETIME_DAYS" \
  --scope "$SCOPE" \
  --output-pattern "*_reco2.root:$OUTPUT_DATASET" \
  --output-pattern "*.logs.tgz" \
  --description "SnowStorm $SAMPLE seed=$SEED: per-file thrown detector parameters"
