#!/bin/bash
# Run the real jobscript locally, inside the same container justIN uses, on one
# Monte Carlo counter. Costs nothing and catches configuration mistakes before
# any job is submitted.
#
# Usage:  SEED=my-2026a ./gridtest/run_local_jobscript.sh
#         SEED=... NEV=1 DIALS_FILE=dials/my_model_v1.json ./gridtest/run_local_jobscript.sh
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${SEED:?SEED must be set}"
NEV=${NEV:-1}
DIALS_FILE=${DIALS_FILE:-$ROOT/dials/recomb_lifetime_v1.json}

source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh >/dev/null 2>&1
setup justin >/dev/null 2>&1

# Ship the sampler exactly as a real submission would, so the local run
# exercises the RCDS path too.
CFGTAR=$(mktemp -d)/snowstorm.tar
tar cf "$CFGTAR" -C "$ROOT/bin" snowstorm_params.py
tar rf "$CFGTAR" -C "$(cd "$(dirname "$DIALS_FILE")" && pwd)" "$(basename "$DIALS_FILE")"
FCL_DIR=$(justin-cvmfs-upload "$CFGTAR") || exit 1
echo "sampler uploaded to $FCL_DIR"
a=2; until stat "$FCL_DIR" >/dev/null 2>&1; do echo "waiting for RCDS..."; sleep $a; a=$((a<60?a*2:60)); done

justin-test-jobscript \
  --jobscript "$ROOT/jobscripts/snowstorm.jobscript" \
  --monte-carlo 1 \
  --env FCL_DIR="$FCL_DIR" \
  --env DIALS="$(basename "$DIALS_FILE")" \
  --env SEED="$SEED" \
  --env NUM_EVENTS="$NEV" \
  --env GEN_FCL=prodgenie_nu_dune10kt_1x2x6.fcl
echo "=== justin-test-jobscript exit=$?"
