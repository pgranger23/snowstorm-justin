# Per-event variation (experimental)

The per-file workflow in this repository is validated and in use. This
directory holds the *next* question — one parameter point per event rather than
per file — which needs code changes in LArSoft and is **not** production
machinery.

- `../docs/PEREVENT.md` — the study: what works, what the bookkeeping looks
  like, and a per-package list of what a production-quality implementation
  needs.
- `larsim-perevent.patch` — the working prototype against larsim v10_10_00
  (matching dunesw v10_16_00d00): a `DetectorVariation` art service that
  rethrows on `sPreProcessEvent` using the same hash as `bin/snowstorm_params.py`,
  plus a ~20-line hook so `IonAndScint` picks the values up per event.
  Apply with `git apply` in an mrb `srcs/larsim`.
- `pe_*.fcl` — nominal / per-file / per-event g4 configurations used for the
  three-way comparison.
- `perevent_lookup.py` — recovers every event's parameters from a file's own
  process history, with no new data product.

Demonstrated on 5 GENIE events: ionization moves -2.3% to +5.0% event by event,
and all five events' values are recomputable offline from the file alone. The
electron lifetime half (WireCell) is designed but not implemented.
