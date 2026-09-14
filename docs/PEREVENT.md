# Per-event detector variation — feasibility

The per-file workflow (PROPOSAL.md, validated on the grid as workflow 20169)
gives every *file* one parameter point. This note answers the next question:
can a single file carry a *different* parameter point per event, and if so what
happens to the bookkeeping?

Short answer: yes for the g4-stage recombination dials, with a ~20-line hook
in larsim plus a service; yes for the WireCell electron lifetime too, but by a
different and less obvious route, and it has not been prototyped here. The
bookkeeping problem has a clean answer that requires no new data product and no
new catalogue field.

---

## 1. Why a service is the right shape

`LArG4Parameters` is a plain art service holding `double const fModBoxA` with
no setter, and even if it had one it would not help: `IonAndScint::beginJob()`
constructs `ISCalcCorrelated` once, and that constructor *caches* ModBoxA and
ModBoxB (dividing ModBoxB by the argon density). The per-deposit calculation
then uses the cached doubles. So the value that matters is frozen at begin-job,
one level below the service, and any per-event scheme has to reach it.

art does not support reconfiguring a service per event. What it does support is
a service that *recomputes* per event: `ActivityRegistry::sPreProcessEvent`
fires before each event, and `NuRandomService` already uses exactly this
mechanism. That is the hook the prototype uses.

## 2. What the prototype does

In `dev/srcs/larsim` (larsim v10_10_00, matching dunesw v10_16_00d00):

- **`larsim/DetectorVariation/`** — a new service holding the job key, the
  policy (`perFile` or `perEvent`) and the dial definitions. On every event it
  rethrows each dial from the key `"<jobkey>/<run>/<subrun>/<event>"`.
  The throw is SHA-256 based and *bit-for-bit identical to the Python sampler*
  (`snowstorm_params.py --event RUN:SUBRUN:EVENT`), which is what makes the
  values recomputable offline.
- **`ISCalc::SetRecombModBox(A, B)`** — a virtual with an empty default, so
  models that do not support variation are untouched; `ISCalcCorrelated`
  overrides it and re-applies the density division.
- **`IonAndScint::produce()`** — three lines: if the service is configured and
  defines `alpha`/`beta`, push this event's values into the algorithm.

Nothing else in larsim changes. Without the service in the fcl the module
behaves exactly as the release does. One gap on purpose: `ISCalcSeparate`
caches ModBoxA/B the same way and would need the same override to be complete
(§7); the DUNE FD chain uses `Correlated`, so the prototype does not.

## 3. The WireCell half — feasible, not prototyped

The electron lifetime is not a LArSoft parameter at all; it is
`Drifter.lifetime` inside WireCell's own configuration, applied per depo as
`Q *= exp(-t_drift/lifetime)` in `Gen::Drifter::transport()` (diffusion widths
depend on drift time and DL/DT, not on the lifetime, so the two are separable).

WireCell builds its graph once per job: `WireCellToolkit_module` constructs the
`wcls_main` tool in its constructor, and `WCLS::process(event)` only runs the
already-built graph. So there is no configuration hook per event — but there is
an *event* hook. `WCLS::process()` calls `visit(event)` on every registered
"inputer" **before** running the graph:

```cpp
void wcls::WCLS::process(art::Event& event) {
  for (auto iaev : m_inputers) iaev->visit(event);   // <-- here
  m_wcmain();
  for (auto iaev : m_outputers) iaev->visit(event);
}
```

`wcls::IArtEventVisitor` is a WCT component like any other, so a visitor can
reach the Drifter through the toolkit's own factory —
`WireCell::Factory::find_tn<IConfigurable>("Drifter")` — and call `configure()`
on it with a new lifetime before each event's graph run. That is roughly 50
lines in larwirecell and **no change to WireCell itself**.

Two details make it slightly more than trivial:

- `Drifter::configure()` starts with `reset()` and rebuilds `m_xregions` from
  the configuration, throwing if `xregions` is absent. So the visitor must be
  handed the *whole* drifter configuration, not just the lifetime. In a real
  implementation the jsonnet already has that object and can pass it to the
  visitor by reference. A three-line upstream change — keep the existing
  xregions when the new configuration omits them — would let the visitor send
  `{lifetime: x}` alone, and is worth asking WireCell for.
- Reconfiguring mid-job is only safe at an event boundary, which is exactly
  where the visitor runs (the graph is flushed by then).

