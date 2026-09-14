# Running a SnowStorm-style production — tutorial

How to produce a DUNE MC sample in which every file was simulated with a
different, recorded set of detector-physics parameters, using one justIN
workflow. No configuration grid, no per-point submission, no bookkeeping
database.

Everything below has been run. Workflow 20169 is the two-job reference
(PROPOSAL.md §6); workflow 20380 is this tutorial's own path, run end to end
with the four-dial `example/my_dials.json`.

---

## 0. What you need

- a DUNE account with justIN access, on a gpvm;
- about 15 minutes for the first (local) test;
- nothing else. The sampler is two Python files with no dependencies.

```bash
source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh
setup justin

htgettoken -a htvaultprod.fnal.gov -i dune   # bearer token, needed by RCDS
justin get-token                             # justIN session + x509 proxy
justin whoami                                # should print your name
```

Both tokens expire. `htgettoken` normally refreshes silently; `justin
get-token` asks you to visit a URL once every 7 days. **If `justin-cvmfs-upload`
ever fails with `Failed to upload ... to RCDS server`, it is almost always an
expired *bearer* token, not a justIN problem** — rerun `htgettoken`.

## 1. Choose a seed

Everything in a SnowStorm sample hangs off one string you pick:

```bash
export SEED=fdhd-recomb-2026a
```

The seed plus a job's input file name is the entire parameter throw. That is
what makes the sample reproducible: the justIN workflow ID is deliberately not
involved, so re-running a lost job, or re-processing the same inputs next year
in a different workflow, gives back *the same* parameter point. Record the seed
in your production notes — it also goes into every output file's metadata, and
a fingerprint of it goes into every file name, but the string itself is yours
to keep.

Use a fresh seed for a genuinely new sample; reuse one only when you mean "the
same sample again".

The flip side is worth knowing: because the seed and the input names fully
determine the output names, re-running a production with the same seed over the
same inputs produces files with *identical names*, which Rucio will refuse as
duplicates. That is the correct behaviour — the sample already exists — but if
you deliberately want a second copy (a reprocessing under a newer dunesw, say),
set `PASS=v2`. It is added to the output names and not to the throw, so the
parameters stay identical while the files are distinguishable.

## 2. Decide what to vary

`dials.json` is the whole parameter model. Each entry names the fcl parameter
to override, the stage whose fcl carries it, the art process that consumes it,
and how to throw it:

```json
"alpha": {
  "fcl": "services.LArG4Parameters.ModBoxA",
  "stage": "g4", "process": "G4",
  "dist": "gaus", "nominal": 0.93, "sigma": 0.02, "clip": [0.85, 1.01]
}
```

Distributions: `gaus` (with optional `clip`), `uniform`, `loguniform` (both
take `range`), and `fixed` (takes `value` — use it to pin a dial while varying
others, or to build a discrete grid instead of a continuous throw).

Definitions live in `dials/`, versioned, and are addressed by an 8-character
hash of their exact contents — the same hash that appears in every output file
name:

```bash
python3 bin/snowstorm_dials.py --list
python3 bin/snowstorm_dials.py --resolve e1d55d70    # what made this file?
```

To use your own set, add a *new* file rather than editing one:

```bash
cp dials/recomb_lifetime_v1.json dials/my_model_v1.json   # then edit
python3 bin/snowstorm_dials.py --index > dials/INDEX.md
```

Editing an existing definition changes its hash, which silently makes every
file that references the old hash unresolvable. The registry exists precisely
so that "keep your dial file forever" is not each user's problem.

`dials/recomb_lifetime_gain_v1.json` is a worked example that adds a fourth dial, the
WireCell electronics gain. It has been run: workflow 20380 produced a file
whose MetaCat record carries all four values, matching what
`snowstorm_params.py --key w20380-1` predicts before submission, to the last
digit:

```
snowstorm.alpha    : 0.9410196706894793     snowstorm.beta     : 0.21250866496998108
snowstorm.etau     : 24893.14769679222      snowstorm.elecgain : 13.73009230241109
snowstorm.key      : w20380-1               snowstorm.dial_hash: 93e410ac
``` Which parameters are reachable from fcl at all is
the subject of PROPOSAL.md §1 — the short version is that everything WireCell
declares as `std.extVar` works, and `shaping`, `postgain`, field responses and
noise spectra do not.

Two things to get right, because they are physics choices and not defaults:

- **the priors.** The σ values shipped here are reverse-engineered from the
  DetSuM grid spacing. Whatever you throw is what the analysis marginalises
  over, so agree them with the systematics group.
