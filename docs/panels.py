"""Every results panel, regenerated standalone at presentation size.

Cropping the multi-panel figures would give the wrong font sizes and lock in
their layout, so each panel is re-rendered from the same data instead. One file
per panel, all in docs/panels/.
"""
import json, os, sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullLocator, FuncFormatter

OUT = "/exp/dune/data/users/pgranger/repos/snowstorm-justin/docs/panels"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({
    "figure.dpi": 170, "font.size": 12.5, "axes.grid": True, "grid.alpha": 0.25,
    "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
    "axes.labelsize": 13.5, "axes.titlesize": 14, "legend.fontsize": 11.5,
})
C = {"lep": "#2166ac", "had": "#b2182b", "calo": "#762a83", "range": "#1b7837"}
NOMA, NOMT = 0.93, 10400.0
made = []

def fig1(w=7.4, h=5.0):
    f, a = plt.subplots(figsize=(w, h)); return f, a

def save(f, name, title):
    f.savefig(f"{OUT}/{name}.png", bbox_inches="tight"); plt.close(f)
    made.append((name, title)); print(f"  {name}")

def taufmt(ax):
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator([3e3, 6e3, 1e4, 2e4, 3e4]))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v/1000:g}k"))
    ax.set_xlabel(r"electron lifetime  $\tau$   [$\mu$s]")

def fit(x, y, logx=False):
    xx = np.log10(x) if logx else np.asarray(x)
    s, i = np.polyfit(xx, y, 1)
    r = y - (s * xx + i)
    se = np.sqrt(np.sum(r**2) / (len(xx) - 2) / np.sum((xx - xx.mean())**2))
    return s, se, i

def trend(ax, x, y, color, label, logx=False, nq=9):
    xx = np.log10(x) if logx else np.asarray(x)
    ax.plot(x, y, ".", ms=3, color=color, alpha=0.22, zorder=1)
    qs = np.quantile(xx, np.linspace(0, 1, nq))
    cx, cy, ce = [], [], []
    for a_, b_ in zip(qs[:-1], qs[1:]):
        m = (xx >= a_) & (xx <= b_)
        if m.sum() < 3: continue
        cx.append(np.median(x[m])); cy.append(y[m].mean())
        ce.append(y[m].std() / np.sqrt(m.sum()))
    ax.errorbar(cx, cy, yerr=ce, fmt="o", ms=5.5, color=color, lw=1.8,
                capsize=3, zorder=3, label=label)
    s, se, i = fit(x, y, logx)
    gx = np.linspace(xx.min(), xx.max(), 50)
    ax.plot(10**gx if logx else gx, s * gx + i, "-", color=color, lw=1.5, zorder=2)
    return s, se

# ------------------------------------------------------------------ data
df = pd.read_csv("events_v2.csv")
df = df[np.isfinite(df.calo) & (df.calo > 0)]
df["r"] = df.calo / df.Etrue
df["r_lep"] = df.lep_calo / df.Etrue
df["r_had"] = df.e_had / df.Etrue
df["r_mu"] = df.mu_range / df.Etrue
tot = df.lep_calo + df.e_had
df["fhad"] = np.where(tot > 0, df.e_had / tot, np.nan)
g = df.groupby("stem")
per = g.agg(alpha=("alpha", "first"), beta=("beta", "first"), etau=("etau", "first"),
            n=("Etrue", "size"), calo=("r", "median"), lep=("r_lep", "median"),
            had=("r_had", "median"), mu=("r_mu", "median"), fhad=("fhad", "median"))
per = per[per.n >= 20]
NRM = {k: per[k] / per[k].median() for k in ["calo", "lep", "had", "mu", "fhad"]}
QLO, QHI = per.etau.quantile(0.25), per.etau.quantile(0.75)
SLO = df[df.stem.isin(per.index[per.etau <= QLO])]
SHI = df[df.stem.isin(per.index[per.etau >= QHI])]
print(f"{len(df):,} events, {len(per)} universes")