The alternative — set WireCell's lifetime to infinity and attenuate the
SimEnergyDeposits upstream in LArSoft — is *not* recommended even though it
needs no WireCell-side code: it would have to reproduce the Drifter's own
response-plane geometry to get the drift time right, and it would lose the
binomial fluctuation on the absorbed charge that the Drifter applies.

## 4. Bookkeeping — the part that actually decides this

Per-event variation destroys the property that makes the per-file design
tidy: a file no longer *has* a parameter point, so it cannot be named after
one, and MetaCat range queries can no longer select files by dial value. What
replaces it:

**Provenance is already in the file.** The DetectorVariation service
configuration — job key, policy, dial definitions — is part of the art process
history, exactly like every other service, and comes back out with
`config_dumper -P`. Since the throw is a pure function of that key and the
event ID, *every event's parameters are recomputable from the file alone*, with
no new data product, no new metadata field and no external database.
`perevent_lookup.py` does this and cross-checks against the job's own log.

**MetaCat changes meaning, not mechanism.** A per-event file should carry
`snowstorm.policy: "perEvent"`, `snowstorm.key` and `snowstorm.dial_hash` —
identity and reproducibility — but not `snowstorm.alpha`. Selection by value
moves from file level to event level, which is a real loss for job scheduling
and a real gain for statistics: every file spans the whole space.

**The CAF needs the values per event.** Recomputing them at CAF-making time
from the process history and event ID is enough in principle, but analysis code
should not have to carry a hash function, so the values belong in a branch —
the same few floats per record that DESIGN.md already recommends for the
per-file case, which is why that recommendation was to store them per event
even when they vary per file.

**Common random numbers still work, and matter more.** With
`NuRandomService.policy: "perEvent"` the random stream depends only on the
event ID, so the same event simulated at two parameter points has identical
randomness and their difference is a clean derivative. Note this is a
*different* use of the same machinery: per-event throwing marginalises over the
space within one sample, common random numbers compare points across samples.
A surrogate-model programme will want both.

**Threading.** The prototype caches the current event's values in the service,
which is only safe with one schedule. Because the throw is a pure function,
the production version should expose `value(dial, EventID)` and cache nothing
— then it is thread-safe by construction.

## 5. Demonstration

Five GENIE events, dunesw v10_16_00d00 with the patched larsim in front
(`run_perevent_test.sh`), run through g4 three times with identical input.

| event | nominal e- | per-file e- | per-event e- | per-event alpha |
|---|---|---|---|---|
| 1 |   1 889 365 |   1 915 163 |   1 895 644 | 0.93740506810129809 |
| 2 |  29 672 701 |  30 439 177 |  29 645 292 | 0.93010786846341131 |
| 3 |  23 922 861 |  24 483 043 |  24 424 691 | 0.94739320969999385 |
| 4 |  66 049 216 |  67 486 890 |  64 546 423 | 0.91181949023507425 |
| 5 | 103 989 143 | 106 686 475 | 109 176 462 | 0.96426599671881652 |

Three things to read off it:

- **The control is clean.** Without the service configured the module produces
  exactly the release's numbers and logs no dials — the patch is inert unless
  asked for.
- **Per-file reproduces the grid.** Its alpha, 0.94686924826693974, is the same
  value justIN workflow 20169 threw for counter 1, because it is the same key
  (`w20169-1`) through the same hash — the C++ service and the Python sampler
  agree to the last bit.
- **Per-event really varies per event**, and by a physically meaningful amount:
  ionization moves -2.3% to +5.0% against nominal, in step with alpha, while
  the deposits themselves (`ndepos`, `energy`) are identical across all three
  runs — only the recombination changed.

**The bookkeeping works.** `perevent_lookup.py` reads the job key, the policy
and the dial definitions out of each file's process history with
`config_dumper -P`, recomputes every event's values from its event ID, and
compares against what the job used: all events match, in both policies. No data
product, no metadata field, no database — the file already contains everything
needed to recover the parameters of every event in it.

## 6. Status

- [x] service + larsim hook written, builds against larsim v10_10_00
- [x] 5-event g4 demonstration: nominal / per-file / per-event all correct
- [x] offline recomputation from the file alone, cross-checked against the job
- [ ] WireCell lifetime visitor — designed in §3, not implemented
- [ ] stateless `value(dial, EventID)` for multi-schedule safety (§4)
- [ ] a CAF branch for the per-event values

## 7. What a production-quality implementation needs

The prototype proves the mechanism. Making it *right* means five packages, of
which only the first two are needed for recombination alone.

### larsim — the hook (upstream PR)

