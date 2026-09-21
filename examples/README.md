# Examples

## The whole integration, in three lines

The sampler emits **fcl override lines**. Making an existing art chain a
SnowStorm production is therefore: call the sampler, prepend its output to an
`#include` of the fcl you already use, run `lar` as before.

```bash
SSP="python3 snowstorm_params.py --seed $SEED --stem $stem --dials $DIALS"

{ echo '#include "standard_g4_dune10kt_1x2x6.fcl"'
  $SSP --stage g4
} > local_g4.fcl

lar -c local_g4.fcl -o out.root in.root
```

`$SSP --stage g4` prints exactly this, and nothing else:

```
# SnowStorm overrides, stage=g4, key=demo-2026/dune10kt_1x2x6_000101
services.LArG4Parameters.ModBoxA: 0.9089229805292603
services.LArG4Parameters.ModBoxB: 0.21092083229803535
```

[`minimal.jobscript`](minimal.jobscript) is a complete, runnable version for a
gen→g4→detsim chain. It is deliberately not atmospherics-specific.

## Adding a dial is a JSON block

Nothing in the sampler knows what a dial *means* — it knows an fcl path, an art
stage, and a prior. So any fcl parameter at any stage can be varied:

```json
"elecgain": {
  "fcl": "physics.producers.tpcrawdecoder.wcls_main.structs.elecGain",
  "stage": "detsim",
  "dist": "gaus",
  "nominal": 14.0,
  "sigma": 0.3,
  "clip": [12.5, 15.5]
}
```

Supported priors: `gaus` (with optional `clip`), `uniform`, `loguniform`.

Editing a dial file changes its hash, and the hash is in every output filename —
so a sample thrown from one set of priors can never be confused with another.
Add a new file rather than editing a published one; `dials/INDEX.md` is the
registry.

## Seeing the throw before spending anything

```bash
# what would counter 101 get?
python3 bin/snowstorm_params.py --seed my-2026a \
        --stem dune10kt_1x2x6_000101 --dials dials/recomb_lifetime_v1.json --json

# and the inverse, at analysis time, from the filename alone
python3 bin/snowstorm_lookup.py --from-name <file>.root \
        --seed my-2026a --dials dials/recomb_lifetime_v1.json
```

Full walkthrough, including submission and verification: [`../TUTORIAL.md`](../TUTORIAL.md).