# =============================================== 1. thrown parameter coverage
f, ax = fig1(7.6, 5.2)
sc = ax.scatter(per.alpha, per.etau, c=per.beta, s=24, cmap="viridis")
ax.axvline(NOMA, color="k", lw=0.9, ls="--", alpha=0.6)
ax.axhline(NOMT, color="k", lw=0.9, ls="--", alpha=0.6)
ax.set_yscale("log"); ax.set_xlabel(r"recombination  $\alpha$")
ax.set_ylabel(r"electron lifetime  $\tau$   [$\mu$s]")
ax.set_title(f"{len(per)} files = {len(per)} independent universes")
plt.colorbar(sc, ax=ax, label=r"$\beta$", pad=0.02)
save(f, "coverage_alpha_tau", "thrown parameter coverage; dashed = nominal")

# =============================================== 2-4. spectra split by tau
for col, name, lab, rng, ttl in [
        ("r", "spectrum_calo_by_tau", r"$E_{\rm calo}/E_\nu^{\rm true}$", (0, 1.5),
         "total calorimetric energy"),
        ("r_lep", "spectrum_lep_by_tau", r"$E_{\rm lep}/E_\nu^{\rm true}$", (0, 1.3),
         "leptonic energy"),
        ("r_had", "spectrum_had_by_tau", r"$E_{\rm had}/E_\nu^{\rm true}$", (0, 0.9),
         "hadronic energy")]:
    f, ax = fig1(7.6, 5.0)
    bins = np.linspace(*rng, 44)
    for d, c, l in [(df, "k", "all files"), (SLO, C["had"], r"short $\tau$ (low 25%)"),
                    (SHI, C["lep"], r"long $\tau$ (high 25%)")]:
        ax.hist(d[col], bins=bins, density=True, histtype="step", lw=2.2, color=c,
                label=f"{l}   median {np.median(d[col]):.3f}")
    ax.set_xlabel(lab); ax.set_ylabel("events (normalised)")
    ax.set_title(ttl); ax.legend(frameon=False)
    save(f, name, f"{ttl}, split by thrown lifetime")

# =============================================== 5-6. response vs each dial
for var, logx, xlab, name, ttl in [
        ("alpha", False, r"recombination  $\alpha$", "response_vs_alpha",
         r"response to $\alpha$"),
        ("etau", True, None, "response_vs_tau", r"response to $\tau$")]:
    f, ax = fig1(7.6, 5.0)
    for k, lab, c in [("had", r"$E_{\rm had}$ calorimetric", C["had"]),
                      ("lep", r"$E_{\rm lep}$ calorimetric", C["lep"]),
                      ("mu", r"$E_\mu$ from range", C["range"])]:
        trend(ax, per[var].values, NRM[k].values, c, lab, logx=logx)
    if logx: taufmt(ax)
    else: ax.set_xlabel(xlab)
    ax.axvline(NOMA if var == "alpha" else NOMT, color="k", lw=0.9, ls="--", alpha=0.6)
    ax.set_ylabel("median response (normalised)")
    ax.set_title(ttl); ax.legend(frameon=False, fontsize=10.5)
    save(f, name, f"per-file median energy against thrown {var}")

# =============================================== 7. slope summary
f, ax = fig1(7.6, 5.0)
KEYS = [("had", r"$E_{\rm had}$", C["had"]), ("lep", r"$E_{\rm lep}$", C["lep"]),
        ("mu", r"$E_\mu$ (range)", C["range"])]
res = {}
for k, _, _ in KEYS:
    sa, ea, _ = fit(per.alpha.values, NRM[k].values)
    st, et, _ = fit(per.etau.values, NRM[k].values, logx=True)
    res[k] = (sa*0.02*100, ea*0.02*100, st*np.log10(2)*100, et*np.log10(2)*100)
