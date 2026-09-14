# SnowStorm with justIN — refined proposal

Scope, per your constraints: **one parameter point per file** (not per event),
**reproducible seeds** driving the parameter values, **easy retrieval** of the
parameters for any file, and **no significant codebase changes**.

Headline: no LArSoft or dunereco change is needed. Everything below is fcl
overrides generated inside the job plus two small standalone scripts.

---

## 1. Where the parameters live — including the WireCell question

You were right to be unsure about WireCell. The answer is better than expected.

### LArSoft services — ordinary fcl override
```
services.LArG4Parameters.ModBoxA: 0.9377      # g4 stage
services.LArG4Parameters.ModBoxB: 0.2120      # g4 stage
```

### WireCell — also an ordinary fcl override

The detsim jsonnet declares its tunables as `std.extVar`, and the fcl
`wcls_main.structs` block binds them. So WireCell parameters are reachable
from fcl exactly like LArSoft ones:
```
physics.producers.tpcrawdecoder.wcls_main.structs.lifetime: 21968.0
```
This is not a hack — dunesw already ships
`protodunevd_detsim_nodiffusion_35mslifetime.fcl` doing precisely this.

**extVars declared in the dune10kt-1x2x6 sim chain** (verified by grepping the
whole `wire-cell-cfg` tree):

| extVar | What | Status |
|---|---|---|
| `lifetime`, `DL`, `DT`, `driftSpeed`, `G4RefTime` | drift physics | already in the production `structs` block — safe |
| `elecGain` (`pgrapher/dune/params.jsonnet`), `Nbit` | electronics gain, ADC bits | **confirmed working** in a real detsim job (§5); v10_16_00d00 already ships both in the production `structs` block |
| `apa_sparsity`, `engine`, `use_dnnroi`, `dnn_model`, `signal_output_form` | plumbing, not physics | leave alone |

Verified end-to-end by compiling the real graph twice with `jsonnet`:
`lifetime` 10400→5000 changed `"lifetime": 10400000→5000000`, and
`elecGain` 14.0→13.3 changed `"gain": 2.2430e-12→2.1309e-12` (ratio 1.0526 =
14.0/13.3, exactly as expected).

### What is *not* fcl-reachable, and the escape hatch

`shaping` (2.2 µs), `postgain`, the field-response files and the noise spectra
are hardcoded in `params.jsonnet` with **no** `extVar`. They cannot be set from
fcl.

They can still be varied with zero codebase change, because of how WireCell
builds its jsonnet search path (`util/src/Persist.cxx`):

```cpp
// Loading: 1) cwd, 2) passed in paths 3) environment
m_load_paths.push_back(boost::filesystem::current_path());
...
// load paths into jsonnet backwards to counteract its reverse ordering
for (auto pit = m_load_paths.rbegin(); pit != m_load_paths.rend(); ++pit)
```

Two things follow. Raw `jsonnet -J` is **last-wins** (confirmed with a minimal
test); WireCell deliberately reverses that to restore intuitive first-wins for
`WIRECELL_PATH`. And **the current working directory has the highest priority
of all**. So in a justIN job you simply write a modified
`pgrapher/experiment/dune10kt-1x2x6/params.jsonnet` into the workspace and it
shadows the cvmfs copy — no env var juggling.

Verified by shadowing that file and recompiling: `"shaping": 2200 → 3300`.
(Caveat: verified with the `jsonnet` CLI mimicking the documented path order;
worth confirming once inside a real detsim job.)

Recommendation: start with the fcl-reachable dials only. Keep the shadowing
trick in reserve — it works, but it pins you to one release's jsonnet.

---

## 2. Reproducible seeds → parameter values

The rule that makes everything else easy: **the parameter point is a pure
function of the job's identity, computed in the job.** Nothing is decided at
submission time, and nothing needs a central registry.

```
key   = "w<justIN workflow id>-<MC counter>"     # or the input file name
value = InverseCDF_dial( SHA256(key + "/" + dial_name) )
```

Consequences that matter in practice:

- Re-running a counter reproduces the identical configuration, forever.
- The parameter point of any file is recoverable from its **name alone**, with
  no file access, no database and no network.
