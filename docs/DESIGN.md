# SnowStorm with LArSoft + justIN: design options

Companion to `README.md`, which covers what Linyan/Sungbin's DetSuM workflow
does today. This document evaluates how to build on it.

Everything below marked "verified" was checked against real code or real
files; everything marked "proposal" is not implemented.

---

## 1. Two studies, not one

These need to be separated before choosing anything else, because they want
opposite sample designs:

- **Marginalisation (SnowStorm proper).** Train/evaluate on an ensemble whose
  detector parameters are smeared over their prior, so the result is robust to
  the systematic. Wants *independent* events at each throw.
- **Response surface / derivatives** (the surrogate model, and the natural
  stepping stone to your differentiable-simulator plan). Wants the *same*
  events at every throw, so that output differences are due to the parameter
  and not to simulation noise — "common random numbers". With CRN a finite
  difference is a usable derivative estimate; without it, it is mostly noise.

Their production uses *disjoint* GENIE file blocks per configuration
(`genie_1st_file_idx = index*10 + 9000` etc.), which is right for the first
and maximally wasteful for the second. The same justIN infrastructure serves
both — the difference is only whether the generator input is shared.

---

## 2. justIN implementation options

| Option | Shape | Verdict |
|---|---|---|
| **A** | Port as-is: one workflow per configuration | Reproduces the 145-submission bookkeeping problem. No. |
| **B** | One `--monte-carlo N` workflow, parameters thrown from the MC counter | **Default choice** for a fresh marginalised sample. |
| **C** | Multi-stage: gen as stage 1, g4→reco as stage 2 via `--output-pattern-next-stage` | Useful if generation is expensive and shared; adds moving parts. |
| **D** | `--mql` over an existing GENIE/gen dataset, throw keyed on the *input file name* | **Choice for CRN studies** and for re-simulating existing samples. |

B and D are the same jobscript; only the key differs (MC counter vs input file
name). `snowstorm.jobscript` already branches on `GEN_FCL` to cover both.

Notes that cost time if discovered late (all verified against
`/exp/dune/app/users/pgranger/dune-justin`):

- `--git-repo` does **not** deliver files to the jobscript. It is tarred,
  uploaded to RCDS, and the resulting path is read only by the dashboard for
  display. Worse, the Finder gates workflow startup on that upload. Ship code
  with `justin-cvmfs-upload` and pass the path via `--env`.
- `--env` values are emitted in **alphabetical order by name**, so one cannot
  reference another.
- `justin-test-jobscript` always hands out counter `000001`, so a test run
  exercises exactly one point of the parameter space.

---

## 3. Random values

Two independent randomness questions that are easy to conflate.

### 3a. The parameter throw

It must be a **deterministic function of job identity**, not a time-seeded
draw. If a job throws from `/dev/urandom`, the parameter point exists only in
whatever you managed to record, and a lost record is a lost file. Hashing
`(job key, dial name)` means the point is re-derivable from the file name
forever, and re-running a counter reproduces the configuration exactly.

`snowstorm_params.py` does this with SHA-256 per dial. Hashing *per dial*
(rather than drawing a vector) has a useful property: adding, removing or
reordering dials does not change the values of the existing ones.

**Sampling design.** Measured L2-star discrepancy, IID vs scrambled Sobol
(scipy is available in the dunesw environment — verified, 1.13.1):

| dials | N | IID | Sobol | gain |
|---|---|---|---|---|
| 3 | 2048 | 4.9e-3 | 5.7e-4 | 8.7× |
| 6 | 2048 | 2.7e-3 | 9.3e-4 | 2.9× |
| 10 | 2048 | 6.9e-4 | 4.9e-4 | 1.4× |

So Sobol is clearly worth it for a handful of dials and close to irrelevant
for a full high-dimensional SnowStorm. The catch: a Sobol point depends on the
*whole* dial set, so adding a dial later changes every point — the opposite of
the per-dial hash. Pick deliberately and record the choice in the dial file.

