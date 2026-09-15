#!/bin/bash
# SnowStorm production: DUNE FD HD 1x2x6 atmospheric neutrinos, gen -> CAF.
#
#   canary:      SEED=... NJOBS=3 NUM_EVENTS=20 KEEP_RECO2=1 ./submit/submit_atmnu_hd.sh
#   production:  SEED=... NJOBS=1000 NUM_EVENTS=100 OFFSET=100 ./submit/submit_atmnu_hd.sh
#
# OFFSET keeps a canary and a production run from colliding: both start their
# justIN counters at 1, which would give duplicate file names and duplicate
# subrun numbers.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ -z "${SEED:-}" ]; then
  echo "SEED must be set: it is what makes the parameter points reproducible." >&2
  echo 'e.g. SEED=atmnu-hd-2026a ./submit/submit_atmnu_hd.sh' >&2
  exit 1
fi

NJOBS=${NJOBS:-1000}
NUM_EVENTS=${NUM_EVENTS:-100}
OFFSET=${OFFSET:-0}
SAMPLE=${SAMPLE:-dune10kt_1x2x6}
DUNE_VERSION=${DUNE_VERSION:-v10_16_00d00}
DUNE_QUALIFIER=${DUNE_QUALIFIER:-e26:prof}

# Measured on HD atmospheric events: T(n) ~ 245 s + 45 s/event, so 100 events
# is ~1.3 h. 6 h of wall gives ~4.5x headroom for the slow tail (the VD
# production lost files to hours-long anglereco on huge showers).
WALL_SECONDS=${WALL_SECONDS:-21600}
RSS_MIB=${RSS_MIB:-4000}          # measured VmHWM 1.84 GB, VmPeak 3.98 GB at reco2
MAX_DISTANCE=${MAX_DISTANCE:-30}
LIFETIME_DAYS=${LIFETIME_DAYS:-90}
SCOPE=${SCOPE:-usertests}
DIALS_FILE=${DIALS_FILE:-$ROOT/dials/recomb_lifetime_v1.json}
DIALS_NAME=$(basename "$DIALS_FILE")
OUTPUT_DATASET=${OUTPUT_DATASET:-snowstorm-atmnu-hd-1x2x6}
JOBSCRIPT_GIT=${JOBSCRIPT_GIT:-}

set +eu
if ! command -v justin >/dev/null 2>&1; then
  source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh >/dev/null 2>&1
  setup justin
fi
set -eu

justin get-token

CFGTAR=$(mktemp -d)/snowstorm.tar
tar cf "$CFGTAR" -C "$ROOT/bin" snowstorm_params.py
tar rf "$CFGTAR" -C "$(cd "$(dirname "$DIALS_FILE")" && pwd)" "$DIALS_NAME"
tar rf "$CFGTAR" -C "$ROOT/fcl" caf_atmo_hd.fcl
FCL_DIR=$(justin-cvmfs-upload "$CFGTAR")
echo "config uploaded to $FCL_DIR"
a=2; until stat "$FCL_DIR" >/dev/null 2>&1; do echo "waiting for RCDS..."; sleep $a; a=$((a<60?a*2:60)); done

if [ -n "$JOBSCRIPT_GIT" ]; then
  JOBSCRIPT_ARGS=(--jobscript-git "$JOBSCRIPT_GIT")
else
  JOBSCRIPT_ARGS=(--jobscript "$ROOT/jobscripts/snowstorm_atmnu_hd.jobscript")
fi

# Keeping reco2 is for canaries only: ~13.8 MB/event against ~86 kB/event of
# CAFs, so a full production would move terabytes for no analysis benefit.
# justin-test-jobscript accepts only --jobscript/--monte-carlo/--mql/--env;
# the resource and output options are workflow-level and it rejects them.
ENV_ARGS=(
  --env FCL_DIR="$FCL_DIR"
  --env DIALS="$DIALS_NAME"
  --env SEED="$SEED"
  --env NUM_EVENTS="$NUM_EVENTS"
  --env OFFSET="$OFFSET"
  --env SAMPLE="$SAMPLE"
  --env DUNE_VERSION="$DUNE_VERSION"
  --env DUNE_QUALIFIER="$DUNE_QUALIFIER"
)
[ -n "${KEEP_RECO2:-}" ] && ENV_ARGS+=(--env KEEP_RECO2=1)

if [ "${TEST:-0}" = "1" ]; then
  exec justin-test-jobscript \
    --jobscript "$ROOT/jobscripts/snowstorm_atmnu_hd.jobscript" \
    --monte-carlo 1 \
    "${ENV_ARGS[@]}"
fi

OUT_ARGS=(--output-pattern "*_caf.root:${OUTPUT_DATASET}-caf"
          --output-pattern "*_flatcaf.root:${OUTPUT_DATASET}-flatcaf"
          --output-pattern "*.logs.tgz")
[ -n "${KEEP_RECO2:-}" ] && OUT_ARGS+=(--output-pattern "*_reco2.root:${OUTPUT_DATASET}-reco2")

justin simple-workflow \
  --monte-carlo "$NJOBS" \
  "${JOBSCRIPT_ARGS[@]}" \
  "${ENV_ARGS[@]}" \
  --rss-mib "$RSS_MIB" \
  --wall-seconds "$WALL_SECONDS" \
  --max-distance "$MAX_DISTANCE" \
  --lifetime-days "$LIFETIME_DAYS" \
  --scope "$SCOPE" \
  "${OUT_ARGS[@]}" \
  --description "SnowStorm atmnu HD 1x2x6 seed=$SEED: per-file thrown detector parameters"
