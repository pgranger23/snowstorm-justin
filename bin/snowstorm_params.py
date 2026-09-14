#!/usr/bin/env python3
"""
Derive a SnowStorm detector-parameter point from a job identifier and emit
the corresponding fcl overrides.

The mapping identifier -> parameter point is a pure function: given the same
identifier and the same dial definition, any machine reproduces the same
values. Nothing needs to be stored centrally at submission time, and a file
can always be re-derived from its own name.

The job key is "<seed>/<stem>": a seed the submitter chooses once for a
production, and a stem identifying the job -- the input file name when running
over pre-existing files, or the Monte Carlo counter when generating. It
deliberately does NOT contain the justIN workflow ID, so re-processing the same
input file in a new workflow, or re-running a lost job months later, reproduces
the same parameter point.

Usage:
  snowstorm_params.py --seed <seed> --stem <stem> --dials dials.json --stage g4
  snowstorm_params.py --key <job-key> --dials dials.json --stage g4     > overrides.fcl
  snowstorm_params.py --key <job-key> --dials dials.json --stage detsim > overrides.fcl
  snowstorm_params.py --key <job-key> --dials dials.json --json         > params.json

Per-event variation uses exactly the same throw with a longer key:

  snowstorm_params.py --key <job-key> --event 20000001:1:3 --dials dials.json --json

The event key is "<job-key>/<run>/<subrun>/<event>". Nothing else changes, so
one implementation covers both policies, and the values a job used for a given
event can be recomputed here from the event ID alone -- which is what makes
per-event variation bookkeepable. The C++ service
(larsim/DetectorVariation) builds the same string and hashes it the same way.
"""

import argparse
import hashlib
import json
import struct
import sys

# Each dial names the fcl parameter it drives, the stage that reads it, and a
# throwing prescription. sigma values follow the DetSuM convention
# (alpha: 0.93 +- 0.02, beta: 0.212 +- 0.002).
# "stage" is the job step whose fcl carries the override; "process" is the art
# process name that actually consumed it, which is what makes the value
# recoverable unambiguously from a downstream file's process history.
#
# Everything here is a plain fcl override. The WireCell dials work because the
# detsim jsonnet declares them as std.extVar and the fcl "structs" block binds
# them -- verified for lifetime/DL/DT/driftSpeed/elecGain/Nbit on
# dune10kt-1x2x6. Parameters NOT declared as extVar (shaping, postgain, field
# response and noise files) cannot be reached this way; see DESIGN.md.
DEFAULT_DIALS = {
    "alpha": {
        "fcl": "services.LArG4Parameters.ModBoxA",
        "stage": "g4", "process": "G4",
        "dist": "gaus", "nominal": 0.93, "sigma": 0.02, "clip": [0.85, 1.01],
    },
    "beta": {
        "fcl": "services.LArG4Parameters.ModBoxB",
        "stage": "g4", "process": "G4",
        "dist": "gaus", "nominal": 0.212, "sigma": 0.002, "clip": [0.204, 0.220],
    },
    "etau": {
        "fcl": "physics.producers.tpcrawdecoder.wcls_main.structs.lifetime",
        "stage": "detsim", "process": "detsim",
        "dist": "loguniform", "range": [3000.0, 35000.0],
    },
}

# Additional fcl-reachable WireCell dials, verified to propagate into the
# compiled config. Not enabled by default: the ranges below are placeholders
# and need agreeing with the systematics group before use.
OPTIONAL_DIALS = {
    "dl": {
        "fcl": "physics.producers.tpcrawdecoder.wcls_main.structs.DL",
        "stage": "detsim", "process": "detsim",
        "dist": "gaus", "nominal": 4.0, "sigma": 0.4, "clip": [2.0, 6.0],
    },
    "dt": {
        "fcl": "physics.producers.tpcrawdecoder.wcls_main.structs.DT",
        "stage": "detsim", "process": "detsim",
        "dist": "gaus", "nominal": 8.8, "sigma": 0.9, "clip": [5.0, 13.0],
    },
    "elecgain": {
        "fcl": "physics.producers.tpcrawdecoder.wcls_main.structs.elecGain",
        "stage": "detsim", "process": "detsim",
        "dist": "gaus", "nominal": 14.0, "sigma": 0.3, "clip": [12.5, 15.5],
    },
}