**The throw distribution is a prior.** Whatever is thrown is what gets
marginalised over, so it is a physics input and should be agreed with the
systematics group rather than inherited from a grid. The current σ values
(α ±0.02, β ±0.002) are reverse-engineered from the DetSuM grid spacing.

### 3b. The physics RNG (common random numbers)

Verified in `nurandom v1_12_00`, `PerEventPolicy.h`: the `perEvent` policy
with algorithm `EventTimestamp_v1` builds the seed by hashing the string

```
"Run: R Subrun: S Event: E Timestamp: T Process: P Module: M [Instance: I]"
```

It depends only on the event identity, process name and module label — **not**
on job identity, file, or processing order. So two jobs re-simulating the same
input events with different detector parameters get bit-identical random
streams. That is exactly common random numbers, available today with a fcl
one-liner:

```
services.NuRandomService.policy: "perEvent"
```

Caveats: the process name must be kept identical between runs; the event needs
a valid timestamp (it throws otherwise); `std::hash<std::string>` is
libstdc++-implementation-defined, so treat reproducibility as within-release.
Across dunesw the 38:2:1 split of `preDefinedSeed`:`random`:`perEvent` in the
fcls shows `perEvent` is supported but barely used — worth a heads-up to the
production group. `preDefinedSeed` also gives CRN but only if both jobs
process the identical event sequence, so it is more fragile.

Separately: whether WireCell seeds itself independently of the art random
service was **not** established and needs checking before trusting CRN through
detsim.

---

## 4. Keeping track of the parameters

Use more than one layer; they fail differently.

### Filename
Zero cost, survives everything, but encodes nothing queryable. Put the *key*
in the name, not the values — the values are then re-derivable, and the name
stays short.

### MetaCat — the real answer, with two traps

**Trap 1 (verified in `agents/justin-wrapper-job`).** The `<output>.json`
sidecar is merged into MetaCat only in the Rucio branch. A destination
starting with `https://` takes an earlier branch that is a bare WebDAV PUT
with no declaration at all. Writing to dCache scratch silently discards every
custom field. Give `--output-pattern` a plain dataset name.

**Trap 2 (verified against the production MetaCat server).**
`dune_mc.electron_lifetime` already exists — and is **string**-typed with
inconsistent values across existing files: `'10.4'`, `'35ms'`, `'3ms'`. Same
quantity, three formats, one with units baked into the string. It cannot
support a range query, so it is unusable for a continuous scan.

Numeric range queries do work (verified with `core.event_count`), and the
`dune_mc`, `detector`, `core` and `custom` categories are all `Restricted: no`
with no constraints — so new *numeric* keys can be added without any
server-side change. The ask to data management is therefore small and concrete:
agree numeric, unit-suffixed field names (e.g. `dune_mc.electron_lifetime_us`,
`dune_mc.recomb_modboxa`) rather than more free-form strings.

### In-file provenance — works, but only one way

Verified on a real 5-process file
(`.../cvn/atmnu_..._gen_g4_detsim_hitreco_reco2.root`):

- `config_dumper -S` prints **one** `LArG4Parameters` block for the whole
  file. In their setup the g4 fcl varies ModBoxA while the detsim fcl leaves
  it at nominal, so a single collapsed value is actively misleading.
- `config_dumper -P` prints **per-process** blocks (`GenieGen`, `G4`,
  `detsim`, `Reco1`, `Reco2`), each with its own service config. ModBoxA
  appears under `G4` (the value that mattered) *and* under `detsim` (nominal,
  meaningless), and `structs.lifetime` under `detsim`.

So provenance is fully recoverable, but only with `-P`, and only if the reader
knows which process each parameter is meaningful in. That is precisely why
"config_dumper works fine" is true and still not a *clear enough* solution.

### CAF
`SRGlobal` currently holds only `wgts` (a vector of `SRSystParamHeader`:
name/id/nshifts), which is built for *reweightable* systematics. A SnowStorm
parameter is not a weight — it is a coordinate of the file. There is no slot
for it.