xp = np.arange(3); w = 0.36
a = [res[k][0] for k, _, _ in KEYS]; ae = [res[k][1] for k, _, _ in KEYS]
t = [res[k][2] for k, _, _ in KEYS]; te = [res[k][3] for k, _, _ in KEYS]
cols = [c for _, _, c in KEYS]
ax.bar(xp-w/2, a, w, yerr=ae, color=cols, capsize=4, error_kw=dict(lw=1.2, ecolor="0.25"),
       label=r"per $1\sigma$ of $\alpha$")
ax.bar(xp+w/2, t, w, yerr=te, color=cols, alpha=.45, hatch="//", capsize=4,
       error_kw=dict(lw=1.2, ecolor="0.25"), label=r"per factor 2 in $\tau$")
for i in range(3):
    ax.text(xp[i]+w/2, t[i]+te[i]+.35, f"{abs(t[i]/te[i]):.0f}$\\sigma$", ha="center",
            fontsize=10.5, color="0.25")
    ax.text(xp[i]-w/2, a[i]+ae[i]+.35, f"{abs(a[i]/ae[i]):.1f}$\\sigma$", ha="center",
            fontsize=10.5, color="0.25")
ax.axhline(0, color="k", lw=1)
ax.set_xticks(xp); ax.set_xticklabels([l for _, l, _ in KEYS])
ax.set_ylabel("response  [% shift]"); ax.set_ylim(0, max(np.array(t)+np.array(te))*1.22)
ax.set_title("measured response of each energy estimator")
ax.legend(frameon=False, loc="upper center")
save(f, "response_slopes", "slopes with uncertainties and significances")
json.dump(res, open(f"{OUT}/slopes.json", "w"), indent=2)

# =============================================== 8. lep & had vs tau
f, ax = fig1(7.6, 5.0)
for k, c, lab in [("lep", C["lep"], r"$E_{\rm lep}$"), ("had", C["had"], r"$E_{\rm had}$")]:
    trend(ax, per.etau.values, NRM[k].values, c, lab, logx=True)
taufmt(ax); ax.axhline(1, color="k", lw=.9, ls=":")
ax.set_ylabel("relative response")
ax.set_title("hadronic responds more steeply than leptonic")
ax.legend(frameon=False)
save(f, "lep_had_vs_tau", "leptonic vs hadronic response against lifetime")

# =============================================== 9. hadronic fraction
f, ax = fig1(7.6, 5.0)
sf, sfe = trend(ax, per.etau.values, NRM["fhad"].values, C["calo"], None, logx=True)
taufmt(ax); ax.axhline(1, color="k", lw=.9, ls=":")
ax.set_ylabel(r"relative  $E_{\rm had}/(E_{\rm had}+E_{\rm lep})$")
ax.set_title(rf"inelasticity shifts  ${sf*np.log10(2)*100:+.2f}\pm{sfe*np.log10(2)*100:.2f}\%$"
             rf" per $\times2$   (${abs(sf/sfe):.0f}\sigma$)")
save(f, "hadronic_fraction_vs_tau", "energy sharing, not just scale")

# =============================================== 10. E_had response surface
f, ax = fig1(6.8, 5.2)
ab = np.quantile(per.alpha, np.linspace(0, 1, 5))
tb = np.quantile(np.log10(per.etau), np.linspace(0, 1, 5))
Z = np.full((4, 4), np.nan)
for i in range(4):
    for k in range(4):
        m = ((per.alpha >= ab[i]) & (per.alpha <= ab[i+1]) &
             (np.log10(per.etau) >= tb[k]) & (np.log10(per.etau) <= tb[k+1]))
        if m.sum() >= 3: Z[k, i] = NRM["had"][m].mean()
im = ax.imshow(Z, origin="lower", aspect="auto", cmap="RdBu_r", vmin=.90, vmax=1.10,
               extent=[0, 4, 0, 4])
ax.set_xticks(np.arange(5)); ax.set_xticklabels([f"{v:.3f}" for v in ab], fontsize=10, rotation=45)
ax.set_yticks(np.arange(5)); ax.set_yticklabels([f"{10**v/1000:.1f}k" for v in tb], fontsize=10)
ax.set_xlabel(r"$\alpha$"); ax.set_ylabel(r"$\tau$   [$\mu$s]"); ax.grid(False)
ax.set_title(r"$E_{\rm had}$ response surface")
plt.colorbar(im, ax=ax, label="relative response", pad=0.02)
save(f, "had_response_surface", "binned response over the joint parameter space")