- Hashing **per dial** means adding, removing or reordering dials leaves the
  existing dials' values untouched.
- No submission-time bookkeeping: one workflow covers the whole space, versus
  the 145 separate `jobsub` submissions in the DetSuM setup.

The dial definitions live in a small JSON file (fcl path, which process
consumes it, distribution, nominal, σ or range). Its SHA-256 fingerprint is
carried in every output file name, so a file always states which parameter
model produced it — otherwise re-deriving values from a name is only correct
until someone edits the dial file.

Distributions are inverse-CDF from a uniform, so a dial can be Gaussian,
uniform, log-uniform or fixed without touching the machinery. Verified over
20k throws: α mean 0.93019 σ 0.02000, β mean 0.212014 σ 0.002002.

---

## 3. Retrieving the parameters for a file

`snowstorm_lookup.py` implements three independent routes. They should always
agree; if they disagree you want to know.

**Route 1 — from the file name.** Offline, instant.
```
$ snowstorm_lookup.py --from-name snowstorm_dune10kt_1x2x6_w1234_000042_e1d55d70_reco2.root
{"snowstorm_key": "w1234-42", "params": {"alpha": 0.9376770655050063, ...}}
```
Refuses to answer if the supplied dial file does not match the hash in the name.

**Route 2 — from MetaCat.** This is the one that supports bulk selection
(*"every file with lifetime < 6000 µs"*). The job writes a `<output>.json`
sidecar which justIN merges into the file's MetaCat record.

Two traps, both verified:
- The sidecar is merged **only for Rucio-managed outputs**. An `https://`
  destination is a bare WebDAV PUT with no declaration at all, so writing to
  dCache scratch silently discards every field. Give `--output-pattern` a plain
  dataset name.
- Do **not** reuse `dune_mc.electron_lifetime`. It exists, but is string-typed
  with inconsistent production values (`'10.4'`, `'35ms'`, `'3ms'`) and cannot
  be range-queried. Write numeric `snowstorm.*` keys instead. Numeric range
  queries do work, and the categories are unrestricted so no admin action is
  needed.

**Route 3 — from the file itself.** Ground truth, works on any file including
ones made before this tooling existed.
```
$ snowstorm_lookup.py --from-file .../gen_g4_detsim_hitreco_reco2.root
{"processes_in_file": ["G4","GenieGen","Reco1","Reco2","detsim"],
 "params": {"alpha": {"value": 0.93,   "process": "G4"},
            "beta":  {"value": 0.212,  "process": "G4"},
            "etau":  {"value": 10400.0,"process": "detsim"}}}
```
This uses `config_dumper -P`, **never `-S`**. `-S` collapses all processes into
a single block, so a parameter left at nominal in a later stage silently
overwrites the value the earlier stage really used — exactly the failure mode
here, since the detsim fcl carries a nominal `ModBoxA` that means nothing.
That distinction is why "config_dumper works fine" is true but not a *clear
enough* answer on its own.

---

## 4. What this needs from the codebase

Nothing, for the dials above. That is the main refinement versus my earlier
answer: drop the `DetectorVariation` service and per-event variation ideas —
they were solving a problem you do not have.

Two things remain worth raising with Dom and Laura, but neither blocks you:

- **Agree numeric metadata field names** (`..._us` etc.) rather than more
  free-form strings. Cheap, and fixes a real existing wart.
- **Optional, ~50 lines:** art's `FileCatalogMetadata` has a closed fcl schema
  but a public `addMetadata(key, value)` C++ API that **nothing in dunesw
  calls**. A tiny service exposing it would put arbitrary structured metadata
  inside the art file, so the values would survive independently of the
  catalogue. Nice-to-have, not required.

One thing worth telling the production group regardless: `perEvent` seeding
(`services.NuRandomService.policy: "perEvent"`) makes the random streams depend
only on event identity, not on job or ordering. Re-simulating the same events
with different parameters then differs *only* by the detector change, which is
what turns a finite difference into a usable derivative. Only 1 dunesw fcl uses
it today versus 38 using `preDefinedSeed`.

---

## 5. Local validation (done)

