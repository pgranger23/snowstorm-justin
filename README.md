# snowstorm-justin

SnowStorm-style DUNE production with justIN: one workflow covering a whole
detector-parameter space, where every file records the parameters it was
simulated with and anyone can recover them later.

Personal working repository — not a DUNE-official tool.

## The idea

A SnowStorm sample varies detector-physics parameters across files rather than
fixing them. The usual way to do that is to generate a grid of configurations,
write out one fcl per point, and submit one job cluster per point. This does it
with **one workflow and no configuration files**: each job derives its own
parameter point from a pure function of

    key = "<seed>/<stem>"

where `seed` is chosen once for the production and `stem` is the job's input
file name (or its Monte Carlo counter). Nothing is bookkept at submission time,
and because the workflow ID is deliberately *not* part of the key, re-running a
lost job or re-processing the same inputs months later reproduces the same
sample.

The thrown values end up in three places, which must always agree: the output
file name, the file's MetaCat metadata (so `where snowstorm.etau < 10000`
works), and the file's own art process history.

## Layout

```
bin/snowstorm_params.py     the throw: (seed, stem, dials) -> values, fcl overrides, JSON
bin/snowstorm_lookup.py     recover a file's parameters: from its name, MetaCat, or the file
bin/snowstorm_dials.py      the dial registry: resolve the hash in a file name
dials/                      versioned dial definitions; INDEX.md maps hash -> file
jobscripts/gen.jobscript    phase 1: generate the events once
jobscripts/snowstorm.jobscript  phase 2: g4 -> detsim -> reco1 -> reco2 with thrown parameters
submit/                     submission for both phases
tests/test_sampler.py       offline tests, no grid or network needed
docs/                       design notes, the full proposal, the per-event study
perevent/                   experimental: per-event variation (needs LArSoft changes)
```

Start with [TUTORIAL.md](TUTORIAL.md).

## Quick start

```bash
python3 tests/test_sampler.py                      # nothing installed, nothing submitted

# see what a job would throw, before submitting anything
python3 bin/snowstorm_params.py --seed my-2026a \
        --stem prodgenie_nu_dune10kt_1x2x6_000007_gen \
        --dials dials/recomb_lifetime_v1.json --json

# two jobs, one event each
SEED=my-2026a NJOBS=2 NUM_EVENTS=1 LIFETIME_DAYS=7 \
  OUTPUT_DATASET=snowstorm-test ./submit/submit_snowstorm.sh
```

## Status

Validated on the grid: justIN workflows 20169 (two jobs, three dials) and
20380 (one job, four dials, via the tutorial's own path). In both, the values
in MetaCat matched what the sampler predicted before submission, to the last
digit, and MQL range queries selected on them correctly. `config_dumper -P` on
a downloaded output agreed with both.

Not yet done: a run at production scale, and the per-event work in `perevent/`.
