#!/usr/bin/env python3
"""
Recover the detector-physics parameters used to simulate a given file.

Three independent routes, in increasing order of cost and decreasing order of
convenience. They should always agree; if they do not, something is wrong and
you want to know.

  1. --from-name   Re-derive from the stem encoded in the file name plus the
                   production seed. Offline, instant, needs no access to the
                   file at all. The name carries fingerprints of both the dial
                   file and the seed, so a wrong dial file or a wrong seed is
                   refused rather than silently answered with wrong numbers.

  2. --from-metacat  Read the snowstorm.* fields declared in MetaCat.
                   Needs network + metacat setup. This is the route that
                   supports bulk queries ("give me every file with
                   lifetime < 6000 us").

  3. --from-file   Read the fcl actually used, out of the art file's own
                   process history, with config_dumper -P.
                   Slowest, but it is ground truth and works on any file,
                   including ones produced before this tooling existed.

Usage:
  snowstorm_lookup.py --from-name snowstorm_<stem>_<dialhash>_s<seedhash>_reco2.root \
                      --seed <seed> --dials dials.json
  snowstorm_lookup.py --from-metacat usertests:snowstorm_..._reco2.root
  snowstorm_lookup.py --from-file  /path/to/file.root --dials dials.json
"""

import argparse
import json
import re
import subprocess
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from snowstorm_params import throw, dial_hash, seed_hash, job_key  # noqa: E402

# snowstorm_<stem>_<dialhash>_s<seedhash>[_<pass>][_<stage>].root
#
# The stem may itself contain underscores (it is usually an input file name),
# so the name is parsed from the right: find the s<6 hex> token whose left
# neighbour is an 8-hex dial hash, and everything between "snowstorm" and that
# pair is the stem.
SEED_HASH_RE = re.compile(r"^s[0-9a-f]{6}$")
DIAL_HASH_RE = re.compile(r"^[0-9a-f]{8}$")


def parse_name(fname):
    base = fname.rsplit("/", 1)[-1]
    if base.endswith(".root"):
        base = base[:-5]
    parts = base.split("_")
    if not parts or parts[0] != "snowstorm":
        raise SystemExit(f"not a snowstorm file name: {fname}")
    for i in range(len(parts) - 1, 1, -1):
        if SEED_HASH_RE.match(parts[i]) and DIAL_HASH_RE.match(parts[i - 1]):
            return "_".join(parts[1:i - 1]), parts[i - 1], parts[i][1:]
    raise SystemExit(f"file name does not carry dial and seed fingerprints: {fname}")


def params_from_key(key, dials):
    return {name: throw(key, name, d) for name, d in dials.items()}


def from_name(fname, dials, seed):
    stem, want_dhash, want_shash = parse_name(fname)

    got_dhash = dial_hash(dials)
    if want_dhash != got_dhash:
        raise SystemExit(
            f"dial file mismatch: name says {want_dhash}, given dial file hashes to {got_dhash}.\n"
            f"Use the archived dial file for that hash, or the values will be wrong.")

    got_shash = seed_hash(seed)
    if want_shash != got_shash:
        raise SystemExit(
            f"seed mismatch: name says {want_shash}, given seed hashes to {got_shash}.\n"
            f"That seed did not produce this file.")

    key = job_key(seed, stem)
    return key, params_from_key(key, dials)


def from_metacat(did):
    out = subprocess.run(
        ["metacat", "file", "show", "--json", "--metadata", did],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if out.returncode != 0:
        raise SystemExit(f"metacat failed: {out.stderr.strip()}")
    md = json.loads(out.stdout).get("metadata", {})
    got = {k: v for k, v in md.items() if k.startswith("snowstorm.")}
    if not got:
        raise SystemExit(f"no snowstorm.* metadata on {did} "
                         "(was it uploaded to Rucio-managed storage?)")
    return got


def from_file(path, dials):
    """Ground truth: pull each dial's value out of the process that actually used it.

    config_dumper -P is required, not -S: -S collapses every process into one
    block, so a parameter left at nominal in a later stage silently overwrites
    the value the earlier stage really used.
    """
    out = subprocess.run(["config_dumper", "-P", path],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if out.returncode != 0:
        raise SystemExit(f"config_dumper failed: {out.stderr.strip()[:300]}")

    # Split into per-process blocks, keyed by the process name at column 0.
    blocks, current = {}, None
    for line in out.stdout.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*): \{", line)
        if m:
            current = m.group(1)
            blocks[current] = []
        elif current:
            blocks[current].append(line)

    found = {}
    for name, d in dials.items():
        leaf = d["fcl"].rsplit(".", 1)[-1]
        proc = d.get("process")           # which process this dial is meaningful in
        for pname, lines in blocks.items():
            if proc and pname.lower() != proc.lower():
                continue
            for line in lines:
                m = re.match(rf"^\s*{re.escape(leaf)}:\s*(\S+)\s*$", line)
                if m:
                    found[name] = {"value": float(m.group(1)), "process": pname}
                    break
            if name in found:
                break
    missing = set(dials) - set(found)
    if missing:
        print(f"warning: not found in process history: {sorted(missing)}",
              file=sys.stderr)
    return found, sorted(blocks)


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-name")
    p.add_argument("--seed", help="production seed (required with --from-name)")
    g.add_argument("--from-metacat")
    g.add_argument("--from-file")
    p.add_argument("--dials", default="dials.json")
    args = p.parse_args()

    if args.from_metacat:
        json.dump(from_metacat(args.from_metacat), sys.stdout, indent=2)
    else:
        dials = json.load(open(args.dials))
        if args.from_name:
            if not args.seed:
                p.error("--from-name needs --seed")
            key, vals = from_name(args.from_name, dials, args.seed)
            json.dump({"snowstorm_key": key, "params": vals}, sys.stdout, indent=2)
        else:
            vals, procs = from_file(args.from_file, dials)
            json.dump({"processes_in_file": procs, "params": vals},
                      sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