# =============================================== 11-13. drift
d2 = df[np.isfinite(df.vtx_x)]
f, ax = fig1(7.6, 4.4)
ax.hist(d2.vtx_x, bins=80, color="0.62")
ax.set_xlabel(r"reconstructed vertex  $x$   [cm]   (drift coordinate)")
ax.set_ylabel("events"); ax.set_title("vertex distribution along the drift")
save(f, "drift_vertex_distribution", "flat across the drift, as expected")

XB = np.linspace(d2.vtx_x.quantile(.01), d2.vtx_x.quantile(.99), 11)
xc = .5*(XB[1:]+XB[:-1])
def prof(d):
    o, e = [], []
    for a_, b_ in zip(XB[:-1], XB[1:]):
        m = (d.vtx_x >= a_) & (d.vtx_x < b_)
        if m.sum() < 30: o.append(np.nan); e.append(np.nan); continue
        o.append(d.r[m].median()); e.append(1.253*d.r[m].std()/np.sqrt(m.sum()))
    return np.array(o), np.array(e)
ref, _ = prof(d2)
for var, qq, c1, c2, l1, l2, name, ttl in [
        ("etau", per.etau.quantile([.25, .75]), C["had"], C["lep"],
         r"short $\tau$ (low 25%)", r"long $\tau$ (high 25%)",
         "drift_response_tau", r"$\tau$: attenuation grows with drift"),
        ("alpha", per.alpha.quantile([.25, .75]), "#e08214", "#542788",
         r"low $\alpha$ (25%)", r"high $\alpha$ (25%)",
         "drift_response_alpha", r"$\alpha$: flat in drift")]:
    f, ax = fig1(7.6, 5.0)
    for sel, c, l in [(per.index[per[var] <= qq.iloc[0]], c1, l1),
                      (per.index[per[var] >= qq.iloc[1]], c2, l2)]:
        m, e = prof(d2[d2.stem.isin(set(sel))])
        ax.errorbar(xc, m/ref, yerr=e/ref, fmt="o-", ms=5, lw=1.8, color=c, capsize=3, label=l)
    ax.axhline(1, color="k", lw=1, ls=":"); ax.axvline(-4, color="0.45", lw=1.2, ls="-.")
    ax.text(-4, 1.152, " anode", fontsize=11, color="0.35")
    ax.set_xlabel(r"reconstructed vertex  $x$   [cm]")
    ax.set_ylabel(r"$E_{\rm calo}/E_\nu^{\rm true}$  rel. to ensemble")
    ax.set_ylim(.84, 1.17); ax.set_title(ttl); ax.legend(frameon=False)
    save(f, name, ttl)

# =============================================== 14. fingerprint bars
f, ax = fig1(6.6, 5.0)
xm = d2.vtx_x.median(); d2 = d2.assign(absx=(d2.vtx_x-xm).abs())
lo_x, hi_x = d2.absx.quantile(.15), d2.absx.quantile(.85)
out = {}
for var, unit, c in [("etau", np.log10(2), C["lep"]), ("alpha", 0.02, C["had"])]:
    near, far, vv = [], [], []
    for s_, d in d2.groupby("stem"):
        nm = d.absx <= lo_x; fm = d.absx >= hi_x
        if nm.sum() < 8 or fm.sum() < 8: continue
        near.append(d.r[nm].median()); far.append(d.r[fm].median()); vv.append(d[var].iloc[0])
    near, far, vv = map(np.array, (near, far, vv))
    x = np.log10(vv) if var == "etau" else vv
    out[var] = [tuple(np.array(fit(x, y/np.median(y))[:2])*unit*100) for y in (near, far)]