- **continuous or grid.** A continuous throw is what SnowStorm wants. A
  multi-fidelity surrogate wants repeated discrete points instead — use
  `"dist": "fixed"` and one workflow per point for that.

## 3. Look at the throw before spending anything

The sampler is a pure function of a key, so you can see exactly what any job
will get without running anything:

```bash
D=dials/recomb_lifetime_v1.json
S=prodgenie_nu_dune10kt_1x2x6_000007_gen          # an input file name, no .root
python3 bin/snowstorm_params.py --seed $SEED --stem $S --dials $D --json
python3 bin/snowstorm_params.py --seed $SEED --stem $S --dials $D --stage g4
python3 bin/snowstorm_params.py --seed $SEED --seed-hash
```

Output files are named
`snowstorm_<stem>_<dialhash>_s<seedhash>[_<pass>]_<stage>.root`, so a file
states which parameter model and which production made it without giving the
seed away.

Check the distributions are what you meant before submitting thousands of jobs:

```bash
python3 - <<'EOF'
import json, statistics
from snowstorm_params import throw
dials = json.load(open("my_dials.json"))
for name, d in dials.items():
    v = [throw(f"w1-{i}", name, d) for i in range(20000)]
    print(f"{name:10s} mean={statistics.mean(v):.6g} sd={statistics.stdev(v):.6g} "
          f"min={min(v):.6g} max={max(v):.6g}")
EOF
```

## 4. Run one job locally first

This is free and catches every configuration mistake. `justin-test-jobscript`
runs the jobscript inside the same container the grid uses:

```bash
SEED=$SEED ./gridtest/run_local_jobscript.sh
```

Expect `gen → g4 → detsim → reco1 → reco2`, each `exit code 0`, about five
minutes for one event, and at the end a printed sidecar:

```json
{ "metadata": { "snowstorm.key": "w1-1", "snowstorm.dial_hash": "e1d55d70",
                "snowstorm.alpha": 0.938..., "snowstorm.etau": 6422.97... } }
```

Note `justin-test-jobscript` always hands out counter `000001`, so a local test
exercises exactly one parameter point.

## 5. Generate the events once

A SnowStorm sample re-simulates the *same* events at many parameter points, so
generation is shared: do it once, keep the output, and run phase 2 over it as
many times as you like. This is cheaper, and it makes comparisons between
points cleaner, since the samples then differ only by the detector model.

```bash
NJOBS=20 NUM_EVENTS=50 OUTPUT_DATASET=my-gen-sample ./submit/submit_gen.sh
```

DUNE does not keep FD HD gen-stage files catalogued with disk replicas, so
there is generally nothing existing to run over — this phase is how you get an
input sample. Skip it only if you have gen files of your own already in
MetaCat.

## 6. Submit a small workflow

**Always start with two jobs.** The full production submission is the same
command with bigger numbers.

Over the gen sample you just made (the normal case):

```bash
SEED=$SEED NUM_EVENTS=-1 WALL_SECONDS=10000 RSS_MIB=4000 LIFETIME_DAYS=7 \
  MQL="files from usertests:my-gen-sample limit 2" \
  DIALS_FILE=$PWD/dials/recomb_lifetime_v1.json \
  OUTPUT_DATASET=snowstorm-test-dune10kt-1x2x6 \
  ./submit/submit_snowstorm.sh
```

Or generating from scratch inside the same job, with no phase 1:

```bash
SEED=$SEED NJOBS=2 NUM_EVENTS=1 LIFETIME_DAYS=7 \
  DIALS_FILE=$PWD/dials/recomb_lifetime_v1.json \
  OUTPUT_DATASET=snowstorm-test-dune10kt-1x2x6 \
  ./submit/submit_snowstorm.sh
```

`SEED` is required — the jobscript refuses to run without it, because a file
whose parameters cannot be re-derived is worse than no file.

It prints the workflow ID. What the script does for you:

- ships `snowstorm_params.py` and your dial file to cvmfs with
  `justin-cvmfs-upload`, and waits for them to appear. The returned path is
  content-addressed, so it doubles as a version stamp: one `FCL_DIR` means one
  exact parameter model;
- sends the output to a **Rucio dataset**, not to an `https://` scratch URL.
  This is not cosmetic. justIN only merges the `<file>.json` sidecar into
  MetaCat in the Rucio branch of `justin-wrapper-job`; an `https://`
  destination is a bare WebDAV PUT and **your parameters are silently thrown
  away**.

Watch it:

```bash
justin show-jobs --workflow-id <ID>
justin show-files --workflow-id <ID>
justin show-stage-outputs --workflow-id <ID> --stage-id 1
justin fetch-logs --workflow-id <ID> --jobsub-id <JOBSUB-ID>   # if one fails
```

