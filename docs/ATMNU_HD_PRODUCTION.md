# SnowStorm atmospheric production — DUNE FD HD 1x2x6

1000 files x 100 events = 100k atmospheric neutrino events, each file simulated
at its own detector-parameter point and delivered as CAFs.

## Measured cost

dunesw v10_16_00d00, geometry v6, 10 events, one core:

| stage | wall (10 ev) | marginal | output/event |
|---|---|---|---|
| gen | 74 s | 3.6 s | 12 kB |
| g4 | 125 s | 5.0 s | 6.2 MB |
| **detsim** | **397 s** | **~34 s** | 11.6 MB |
| reco1 | 27 s | ~0.7 s | 11.8 MB |
| reco2 (atmos) | 55 s | ~1.5 s | 13.8 MB |
| CAF | 13 s | ~0.4 s | 86 kB |
| total | 691 s | ~45 s | |

`T(n) ~ 245 s + 45 s * n` — predicted 695 s at n=10 against 691 s measured.
detsim is 75% of the marginal cost.

At 100 events/job that is **~1.3 h/job**, so the full 1000-file production is
**~1300 core-hours** and about **9 GB** of CAFs. Keeping reco2 instead would
have cost ~2.8 TB, which is why only the CAFs are kept.

`--wall-seconds 21600` (6 h) gives ~4.5x headroom. That margin is not padding:
the previous VD production lost 12 files to events that spent *hours* in
`anglereco` on large showers, and two older 20-event HD files differ by 2.2x in
size per event, so the per-event cost has a long tail that 10 events cannot
measure.

## Configuration

All stages run at the release-default geometry (**v6**):

```
prodgenie_atmnu_max_weighted_randompolicy_dune10kt_1x2x6.fcl
standard_g4_dune10kt_1x2x6.fcl
standard_detsim_dune10kt_1x2x6.fcl
standard_reco1_dune10kt_1x2x6.fcl
standard_reco2_atmos_dune10kt_1x2x6.fcl
fcl/caf_atmo_hd.fcl          (standard_cafmaker + IsAtmoCVN: true)
```

Three things that will break a job if changed:

- **Do not use the `_geov5` variants.** `reco2_atmos_dune10kt_1x2x6_geov5.fcl`
  forces geometry v5 while the standard chain is v6, and the job aborts with
  "Geometry used for run ... is incompatible with the one configured".
  Verified by running it.
- **`standard_cafmaker_dune10kt_1x2x6.fcl` needs `IsAtmoCVN: true`.** Without
  it the CAFMaker segfaults on the first event of an atmospheric reco2 file.
  With it, output matches the `cafmaker_atmos_..._runreco-nuenergy-nuangular`
  variant byte for byte.
- **reco2 already runs energy and angular reco** (`ereconumu`, `energyrecnumu`,
  CVN), so the CAF stage is pure packaging at 0.4 s/event.

## Reproducibility

The parameter point is a pure function of `(SEED, stem)` where the stem is the
job's counter — the workflow ID is not involved, so re-running a counter in a
later workflow gives the same parameters.

The **events** are not reproducible: the generator uses `randompolicy`
(`random_NuRandomService`), so seeds come from the OS. This is a deliberate
choice. The consequence is that paired sampling — the same events re-simulated
at a second parameter point, giving derivatives with the Monte Carlo noise
cancelling — is not available for this sample. Switching the generator seed to
a counter-derived value would enable it later at no cost.

`OFFSET` shifts the counter, and must differ between a canary and the
production run: both start their justIN counters at 1, which would otherwise
produce duplicate file names *and* duplicate subrun numbers. The previous VD
production lost its canary to exactly that subrun collision.

## Dials

`dials/recomb_lifetime_v1.json` (hash `e1d55d70`): ModBoxA and ModBoxB at g4,
WireCell electron lifetime at detsim, Gaussian/Gaussian/log-uniform.

Two open choices, both one file away and both recorded in the file names via
the dial hash:

- the priors are reverse-engineered from the DetSuM grid spacing and should be
  agreed with the systematics group;
- throwing **wide uniform** instead of Gaussian would let the sample be
  importance-reweighted to revised priors later without regenerating. For a
  1300 core-hour investment that is probably the better trade.