xp = np.arange(2); w = .36
for k, (var, c) in enumerate([("etau", C["lep"]), ("alpha", C["had"])]):
    v = [out[var][0][0], out[var][1][0]]; e = [out[var][0][1], out[var][1][1]]
    ax.bar(xp+(k-.5)*w, v, w, yerr=e, color=c, capsize=4, error_kw=dict(lw=1.2, ecolor="0.25"),
           label=r"$\tau$ (per $\times2$)" if var == "etau" else r"$\alpha$ (per $1\sigma$)")
ax.axhline(0, color="k", lw=1)
ax.set_xticks(xp); ax.set_xticklabels(["near anode", "full drift"])
ax.set_ylabel("response  [% shift]"); ax.set_title("the separating fingerprint")
ax.legend(frameon=False)
save(f, "drift_fingerprint", "near-anode vs full-drift response for both dials")
print("  drift:", {k: [f"{a:+.2f}+-{b:.2f}" for a, b in v] for k, v in out.items()})

# =============================================== 15. CC vs NC
f, ax = fig1(7.6, 5.0)
for cc, c, lab in [(1, "#1b7837", "CC"), (0, "#762a83", "NC")]:
    d = df[df.iscc == cc]
    pf = d.groupby("stem").agg(etau=("etau", "first"), r=("r", "median"), n=("r", "size"))
    pf = pf[pf.n >= 10]; y = pf.r/pf.r.median()
    qs = np.quantile(np.log10(pf.etau), np.linspace(0, 1, 8))
    cx, cy, ce = [], [], []
    for a_, b_ in zip(qs[:-1], qs[1:]):
        m = (np.log10(pf.etau) >= a_) & (np.log10(pf.etau) <= b_)
        if m.sum() < 5: continue
        cx.append(np.median(pf.etau[m])); cy.append(y[m].mean()); ce.append(y[m].std()/np.sqrt(m.sum()))
    ax.errorbar(cx, cy, yerr=ce, fmt="o-", ms=5, lw=1.8, color=c, capsize=3,
                label=f"{lab}  (n={len(d):,})")
taufmt(ax); ax.axhline(1, color="k", lw=.9, ls=":")
ax.set_ylabel("relative response"); ax.set_title("CC and NC respond alike")
ax.legend(frameon=False)
save(f, "response_cc_vs_nc", "no dependence on interaction type")

# =============================================== 16. tau response vs energy
f, ax = fig1(7.6, 5.0)
eb = [0.5, 1, 2, 4, 8, 30]; cx, cy, ce = [], [], []
for lo, hi in zip(eb[:-1], eb[1:]):
    d = df[(df.Etrue >= lo) & (df.Etrue < hi)]
    pf = d.groupby("stem").agg(etau=("etau", "first"), r=("r", "median"), n=("r", "size"))
    pf = pf[pf.n >= 8]
    if len(pf) < 50: continue
    s, se, _ = fit(pf.etau.values, (pf.r/pf.r.median()).values, logx=True)
    cx.append(np.sqrt(lo*hi)); cy.append(s*np.log10(2)*100); ce.append(se*np.log10(2)*100)
cx, cy, ce = map(np.array, (cx, cy, ce))
ax.errorbar(cx, cy, yerr=ce, fmt="o-", ms=6, lw=1.8, color=C["lep"], capsize=4)
ax.axhline(0, color="k", lw=1); ax.set_xscale("log")
z = (cy[-1]-cy[0])/np.hypot(ce[-1], ce[0])
ax.set_xlabel(r"$E_\nu^{\rm true}$   [GeV]"); ax.set_ylabel(r"$\tau$ response  [% per $\times2$]")
ax.set_ylim(0, max(cy+ce)*1.25)
ax.set_title(rf"roughly flat in energy  (${z:.1f}\sigma$ end to end)")
save(f, "tau_response_vs_energy", "energy dependence of the lifetime response")

