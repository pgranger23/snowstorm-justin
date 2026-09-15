#!/bin/bash
# Verify an atmnu HD workflow: for every CAF, compare the snowstorm.* metadata
# in MetaCat against the values re-derived from the file name plus the seed.
# Also reports the per-job wall time and RSS actually seen on the grid, which
# is what should size the next production.
#
# Usage: SEED=atmnu-hd-2026a ./gridtest/verify_atmnu_hd.sh <workflow-id>
set -o pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WF=${1:?usage: verify_atmnu_hd.sh <workflow-id>}
DIALS_FILE=${DIALS_FILE:-$ROOT/dials/recomb_lifetime_v1.json}
: "${SEED:?SEED must be set}"

source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh >/dev/null 2>&1
setup justin >/dev/null 2>&1
setup python v3_9_13 >/dev/null 2>&1   # metacat needs >=3.7; default python3 is 3.6
setup metacat >/dev/null 2>&1
export METACAT_SERVER_URL=${METACAT_SERVER_URL:-https://metacat.fnal.gov:9443/dune_meta_prod/app}
export METACAT_AUTH_SERVER_URL=${METACAT_AUTH_SERVER_URL:-https://metacat.fnal.gov:8143/auth/dune}

DS=$(justin show-stage-outputs --workflow-id "$WF" --stage-id 1 2>/dev/null \
     | awk 'NF>=4 && $(NF) ~ /-caf-/ {print $(NF-2)":"$NF}' | sort -u)
echo "=== CAF dataset(s): $DS"

nok=0; nbad=0
for d in $DS; do
  for f in $(metacat query "files from $d" 2>/dev/null); do
    name="${f#*:}"
    mc=$(python3 "$ROOT/bin/snowstorm_lookup.py" --from-metacat "$f" 2>/dev/null \
         | python3 -c "import json,sys; d=json.load(sys.stdin); print(' '.join('%s=%.17g'%(k.split('.')[1],v) for k,v in sorted(d.items()) if isinstance(v,float)))")
    nm=$(python3 "$ROOT/bin/snowstorm_lookup.py" --from-name "$name" --seed "$SEED" --dials "$DIALS_FILE" 2>/dev/null \
         | python3 -c "import json,sys; d=json.load(sys.stdin)['params']; print(' '.join('%s=%.17g'%(k,v) for k,v in sorted(d.items())))")
    if [ -n "$mc" ] && [ "$mc" = "$nm" ]; then
      echo "  OK   $name"; echo "       $mc"; nok=$((nok+1))
    else
      echo "  BAD  $name"; echo "       metacat: $mc"; echo "       name:    $nm"; nbad=$((nbad+1))
    fi
  done
done
echo "=== $nok verified, $nbad mismatched"

echo "=== grid cost actually seen (wall s, RSS GB, site):"
for d in $DS; do
  for f in $(metacat query "files from $d" 2>/dev/null); do
    metacat file show -m "$f" 2>/dev/null | python3 -c "
import sys,ast,re
for line in sys.stdin:
    if 'dune.workflow' in line:
        w = ast.literal_eval(line.split(':',1)[1].strip())
        print('  %5ds  %4.2f GB  %s' % (w['jobscript_real_seconds'],
              w['jobscript_max_rss_bytes']/1e9, w['site_name']))
"
  done
done
[ $nbad -eq 0 ]
