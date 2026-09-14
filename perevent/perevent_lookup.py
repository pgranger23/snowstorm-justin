#!/usr/bin/env python3
"""
Recover the per-event detector parameters used to produce an art file.

The per-file workflow puts one parameter point in the file name and in MetaCat.
Per-event variation cannot do that -- there is no single value -- so the
provenance has to come from somewhere else. It already does:

  * the DetectorVariation service configuration (job key, policy, dial
    definitions) is part of the art process history, recoverable with
    `config_dumper -P` like any other service;
  * the throw is a pure function of that key and the event ID.

So every event's parameters are recomputable from the file alone: no new data
product, no new metadata field, no bookkeeping database. This script does that
and, given the job's own log, checks the two agree.

Usage:
  perevent_lookup.py --file g4.root                 # dump per-event values
  perevent_lookup.py --file g4.root --log g4.log    # and check against the job
"""

import argparse
import re
import subprocess
import sys

sys.path.insert(0, "/exp/dune/app/users/pgranger/snowstorm_justin")
from snowstorm_params import throw  # noqa: E402


def service_config(path):
    """Pull the DetectorVariation service block out of the process history."""
    out = subprocess.run(["config_dumper", "-P", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if out.returncode != 0:
        raise SystemExit(f"config_dumper failed: {out.stderr.strip()[:300]}")

    lines = out.stdout.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^\s*DetectorVariation:\s*\{", line):
            block, depth = [], 0
            for l in lines[i:]:
                depth += l.count("{") - l.count("}")
                block.append(l)
                if depth <= 0:
                    break
            return parse_block(block)
    raise SystemExit("no DetectorVariation service block in the process history")


def parse_block(block):
    """Minimal fhicl-dump reader: enough for key/policy/dials."""
    text = "\n".join(block)
    key = re.search(r'key:\s*"([^"]+)"', text)
    policy = re.search(r'policy:\s*"([^"]+)"', text)
    dials = {}
    for m in re.finditer(r"(\w+):\s*\{([^{}]*)\}", text):
        name, body = m.group(1), m.group(2)
        if "dist" not in body:
            continue
        d = {"dist": re.search(r'dist:\s*"(\w+)"', body).group(1)}
        for field in ("nominal", "sigma"):
            v = re.search(rf"{field}:\s*([-\d.eE+]+)", body)
            if v:
                d[field] = float(v.group(1))
        for field, out_key in (("clip", "clip"), ("range", "range")):
            arr = re.search(rf"{field}:\s*\[([^\]]*)\]", body)
            if arr:
                d[out_key] = [float(x) for x in arr.group(1).replace(",", " ").split()]
        dials[name] = d
    return (key.group(1) if key else None,
            policy.group(1) if policy else None,
            dials)


def event_ids(path):
    """Event IDs straight out of the file."""
    import ROOT
    f = ROOT.TFile.Open(path)
    tree = f.Get("Events")
    ids = []
    for i in range(tree.GetEntries()):
        tree.GetEntry(i)
        aux = tree.EventAuxiliary
        ids.append((aux.run(), aux.subRun(), aux.event()))
    return ids


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--log", help="job log, to check the recomputed values against")
    args = p.parse_args()

    key, policy, dials = service_config(args.file)
    print(f"# key={key} policy={policy} dials={sorted(dials)}")

    logged = {}
    if args.log:
        for line in open(args.log):
            m = re.search(
                r"DVSUMMARY .*event=(\d+) key=(\S+) alpha=([\d.eE+-]+) beta=([\d.eE+-]+)", line)
            if m:
                logged[int(m.group(1))] = (m.group(2), float(m.group(3)), float(m.group(4)))

    bad = 0
    for run, subrun, event in event_ids(args.file):
        ekey = key if policy == "perFile" else f"{key}/{run}/{subrun}/{event}"
        vals = {n: throw(ekey, n, d) for n, d in dials.items()}
        line = f"{run}:{subrun}:{event}  " + "  ".join(f"{n}={vals[n]!r}" for n in sorted(vals))
        if event in logged:
            lkey, la, lb = logged[event]
            ok = (lkey == ekey and la == vals.get("alpha") and lb == vals.get("beta"))
            bad += not ok
            line += "   " + ("OK" if ok else f"MISMATCH job had key={lkey} alpha={la} beta={lb}")
        print(line)

    if args.log:
        print("all events match" if not bad else f"{bad} events MISMATCH")
        return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main() or 0)