# =============================================== 17-22. analysis inputs
EDGES = np.array([0, .5, 1, 1.5, 2, 3, 4, 6, 9, 15, 30]); NB = len(EDGES)-1
stems = df.stem.unique()
N = np.zeros((len(stems), NB))
for i, s_ in enumerate(stems): N[i], _ = np.histogram(df.calo[df.stem == s_], bins=EDGES)
mean = N.mean(axis=0)
V_tot = np.cov(N, rowvar=False)
frac_tot = np.sqrt(np.diag(V_tot))/mean
frac_mc = np.sqrt(mean)/mean
frac_sub = np.sqrt(np.clip(np.diag(V_tot-np.diag(mean)), 0, None))/mean
A = np.array([df.etau[df.stem == s_].iloc[0] for s_ in stems])
AL = np.array([df.alpha[df.stem == s_].iloc[0] for s_ in stems])
X = np.column_stack([np.ones_like(A), AL-NOMA, np.log10(A)-np.log10(NOMT)])
coef, *_ = np.linalg.lstsq(X, N, rcond=None)
SIG_T = np.std(np.log10(A))
V_rs = np.outer(coef[1], coef[1])*0.02**2 + np.outer(coef[2], coef[2])*SIG_T**2
frac_rs = np.sqrt(np.clip(np.diag(V_rs), 0, None))/mean

f, ax = fig1(7.6, 5.0)
lo, hi = np.percentile(N, 16, axis=0), np.percentile(N, 84, axis=0)
ax.stairs(mean, EDGES, color="k", lw=2.2, label="ensemble mean")
ax.stairs(hi, EDGES, baseline=lo, fill=True, alpha=.30, color=C["lep"],
          label="detector band (16–84%)")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel(r"$E_{\rm calo}$   [GeV]"); ax.set_ylabel("events / universe")
ax.set_title("prediction with its detector band"); ax.legend(frameon=False)
save(f, "prediction_with_band", "ensemble mean and 16-84% spread")

f, ax = fig1(8.0, 5.0)
ax.stairs(frac_tot*100, EDGES, color=C["had"], lw=2.4, label="naive ensemble spread")
ax.stairs(frac_mc*100, EDGES, color="0.45", lw=2.0, ls="--", label="MC statistics alone")
ax.stairs(frac_sub*100, EDGES, color=C["lep"], lw=2.2, label="after subtracting MC noise")
ax.stairs(frac_rs*100, EDGES, color=C["range"], lw=2.6, label="response surface")
ax.set_xscale("log"); ax.set_xlabel(r"$E_{\rm calo}$   [GeV]")
ax.set_ylabel("fractional uncertainty  [%]")
ax.set_title("universes hold different events — MC noise does not cancel")
ax.legend(frameon=False, loc="upper left")
save(f, "mc_noise_trap", "why the naive covariance fails here")

f, ax = fig1(6.4, 5.4)
d_rs = np.sqrt(np.clip(np.diag(V_rs), 1e-12, None))
im = ax.imshow(V_rs/np.outer(d_rs, d_rs), vmin=-1, vmax=1, cmap="RdBu_r", origin="lower")
lbl = [f"{e:g}" for e in EDGES[:-1]]
ax.set_xticks(range(NB)); ax.set_yticks(range(NB))
ax.set_xticklabels(lbl, fontsize=9, rotation=90); ax.set_yticklabels(lbl, fontsize=9)
ax.set_xlabel(r"$E_{\rm calo}$ bin  [GeV]"); ax.set_ylabel(r"$E_{\rm calo}$ bin  [GeV]")
ax.grid(False); ax.set_title("response-surface correlation")
plt.colorbar(im, ax=ax, pad=0.02)
save(f, "covariance_correlation", "bin-to-bin correlation of the systematic")

f, ax = fig1(7.6, 5.0)
for sel, c, lab in [(per.index[per.etau <= QLO], C["had"], r"short $\tau$"),
                    (per.index[per.etau >= QHI], C["lep"], r"long $\tau$")]:
    sub = np.array([N[i] for i, s_ in enumerate(stems) if s_ in set(sel)])
    ok = sub.sum(axis=0) >= 50; last = np.max(np.where(ok)[0])+1
    ax.stairs((sub.mean(axis=0)/mean)[:last], EDGES[:last+1], color=c, lw=2.2, label=lab)