justIN submits a few more jobs than counters; the extras exit immediately with
"Nothing to process". That is normal.

## 7. Check the metadata actually arrived

This is the step people skip and regret.

```bash
SEED=$SEED ./gridtest/verify_gridtest.sh <ID>
```

It finds the dataset and, for every file, prints the `snowstorm.*` metadata
MetaCat holds next to the values re-derived from the file name alone. They must
agree. For workflow 20169:

```
--- usertests:snowstorm_dune10kt_1x2x6_w20169_000002_e1d55d70_reco2.root
  MetaCat:    alpha 0.9202654607768902   beta 0.2123975827988098   etau 4844.2545735651665
  From name:  alpha 0.9202654607768902   beta 0.2123975827988098   etau 4844.2545735651665
```

## 8. Use the sample

The parameters are ordinary MetaCat fields, so they are queryable:

```bash
metacat query "files from usertests:<dataset> where snowstorm.etau < 10000"
metacat query "files from usertests:<dataset> where snowstorm.alpha > 0.94 \
               and snowstorm.etau > 20000"
justin show-replicas --mql "files from usertests:<dataset> where snowstorm.etau < 10000"
```

and a new workflow can take such a query as its `--mql` input, so a downstream
stage can select on the parameter point of its input files.

Three independent ways to ask what a file was simulated with, which should
always agree:

```bash
python3 bin/snowstorm_lookup.py --from-name snowstorm_..._e1d55d70_sf37942_reco2.root \
        --seed $SEED --dials dials/recomb_lifetime_v1.json
python3 bin/snowstorm_lookup.py --from-metacat usertests:snowstorm_..._reco2.root
python3 bin/snowstorm_lookup.py --from-file /path/to/downloaded.root \
        --dials dials/recomb_lifetime_v1.json
```

`--from-name` needs the seed, and refuses if the seed or the dial file does not
match the fingerprints in the name — it will not answer with wrong numbers.
`--from-metacat` needs nothing: the seed is recorded there.

The third reads the fcl out of the file's own process history. It uses
`config_dumper -P`; **never use `-S`**, which collapses all processes into one
block and will report the *nominal* value for a file that was genuinely varied
(demonstrated in PROPOSAL.md §5).

## 9. Scale up

Once two jobs work, the only changes are numbers:

```bash
SEED=$SEED LIFETIME_DAYS=30 \
  MQL="files from usertests:my-gen-sample" \
  DIALS_FILE=$PWD/dials/recomb_lifetime_v1.json \
  OUTPUT_DATASET=snowstorm-dune10kt-1x2x6 \
  JOBSCRIPT_GIT=pgranger23/snowstorm-justin/jobscripts/snowstorm.jobscript:v0.1.0 \
  ./submit/submit_snowstorm.sh
```

`JOBSCRIPT_GIT` makes justIN fetch the jobscript from GitHub at that tag rather
than from your working copy, so the workflow record states exactly which
version produced the sample. Use it for anything you intend to keep.

Measured on workflow 20169: one event through the full chain took ~380 s wall
and 1.9 GB peak RSS, so `--rss-mib 4000` is right and 4 GB slots are far more
plentiful than 8 GB ones. Size `--wall-seconds` from your own `NUM_EVENTS`
with margin; jobs that overrun are lost work.

Keep the dial file forever, or at least keep its hash: the file names record
which model produced them, and `snowstorm_lookup.py --from-name` refuses to
guess if you hand it a dial file whose hash does not match.

## Troubleshooting

| symptom | cause |
|---|---|
| `metacat` dies with `SyntaxError: future feature annotations is not defined` | `setup metacat` alone can leave an old `python3` first on PATH; `setup python v3_9_13` before it |
| `xrdcp` fails with `TLS error: resource temporarily unavailable` | that site's xroot door and the SL7 container's client disagree; try another replica, or fetch over https |
| `Failed to upload ... to RCDS server` | expired bearer token; rerun `htgettoken` |
| `justin` asks you to visit a URL | justIN session expired (7-day) |
| output files exist but have no `snowstorm.*` metadata | output went to an `https://` destination; use a Rucio dataset name |
| `--lifetime-days` error | required whenever any output goes to Rucio |
| `PROLOG blocks must be both contiguous and not nested` | a PROLOG-only `#include` placed after a non-prolog include |
| `config_dumper` reports nominal values for a varied file | `-S` instead of `-P` |
| jobs die at the g4 or detsim stage on the grid but work locally | usually memory: check `VmHWM` in the job log against `--rss-mib` |
| writes fail with "Disk quota exceeded" | `/exp/dune/app` is quota-limited; build and write output under `/exp/dune/data` |