Recommendation: store the values **per event**, not per file, despite the
redundancy. CAFs get concatenated, and a per-file global does not survive
`hadd` in a way that keeps the association. A few floats per record is
negligible.

Better still, CAFMaker can fill them automatically: art exposes the process
history, and each process's `ParameterSetID` resolves through
`fhicl::ParameterSetRegistry` (this is how `config_dumper` works). So the g4
stage's ModBoxA can be read straight out of the input file with no extra
bookkeeping — and retroactively, on samples that already exist.

---

## 5. LArSoft changes worth proposing

Ordered by value-to-effort.

**(a) Generic extra-metadata service — small, high value, useful beyond
SnowStorm.** Verified: art's `FileCatalogMetadata` has a *closed* fcl schema
(`checkSyntax`, `applicationFamily`, `applicationVersion`, `group`,
`processID`, `metadataFromInput`, `fileType`, `runType`), so arbitrary keys
cannot be set from fcl. But `addMetadata(key, value)` is a public C++ method
and **nothing in dunesw calls it**. A ~50-line service taking a fcl table of
key/value pairs and forwarding them would let any production put arbitrary
structured metadata into its files. This is the cleanest answer to "config
dumper isn't clear enough".

**(b) A `DetectorVariation` service that owns the throw — the nice solution.**
Give it the dial definitions and the job key; it throws at begin-job, exposes
the values to whoever needs them, and registers them through (a). The
generated-override-fcl step then disappears entirely: jobs are configured by
passing *one number*, not by writing fcl. This is what would make the workflow
genuinely easy for others to adopt.

**(c) Per-event variation — feasible, but not now.** Verified plumbing:
`LArG4Parameters` stores `double const fModBoxA` with only const accessors and
no setter; `IonAndScint::beginJob()` constructs `ISCalcCorrelated` once;
that constructor caches `fModBoxA`/`fModBoxB`, which are then used per deposit
in a two-line formula (`Xi = fModBoxB*dEdx/E; recomb = log(fModBoxA + Xi)/Xi`).
Because the formula already takes plain doubles, re-reading them per event is
a contained change. art services can drive it: `sPreProcessEvent` callbacks
exist and `NuRandomService` already registers one.

Two reasons to defer it anyway: the detsim electron lifetime lives inside
WireCell's jsonnet configuration, an entirely different code path, so you would
get per-event recombination and per-job lifetime; and per-event throwing breaks
the one-file-one-parameter-point model that makes catalogue-level tracking work
at all.

**(d) Raise the duplicated lifetime.** `services.DetectorPropertiesService.-
Electronlifetime` and `physics.producers.tpcrawdecoder.wcls_main.structs.-
lifetime` are independent, and the DetSuM fcls vary only the second while
leaving the first at nominal 10400 in every configuration. Any generic
"vary the electron lifetime" tooling has to know about both, and the asymmetry
should be an explicit physics choice.

---

## 6. Other considerations

- **Reco must stay nominal.** If reconstruction and calibration used the thrown
  value, the systematic would be partly calibrated away and the study would
  understate it. Their setup happens to do the right thing (the
  `DetectorPropertiesService` lifetime stays at nominal through detsim and
  reco), but it looks incidental rather than intended — worth confirming with
  Linyan.
- **Cost structure.** Generation can be shared across throws; g4, detsim and
  reco cannot. Reusing pre-made GENIE files, as they do, is the right call —
  and is also what makes option D and CRN possible.
- **Do not ship `fhicl-dump` output.** Verified that a 3-line override
  reproduces their 157 KB dump exactly, and dunesw already ships
  `protodunevd_detsim_nodiffusion_35mslifetime.fcl` as precedent. Dumps also
  freeze the configuration against one release, so the sample cannot be
  extended under a newer dunesw without regenerating everything.
- **Content-addressed dial definitions.** `justin-cvmfs-upload` returns a
  hash-derived path, so the RCDS path doubles as a version stamp: one
  `FCL_DIR` means exactly one parameter model. Worth recording in the metadata.