ax.axhline(1, color="k", lw=1, ls=":"); ax.set_xscale("log"); ax.set_ylim(.8, 1.2)
ax.set_xlabel(r"$E_{\rm calo}$   [GeV]"); ax.set_ylabel("ratio to ensemble mean")
ax.set_title("a shape effect, not a rescaling"); ax.legend(frameon=False)
save(f, "shape_not_normalisation", "spectral ratio for the two lifetime quartiles")

f, ax = fig1(6.8, 5.2)
pf = df.groupby("stem").agg(etau=("etau", "first"), r=("r", "median"), n=("r", "size"))
pf = pf[pf.n >= 20]; half = len(pf)//2
train, test = pf.iloc[:half], pf.iloc[half:]
sl, ic = np.polyfit(np.log10(train.etau), train.r, 1)
sig_cal = (train.r-(sl*np.log10(train.etau)+ic)).std()/np.sqrt(len(train))/abs(sl)
grp = pd.qcut(np.log10(test.etau), 8, labels=False)
tt, rr, ee = [], [], []
for q in range(8):
    m = grp == q
    if m.sum() < 5: continue
    tt.append(10**np.mean(np.log10(test.etau[m]))); rr.append((test.r[m].mean()-ic)/sl)
    ee.append(np.hypot(test.r[m].std()/np.sqrt(m.sum())/abs(sl), sig_cal))
tt, rr, ee = map(np.array, (tt, rr, ee))
ax.errorbar(np.log10(tt), rr, yerr=ee, fmt="o", ms=6, color=C["calo"], lw=1.8,
            capsize=4, label="recovered")
lim = [np.log10(pf.etau.min())-.05, np.log10(pf.etau.max())+.05]
ax.plot(lim, lim, "k--", lw=1.2, label="truth")
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel(r"thrown  $\log_{10}\tau$"); ax.set_ylabel(r"recovered  $\log_{10}\tau$")
chi2 = np.sum(((rr-np.log10(tt))/ee)**2)/len(tt)
ax.set_title(rf"closure:  $\chi^2$/dof $= {chi2:.2f}$"); ax.legend(frameon=False)
save(f, "closure_test", "calibrate on half the sample, recover the throw on the other")

f, ax = fig1(7.8, 5.0)
for sa, st, c, lab in [(0.02, SIG_T, "k", "as thrown (log-uniform)"),
                       (0.02, 0.30/np.log(10), C["calo"], r"$\tau$: $\pm30\%$ Gaussian"),
                       (0.02, 0.10/np.log(10), C["range"], r"$\tau$: $\pm10\%$ Gaussian"),
                       (0.06, SIG_T, C["had"], r"$\alpha$ prior $3\times$ wider")]:
    V = np.outer(coef[1], coef[1])*sa**2 + np.outer(coef[2], coef[2])*st**2
    ax.stairs(np.sqrt(np.clip(np.diag(V), 0, None))/mean*100, EDGES, color=c,
              lw=2.4 if c == "k" else 1.8, label=lab)
ax.set_xscale("log"); ax.set_xlabel(r"$E_{\rm calo}$   [GeV]")
ax.set_ylabel("detector uncertainty  [%]")
ax.set_title("one sample, any prior"); ax.legend(frameon=False, fontsize=10.5)
save(f, "prior_reweighting", "priors propagated through the fitted surface")

# ------------------------------------------------------------------ index
with open(f"{OUT}/INDEX.md", "w") as fh:
    fh.write("# Result panels\n\nStandalone versions of every panel in the "
             "multi-panel figures, regenerated from `events_v2.csv` by "
             "`docs/panels.py` (not cropped).\n\n| file | shows |\n|---|---|\n")
    for n, t in made:
        fh.write(f"| [`{n}.png`]({n}.png) | {t} |\n")
print(f"\n{len(made)} panels -> {OUT}")
