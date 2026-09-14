#!/usr/bin/env python3
"""
Offline tests for the sampler, the naming convention and the dial registry.
No LArSoft, no grid, no network: run with `python3 tests/test_sampler.py`.

These guard the properties the whole design rests on -- that a parameter point
is reproducible from (seed, stem), that it does not depend on anything else,
and that a file name plus a seed is enough to recover it.
"""

import json
import os
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "bin"))

from snowstorm_params import throw, dial_hash, seed_hash, job_key  # noqa: E402
from snowstorm_lookup import from_name, parse_name  # noqa: E402

DIALS = json.load(open(os.path.join(ROOT, "dials", "recomb_lifetime_v1.json")))
failures = []


def check(name, condition, detail=""):
    print(f"{'ok  ' if condition else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not condition:
        failures.append(name)


# --- the throw is a pure function of (seed, stem) ---------------------------
k = job_key("seed-a", "somefile_gen")
check("throw is deterministic",
      throw(k, "alpha", DIALS["alpha"]) == throw(k, "alpha", DIALS["alpha"]))

check("different seed gives a different point",
      throw(job_key("seed-a", "f"), "alpha", DIALS["alpha"])
      != throw(job_key("seed-b", "f"), "alpha", DIALS["alpha"]))

check("different input file gives a different point",
      throw(job_key("s", "file_A"), "alpha", DIALS["alpha"])
      != throw(job_key("s", "file_B"), "alpha", DIALS["alpha"]))

# The point of the seed+stem scheme: nothing else may enter. If a workflow ID
# ever creeps back into the key, this is what catches it.
check("key contains only seed and stem", job_key("s", "f") == "s/f")

# --- distributions ----------------------------------------------------------
for name, d in DIALS.items():
    v = [throw(job_key("dist-test", str(i)), name, d) for i in range(20000)]
    if d["dist"] == "gaus":
        check(f"{name} mean", abs(statistics.mean(v) - d["nominal"]) < 4 * d["sigma"] / 140,
              f"mean={statistics.mean(v):.6g} nominal={d['nominal']}")
        check(f"{name} sigma", abs(statistics.stdev(v) - d["sigma"]) < 0.05 * d["sigma"],
              f"sd={statistics.stdev(v):.6g} sigma={d['sigma']}")
        if "clip" in d:
            check(f"{name} within clip", min(v) >= d["clip"][0] and max(v) <= d["clip"][1])
    else:
        lo, hi = d["range"]
        check(f"{name} within range", min(v) >= lo and max(v) <= hi,
              f"[{min(v):.6g}, {max(v):.6g}]")

# --- file names round-trip --------------------------------------------------
seed, stem = "prod-2026a", "prodgenie_nu_dune10kt_1x2x6_000007_gen"
fname = f"snowstorm_{stem}_{dial_hash(DIALS)}_s{seed_hash(seed)}_reco2.root"
got_stem, got_dhash, got_shash = parse_name(fname)
check("name parses back to its stem", got_stem == stem, got_stem)
check("name carries the dial hash", got_dhash == dial_hash(DIALS))
check("name carries the seed hash", got_shash == seed_hash(seed))

key, vals = from_name(fname, DIALS, seed)
check("name + seed reproduce the throw",
      all(vals[n] == throw(job_key(seed, stem), n, d) for n, d in DIALS.items()))

# A PASS tag distinguishes a reprocessing without changing the parameters.
p_stem, _, _ = parse_name(f"snowstorm_{stem}_{dial_hash(DIALS)}_s{seed_hash(seed)}_v2_reco2.root")
check("PASS tag does not disturb parsing", p_stem == stem, p_stem)

# --- the guards refuse rather than answer wrongly ---------------------------
for label, args in (("wrong seed", (fname, DIALS, "not-the-seed")),
                    ("wrong dials", (fname, {**DIALS, "alpha": {**DIALS["alpha"], "sigma": 0.03}},
                                     seed))):
    try:
        from_name(*args)
        check(f"refuses {label}", False, "it answered instead of refusing")
    except SystemExit:
        check(f"refuses {label}", True)

# --- registry ---------------------------------------------------------------
out = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "snowstorm_dials.py"), "--list"],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
check("registry lists this dial file", dial_hash(DIALS) in out.stdout)

index = open(os.path.join(ROOT, "dials", "INDEX.md")).read()
regen = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "snowstorm_dials.py"), "--index"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True).stdout
check("INDEX.md is up to date", index == regen,
      "" if index == regen else "run bin/snowstorm_dials.py --index > dials/INDEX.md")

print()
if failures:
    print(f"{len(failures)} FAILED: {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")