| # | change | size |
|---|---|---|
| 1 | `ISCalc.h`: virtual `SetRecombModBox(A, B)` with an empty default | 3 lines |
| 2 | `ISCalcCorrelated`: override it, cache the argon density | 8 lines |
| 3 | `ISCalcSeparate`: same override — it caches `fModBoxA/fModBoxB` too, and is a supported model | 8 lines |
| 4 | `IonAndScint::produce()`: fetch this event's values and push them in | 5 lines |
| 5 | **restructure the service as a LArSoft service *interface*** | ~80 lines |

Items 1-4 are done and working. Item 5 is the one real design change: larsim
must not depend on a DUNE service. LArSoft's own pattern for exactly this is
`spacecharge::SpaceChargeService` — an abstract interface plus a provider in
larsim, with the concrete implementation living in each experiment's code.
`IonAndScint` then asks for the interface if one is configured and is otherwise
unchanged, and dunesw supplies the implementation. `ISCalcNESTLAr` needs
nothing: NEST does not use the modified-box parameters at all.

Worth doing at the same time: take a `map<string,double>` rather than two
named doubles, so that the LArQL parameters (`LarqlChi0A..D`, `LarqlAlpha`,
`LarqlBeta`, `QAlpha`, `QProton`) and the ellipsoidal-box parameters become
dials without another larsim PR.

### dunesw — the service

| # | change | size |
|---|---|---|
| 6 | concrete `DetectorVariation` implementing the larsim interface: dial parsing, the throw, `perFile`/`perEvent` policy | ~200 lines (exists) |
| 7 | make it stateless: `value(dial, EventID)`, caching nothing | ~20 lines |
| 8 | fcl fragments, and a jobscript that passes the key instead of generating per-stage override fcls | small |
| 9 | a unit test asserting the C++ and Python throws agree bit for bit | ~40 lines |

Item 7 matters more than it looks. The prototype recomputes on
`sPreProcessEvent` and caches the result, which is only safe with one schedule.
Because the throw is a pure function there is no reason to hold state at all,
and without state the service is thread-safe by construction. Item 9 guards the
property the entire bookkeeping story rests on: if the two implementations ever
diverge, every file silently becomes unreadable.

### larwirecell — the electron lifetime

| # | change | size |
|---|---|---|
| 10 | `wclsDetectorVariation`, an `IArtEventVisitor` + `IConfigurable`: on `visit(event)`, throw the lifetime and reconfigure the Drifter through `Factory::find_tn<IConfigurable>` | ~60 lines |
| 11 | jsonnet: instantiate it, hand it the drifter configuration; fcl: add it to `wcls_main.inputers` | small |

This also covers `DL`/`DT`, which live in the same Drifter configuration and
are applied the same way.

### wire-cell-toolkit — optional, 3 lines

| # | change | size |
|---|---|---|
| 12 | `Drifter::configure()`: keep the existing `xregions` when the new configuration omits them | 3 lines |

Without it the visitor has to be handed the Drifter's whole configuration
(because `configure()` calls `reset()` and rebuilds the regions, throwing if
they are absent). With it, the visitor sends `{lifetime: x}` and nothing else,
which is much harder to get wrong.

### duneanaobj + CAFMaker — analysis access

| # | change | size |
|---|---|---|
| 13 | a per-event branch for the thrown values in `StandardRecord` | small |
| 14 | CAFMaker fills it | small |

Not strictly required — the values are recomputable from the file — but no
analyser should have to carry a hash function.

### What should *not* be made per-event

`elecGain`, `shaping`, the field responses and the noise spectra are baked into
cached waveforms and convolutions at configure time: `ColdElecResponse::configure()`
regenerates its response waveform, and `PlaneImpactResponse` builds convolved
field x electronics responses which nothing would rebuild. Varying them per
event means redoing that FFT work every event, and getting every cache
invalidated correctly. Per-event variation should stay restricted to parameters
applied per charge or per deposit — recombination, lifetime, diffusion — and
those are exactly the ones where it is cheap and correct.

### Order of work

The larsim and dunesw items (1-9) give per-event recombination with per-file
lifetime, which is a mixed model nobody asked for. So the sequence is: agree
with the systematics group that per-event is wanted at all, then do 10-12 so
both stages vary together, then propose 1-5 upstream with a working DUNE
implementation behind it. Items 13-14 can follow whenever the first sample
exists.

Files here: `setup_dev.sh` and `build_dev.sh` build the area (which lives under
`/exp/dune/data`, since `/exp/dune/app` has a 110 GB quota),
`run_perevent_test.sh` runs the three-way comparison, `check_perevent.sh` runs
the offline cross-check, `pe_*.fcl` are the configurations.
