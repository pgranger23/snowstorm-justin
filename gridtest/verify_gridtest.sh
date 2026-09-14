#!/bin/bash
# Verify a finished workflow: for every output file, compare the snowstorm.*
# metadata MetaCat holds against the values re-derived from the file name and
# the seed. Agreement means counter -> throw -> fcl -> sidecar -> MetaCat is
# self-consistent and the sample is recoverable.
#
# Usage:  SEED=my-2026a ./gridtest/verify_gridtest.sh <workflow-id> [dials-file]
set -o pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WF=${1:?usage: verify_gridtest.sh <workflow-id> [dials-file]}
DIALS_FILE=${2:-$ROOT/dials/recomb_lifetime_v1.json}
: "${SEED:?SEED must be set}"

source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh >/dev/null 2>&1
setup justin >/dev/null 2>&1
setup python v3_9_13 >/dev/null 2>&1   # metacat needs >=3.7; the default python3 is 3.6
setup metacat >/dev/null 2>&1
export METACAT_SERVER_URL=${METACAT_SERVER_URL:-https://metacat.fnal.gov:9443/dune_meta_prod/app}
export METACAT_AUTH_SERVER_URL=${METACAT_AUTH_SERVER_URL:-https://metacat.fnal.gov:8143/auth/dune}

echo "=== stage outputs"
justin show-stage-outputs --workflow-id "$WF" --stage-id 1

# show-stage-outputs prints: (flags) <scope> <pattern> <dataset>
DS=$(justin show-stage-outputs --workflow-id "$WF" --stage-id 1 2>/dev/null \
     | awk 'NF>=4 {print $(NF-2)":"$NF}' | sort -u)

for d in $DS; do
  echo "=== files in $d"
  metacat query "files from $d" 2>&1 | head -20
done

echo "=== per-file cross-check"
for d in $DS; do
  for f in $(metacat query "files from $d" 2>/dev/null); do
    case "$f" in *reco2.root) ;; *) continue ;; esac
    echo "--- $f"
    echo "  MetaCat:";   python3 "$ROOT/bin/snowstorm_lookup.py" --from-metacat "$f" | sed 's/^/    /'
    echo "  From name:"; python3 "$ROOT/bin/snowstorm_lookup.py" --from-name "${f#*:}" \
                             --seed "$SEED" --dials "$DIALS_FILE" | sed 's/^/    /'
  done
done