A 1-event `gen -> g4 -> detsim` chain was run under dunesw v10_16_00d00 with
four dials thrown (alpha, beta, etau, elecgain). All three stages exited 0; the
whole chain took about two minutes. Every dial round-tripped exactly:

```
  alpha     thrown=0.9179414797708435   recovered=0.9179414797708435   process=G4      OK
  beta      thrown=0.21156617993791269  recovered=0.21156617993791269  process=G4      OK
  etau      thrown=8401.647272447504    recovered=8401.647272447504    process=detsim  OK
  elecgain  thrown=14.165367634187529   recovered=14.165367634187529   process=detsim  OK
```

This settles the one open question: `structs.elecGain` **does** bind. In
v10_16_00d00 the `dunefd_horizdrift_1x2x6_sim_nfsp` prolog already ships
`elecGain`, `Nbit` and `use_dnnroi` in the `structs` block, so the cwd-shadowing
fallback is not needed for these dials.

It also produced a sharper version of the `config_dumper` warning. The g4 stage
genuinely ran with `ModBoxA = 0.9179414797708435`, and `config_dumper -S`
reported `ModBoxA: 9.3e-1` — the **nominal** value — because the file also
carries a `SinglesGen` process whose `LArG4Parameters` sits at nominal. `-S`
does not merely lose process attribution, it silently returns the wrong number.
Anyone auditing a SnowStorm file with `-S` would conclude the parameters were
never varied. Only `-P` is trustworthy.

Reproduce with `localtest/run_test.sh`.

## 6. Grid validation (done)

justIN workflow **20169**: two jobs, one event each, `--monte-carlo 2`,
`--scope usertests`, outputs to a Rucio-managed dataset (never an `https://`
scratch URL — see §3). Both jobs ran the full `gen -> g4 -> detsim -> reco1 ->
reco2` chain, one at NIKHEF and one at Manchester, ~380 s wall and 1.9 GB peak
RSS each. This is what it demonstrated:

**Two counters give two genuinely different parameter points.** Nothing was
bookkept at submission time; each job derived its own point from its counter.

| | counter 000001 | counter 000002 |
|---|---|---|
| key | `w20169-1` | `w20169-2` |
| alpha | 0.9468692482669397 | 0.9202654607768902 |
| beta | 0.21035842031779187 | 0.2123975827988098 |
| etau | 32295.866944698395 | 4844.2545735651665 |

**The sidecar survives into MetaCat.** Each reco2 file carries numeric
`snowstorm.alpha/beta/etau` plus `snowstorm.key` and `snowstorm.dial_hash`.
MetaCat accepts the previously unused `snowstorm.` category with no admin
action: its validator skips keys whose category has no registered ancestor.

**The parameters are queryable, which was the whole point.** MQL range queries
partition the two files correctly on every dial, and compose with replica
lookup — `justin show-replicas --mql "files from <dataset> where
snowstorm.etau < 10000"` returns the low-lifetime file and its RSE URL. That is
analysis-time selection without opening a single file.

**All three retrieval routes agree, to the last digit.** For counter 000002,
MetaCat, re-derivation from the file name, and `config_dumper -P` on the
downloaded grid file itself all give alpha 0.9202654607768902, beta
0.2123975827988098, etau 4844.2545735651665 — the last one attributing alpha
and beta to process `G4` and etau to `detsim` out of a five-process history.

A second single-job workflow, **20380**, repeated this through the tutorial's
own path with a four-dial model (`example/my_dials.json`, adding the WireCell
`elecGain`): the file name carries the new dial hash `93e410ac`, and all four
values in MetaCat match what the sampler predicts for key `w20380-1` before
submission. Changing the parameter model costs one edited JSON file and
nothing else — no fcl regeneration, no new workflow code.

Reproduce with `gridtest/submit_gridtest.sh` then `gridtest/verify_gridtest.sh
<workflow-id>`; `gridtest/run_local_jobscript.sh` runs the same jobscript
locally in justIN's container first, which is the cheap way to catch mistakes.

## 7. Before submitting at scale

Decide the priors with the systematics group. The current σ values are
reverse-engineered from the DetSuM grid spacing, and whatever is thrown is what
gets marginalised over.
