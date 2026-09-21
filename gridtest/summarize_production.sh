#!/bin/bash
# End-of-production report: completeness, parameter coverage, cost and size.
#
# Coverage is computed by re-deriving each file's throw from its NAME, which
# needs no per-file metadata query -- the point of putting the stem and the
# dial/seed fingerprints in the name.
#
# Usage: SEED=atmnu-hd-2026a ./gridtest/summarize_production.sh <workflow-id>
set -o pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WF=${1:?usage: summarize_production.sh <workflow-id>}
DIALS_FILE=${DIALS_FILE:-$ROOT/dials/recomb_lifetime_v1.json}
: "${SEED:?SEED must be set}"

source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh >/dev/null 2>&1
setup justin >/dev/null 2>&1
setup python v3_9_13 >/dev/null 2>&1
setup metacat >/dev/null 2>&1
export METACAT_SERVER_URL=${METACAT_SERVER_URL:-https://metacat.fnal.gov:9443/dune_meta_prod/app}
export METACAT_AUTH_SERVER_URL=${METACAT_AUTH_SERVER_URL:-https://metacat.fnal.gov:8143/auth/dune}

CAF_DS=$(justin show-stage-outputs --workflow-id "$WF" --stage-id 1 2>/dev/null \
         | awk 'NF>=4 && $(NF) ~ /-caf-/ {print $(NF-2)":"$NF}' | head -1)
FLAT_DS=$(justin show-stage-outputs --workflow-id "$WF" --stage-id 1 2>/dev/null \
         | awk 'NF>=4 && $(NF) ~ /-flatcaf-/ {print $(NF-2)":"$NF}' | head -1)
echo "CAF dataset:     $CAF_DS"
echo "flatCAF dataset: $FLAT_DS"

echo "=== counters"
justin show-files --workflow-id "$WF" 2>/dev/null | awk '{print $3}' | sort | uniq -c
echo "=== size"
for d in "$CAF_DS" "$FLAT_DS"; do metacat query -s "files from $d" 2>/dev/null | head -2; done

echo "=== parameter coverage (re-derived from file names, no metadata queries)"
metacat query "files from $CAF_DS" 2>/dev/null \
  | sed 's/.*://; s/_[0-9a-f]\{8\}_s[0-9a-f]\{6\}.*//; s/^snowstorm_//' > /tmp/_stems.$$
python3 - "$SEED" "$DIALS_FILE" /tmp/_stems.$$ <<'PYEOF'
import sys, json, statistics as st, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))), 'bin'))
sys.path.insert(0, 'bin')
from snowstorm_params import throw, job_key
seed, dialfile, stemfile = sys.argv[1], sys.argv[2], sys.argv[3]
dials = json.load(open(dialfile))
stems = [l.strip() for l in open(stemfile) if l.strip()]
print(f"  files: {len(stems)}   unique parameter points: {len(set(stems))}")
for name, d in dials.items():
    v = [throw(job_key(seed, s), name, d) for s in stems]
    print(f"  {name:6s} mean={st.mean(v):.6g} sd={st.pstdev(v):.4g} "
          f"range=[{min(v):.6g}, {max(v):.6g}]")
PYEOF
rm -f /tmp/_stems.$$