def dial_hash(dials):
    """Short stable fingerprint of a dial definition.

    Goes into the output file name so that a file always states which parameter
    model produced it. Without this, re-deriving values from a name is only
    correct as long as nobody ever edits the dial file -- which they will.
    """
    canon = json.dumps(dials, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()[:8]


def job_key(seed, stem):
    """The key a job throws from: the submitter's seed and the job's stem.

    Keeping the workflow ID out of this is the whole point -- the parameter
    point must be a property of (production, input file), not of which workflow
    happened to process it.
    """
    return f"{seed}/{stem}"


def seed_hash(seed):
    """Short fingerprint of the seed, carried in output file names.

    The seed itself is not in the name: it may be long, and a name is not a
    secret-keeping device. The fingerprint lets a lookup verify that the seed
    someone hands it is the one that actually produced the file, instead of
    silently returning wrong numbers.
    """
    return hashlib.sha256(str(seed).encode()).hexdigest()[:6]


def _uniform(key, salt):
    """Deterministic uniform on [0,1) from (key, salt). Stable across hosts."""
    digest = hashlib.sha256(f"{key}/{salt}".encode()).digest()
    # 53 bits -> exactly representable as a double, same recipe as random.random
    return (struct.unpack(">Q", digest[:8])[0] >> 11) * (2.0 ** -53)


def sobol_point(index, ndim, seed=0):
    """The index-th point of a scrambled Sobol sequence.

    Sobol covers the parameter space far more evenly than independent uniforms,
    which matters when the sample is used to fit a response surface. The cost is
    that the point depends on the *set* of dials: adding or reordering a dial
    changes every point. Hash-throwing (throw() below) is per-dial and does not
    have that property. Pick one deliberately and record it in the dial file.
    """
    from scipy.stats import qmc
    # Sobol's balance properties hold for the first 2^m points, so generate a
    # power-of-two block containing the index rather than index+1 points.
    m = max(1, (index + 1).bit_length())
    pts = qmc.Sobol(d=ndim, scramble=True, seed=seed).random_base2(m)
    return pts[index]


def throw(key, name, dial):
    dist = dial["dist"]
    if dist == "fixed":
        return float(dial["value"])
    if dist == "uniform":
        lo, hi = dial["range"]
        return lo + (hi - lo) * _uniform(key, name)
    if dist == "loguniform":
        import math
        lo, hi = dial["range"]
        return math.exp(math.log(lo) + (math.log(hi) - math.log(lo)) * _uniform(key, name))
    if dist == "gaus":
        import math
        # Box-Muller on two independent streams, so each dial stays reproducible
        # on its own even if other dials are added or removed later.
        u1 = max(_uniform(key, name + ":u1"), 1e-12)
        u2 = _uniform(key, name + ":u2")
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        val = dial["nominal"] + dial["sigma"] * z
        if "clip" in dial:
            val = min(max(val, dial["clip"][0]), dial["clip"][1])
        return val
    raise ValueError(f"unknown dist {dist!r} for dial {name!r}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--key", help="full job key, if you already have it")
    p.add_argument("--seed", help="production seed, chosen once by the submitter")
    p.add_argument("--stem", help="job stem: input file name (no .root) or MC counter")
    p.add_argument("--event", metavar="RUN:SUBRUN:EVENT",
                   help="throw for one event instead of for the file: appends "
                        "/run/subrun/event to the key, matching the C++ service")
    p.add_argument("--dials", help="JSON dial definition file (default: built-in)")
    p.add_argument("--stage", choices=["g4", "detsim"], help="emit fcl overrides for this stage")
    p.add_argument("--json", action="store_true", help="emit the parameter point as JSON")
    p.add_argument("--dial-hash", action="store_true",
                   help="print the dial-definition fingerprint and exit")
    p.add_argument("--seed-hash", action="store_true",
                   help="print the seed fingerprint and exit")
    args = p.parse_args()

    if args.seed_hash:
        if not args.seed:
            p.error("--seed-hash needs --seed")
        print(seed_hash(args.seed))
        return

    if not args.key:
        if not (args.seed and args.stem):
            p.error("give either --key, or --seed and --stem")
        args.key = job_key(args.seed, args.stem)

    dials = json.load(open(args.dials)) if args.dials else DEFAULT_DIALS

    if args.dial_hash:
        print(dial_hash(dials))
        return

    key = args.key
    if args.event:
        run, subrun, event = args.event.split(":")
        key = f"{key}/{int(run)}/{int(subrun)}/{int(event)}"

    values = {name: throw(key, name, d) for name, d in dials.items()}

    if args.json:
        json.dump({"snowstorm_key": key,
                   "dial_hash": dial_hash(dials),
                   "params": values}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return

    if not args.stage:
        p.error("need --stage or --json")

    print(f"# SnowStorm overrides, stage={args.stage}, key={key}")
    for name, d in dials.items():
        if d["stage"] == args.stage:
            print(f'{d["fcl"]}: {values[name]!r}')


if __name__ == "__main__":
    main()
