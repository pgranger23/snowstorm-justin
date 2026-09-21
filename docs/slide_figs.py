"""Standalone, slide-sized versions of the key panels.

The six-panel overview figures are for reading; these are for projecting, so
each carries ONE message at a font size that survives a beamer.
"""
import sys, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.ticker import FixedLocator, NullLocator, FuncFormatter

plt.rcParams.update({
    "figure.dpi": 160, "font.size": 13, "axes.grid": True, "grid.alpha": 0.25,
    "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
    "axes.labelsize": 14, "axes.titlesize": 15, "legend.fontsize": 12,
})
OUT = "/exp/dune/data/users/pgranger/repos/snowstorm-justin/docs"
C = {"lep": "#2166ac", "had": "#b2182b", "calo": "#762a83", "range": "#1b7837"}
NOMA, NOMT = 0.93, 10400.0

df = pd.read_csv("events_v2.csv")
df = df[np.isfinite(df.calo) & (df.calo > 0)]
df["r"] = df.calo / df.Etrue
df["r_lep"] = df.lep_calo / df.Etrue
df["r_had"] = df.e_had / df.Etrue
tot = df.lep_calo + df.e_had
df["fhad"] = np.where(tot > 0, df.e_had / tot, np.nan)

g = df.groupby("stem")
per = g.agg(alpha=("alpha", "first"), beta=("beta", "first"), etau=("etau", "first"),
            n=("Etrue", "size"), calo=("r", "median"), lep=("r_lep", "median"),
            had=("r_had", "median"), mu=("mu_range", "median"), fhad=("fhad", "median"))
per = per[per.n >= 20]

def fit(x, y, logx=False):
    xx = np.log10(x) if logx else np.asarray(x)
    s, i = np.polyfit(xx, y, 1)
    res = y - (s * xx + i)
    se = np.sqrt(np.sum(res**2) / (len(xx) - 2) / np.sum((xx - xx.mean())**2))
    return s, se, i

def taufmt(ax):
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator([3e3, 6e3, 1e4, 2e4, 3e4]))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v/1000:g}k"))

# ---------------------------------------------------------------- 1. pipeline
fig, ax = plt.subplots(figsize=(11, 4.4))
ax.set_xlim(0, 100); ax.set_ylim(0, 40); ax.axis("off")
stages = [("gen", 3.5), ("g4", 5.0), ("detsim", 34), ("reco1", 0.7),
          ("reco2", 1.5), ("CAF", 0.4)]
w, gap = 13.5, 2.2
for k, (name, sec) in enumerate(stages):
    x = 3 + k * (w + gap)
    hot = name in ("g4", "detsim")
    ax.add_patch(FancyBboxPatch((x, 17), w, 8, boxstyle="round,pad=0.4",
                                fc="#fde0dd" if hot else "#eef2f6",
                                ec="#b2182b" if hot else "#7a8b99",
                                lw=2.0 if hot else 1.2))
    ax.text(x + w / 2, 22.4, name, ha="center", va="center", fontsize=14,
            fontweight="bold" if hot else "normal")
    ax.text(x + w / 2, 19.2, f"{sec:g} s/evt", ha="center", va="center",
            fontsize=10, color="#555")
    if k < len(stages) - 1:
        ax.add_patch(FancyArrowPatch((x + w, 21), (x + w + gap, 21),
                                     arrowstyle="-|>", mutation_scale=14,
                                     lw=1.3, color="#44515c"))
ax.add_patch(FancyBboxPatch((3, 30), 28, 7.5, boxstyle="round,pad=0.4",
                            fc="#e8f2ea", ec="#1b7837", lw=1.6))
ax.text(17, 33.7, r"$\theta=f(\mathrm{SEED},\ \mathrm{counter})$",
        ha="center", va="center", fontsize=13)
for xs, lab, tgt in [(17, r"$\alpha,\beta$  (ModBoxA/B)", 3 + 1 * (w + gap) + w / 2),
                     (17, r"$\tau$  (WireCell lifetime)", 3 + 2 * (w + gap) + w / 2)]:
    ax.add_patch(FancyArrowPatch((xs + (0 if "Mod" in lab else 6), 30),
                                 (tgt, 25.4), arrowstyle="-|>",
                                 mutation_scale=13, lw=1.5, color="#b2182b",
                                 connectionstyle="arc3,rad=-0.2"))
ax.text(33, 35.2, r"$\alpha,\beta \rightarrow$ g4", fontsize=11, color="#b2182b")
ax.text(33, 31.6, r"$\tau \rightarrow$ detsim", fontsize=11, color="#b2182b")
xend = 3 + 5 * (w + gap) + w
ax.add_patch(FancyBboxPatch((3, 4.5), xend - 3, 8.5, boxstyle="round,pad=0.4",
                            fc="#f7f7f7", ec="#7a8b99", lw=1.2))
ax.text((3 + xend) / 2, 10.2, "kept:  snowstorm_<stem>_<dialhash>_s<seedhash>_caf.root",
        ha="center", fontsize=12, family="monospace")
ax.text((3 + xend) / 2, 6.8, "86 kB/evt    —    reco2 (13.8 MB/evt) discarded",
        ha="center", fontsize=10.5, color="#555")
ax.add_patch(FancyArrowPatch((xend - w / 2, 17), (xend - w / 2, 13.4),
                             arrowstyle="-|>", mutation_scale=13,
                             lw=1.3, color="#44515c"))
ax.text(50, 36, "one justIN job per universe", fontsize=12.5, style="italic",
        color="#44515c", ha="left", va="center")
fig.savefig(f"{OUT}/fig_pipeline.png", bbox_inches="tight")
print("fig_pipeline.png")

# ---------------------------------------------------------------- 2. coverage
fig, ax = plt.subplots(figsize=(8.2, 5.4))
sc = ax.scatter(per.alpha, per.etau, c=per.beta, s=26, cmap="viridis")
ax.axvline(NOMA, color="k", lw=0.9, ls="--", alpha=0.6)
ax.axhline(NOMT, color="k", lw=0.9, ls="--", alpha=0.6)
ax.text(NOMA, 3.2e3, " nominal", fontsize=10, color="0.3")
ax.set_yscale("log")
ax.set_xlabel(r"recombination  $\alpha$")
ax.set_ylabel(r"electron lifetime  $\tau$   [$\mu$s]")
ax.set_title(f"{len(per)} files = {len(per)} independent universes")
plt.colorbar(sc, ax=ax, label=r"$\beta$", pad=0.02)
fig.savefig(f"{OUT}/fig_coverage.png", bbox_inches="tight")
print("fig_coverage.png")

# ---------------------------------------------------------------- 3. spectrum
fig, ax = plt.subplots(figsize=(9, 5.2))
lo, hi = per.etau.quantile(0.25), per.etau.quantile(0.75)
bins = np.linspace(0, 1.5, 44)
for d, c, l in [(df, "k", "all files — marginalised over prior"),
                (df[df.stem.isin(per.index[per.etau <= lo])], C["had"],
                 r"short $\tau$ (lowest quartile)"),
                (df[df.stem.isin(per.index[per.etau >= hi])], C["lep"],
                 r"long $\tau$ (highest quartile)")]:
    ax.hist(d.r, bins=bins, density=True, histtype="step", lw=2.3, color=c,
            label=f"{l}   median {np.median(d.r):.3f}")
ax.set_xlabel(r"$E_{\rm calo}\,/\,E_\nu^{\rm true}$")
ax.set_ylabel("events (normalised)")
ax.set_title(r"A 22% swing in the energy scale, from the lifetime alone")
ax.legend(frameon=False, fontsize=11.5)
fig.savefig(f"{OUT}/fig_spectrum.png", bbox_inches="tight")
print("fig_spectrum.png")

# ---------------------------------------------------------------- 4. slopes
fig, ax = plt.subplots(figsize=(8.6, 5.2))
KEYS = [("had", r"$E_{\rm had}$", C["had"]), ("lep", r"$E_{\rm lep}$", C["lep"]),
        ("mu", r"$E_\mu$ (range)", C["range"])]
res = {}
for k, lab, c in KEYS:
    y = (per[k] / per[k].median()).values
    sa, ea, _ = fit(per.alpha.values, y)
    st, et, _ = fit(per.etau.values, y, logx=True)
    res[k] = (sa * 0.02 * 100, ea * 0.02 * 100,
              st * np.log10(2) * 100, et * np.log10(2) * 100)
xp = np.arange(3); wd = 0.36
a = [res[k][0] for k, _, _ in KEYS]; ae = [res[k][1] for k, _, _ in KEYS]
t = [res[k][2] for k, _, _ in KEYS]; te = [res[k][3] for k, _, _ in KEYS]
cols = [c for _, _, c in KEYS]
ax.bar(xp - wd/2, a, wd, yerr=ae, color=cols, capsize=4,
       error_kw=dict(lw=1.2, ecolor="0.25"), label=r"per $1\sigma$ of $\alpha$")
ax.bar(xp + wd/2, t, wd, yerr=te, color=cols, alpha=0.45, hatch="//", capsize=4,
       error_kw=dict(lw=1.2, ecolor="0.25"), label=r"per factor 2 in $\tau$")
for i in range(3):
    ax.text(xp[i] + wd/2, t[i] + te[i] + 0.35, f"{abs(t[i]/te[i]):.0f}$\\sigma$",
            ha="center", fontsize=11, color="0.25")
    ax.text(xp[i] - wd/2, a[i] + ae[i] + 0.35, f"{abs(a[i]/ae[i]):.1f}$\\sigma$",
            ha="center", fontsize=11, color="0.25")
ax.axhline(0, color="k", lw=1.0)
ax.set_xticks(xp); ax.set_xticklabels([l for _, l, _ in KEYS])
ax.set_ylabel("response  [% shift]")
ax.set_ylim(0, max(np.array(t) + np.array(te)) * 1.22)
ax.set_title("Both dials measured — including range-based energy")
ax.legend(frameon=False, loc="upper center")
fig.savefig(f"{OUT}/fig_slopes.png", bbox_inches="tight")
print("fig_slopes.png")
json.dump({k: res[k] for k in res}, open("slide_slopes.json", "w"), indent=2)

# ---------------------------------------------------------------- 5. drift
d2 = df[np.isfinite(df.vtx_x)]
fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0),
                         gridspec_kw=dict(width_ratios=[1.55, 1], wspace=0.28))
ax = axes[0]
XB = np.linspace(d2.vtx_x.quantile(0.01), d2.vtx_x.quantile(0.99), 11)
xc = 0.5 * (XB[1:] + XB[:-1])
def prof(d):
    o, e = [], []
    for a_, b_ in zip(XB[:-1], XB[1:]):
        m = (d.vtx_x >= a_) & (d.vtx_x < b_)
        if m.sum() < 30: o.append(np.nan); e.append(np.nan); continue
        o.append(d.r[m].median()); e.append(1.253 * d.r[m].std() / np.sqrt(m.sum()))
    return np.array(o), np.array(e)
ref, _ = prof(d2)
pq = per.etau.quantile([0.25, 0.75])
for sel, c, lab in [(per.index[per.etau <= pq.iloc[0]], C["had"], r"short $\tau$"),
                    (per.index[per.etau >= pq.iloc[1]], C["lep"], r"long $\tau$")]:
    m, e = prof(d2[d2.stem.isin(set(sel))])
    ax.errorbar(xc, m / ref, yerr=e / ref, fmt="o-", ms=5, lw=1.8, color=c,
                capsize=3, label=lab)
ax.axhline(1, color="k", lw=1.0, ls=":")
ax.axvline(-4, color="0.45", lw=1.2, ls="-.")
ax.text(-4, 1.145, " anode", fontsize=11, color="0.35")
ax.text(-350, 1.145, "cathode", fontsize=11, color="0.35")
ax.text(300, 1.145, "cathode", fontsize=11, color="0.35", ha="center")
ax.set_xlabel(r"reconstructed vertex  $x$   [cm]   (drift coordinate)")
ax.set_ylabel(r"$E_{\rm calo}/E_\nu^{\rm true}$  relative to ensemble")
ax.set_ylim(0.84, 1.17)
ax.set_title(r"$\tau$: attenuation grows with drift distance")
ax.legend(frameon=False)

ax = axes[1]
xm = d2.vtx_x.median(); d2 = d2.assign(absx=(d2.vtx_x - xm).abs())
lo_x, hi_x = d2.absx.quantile(0.15), d2.absx.quantile(0.85)
out = {}
for var, unit, c, lab in [("etau", np.log10(2), C["lep"], r"$\tau$ (per $\times2$)"),
                          ("alpha", 0.02, C["had"], r"$\alpha$ (per $1\sigma$)")]:
    near, far, vv = [], [], []
    for s_, d in d2.groupby("stem"):
        nm = d.absx <= lo_x; fm = d.absx >= hi_x
        if nm.sum() < 8 or fm.sum() < 8: continue
        near.append(d.r[nm].median()); far.append(d.r[fm].median()); vv.append(d[var].iloc[0])
    near, far, vv = map(np.array, (near, far, vv))
    x = np.log10(vv) if var == "etau" else vv
    vals = []
    for y in (near, far):
        yy = y / np.median(y)
        s, se, _ = fit(x, yy)
        vals.append((s * unit * 100, se * unit * 100))
    out[var] = vals
xp = np.arange(2); wd = 0.36
for k, (var, c) in enumerate([("etau", C["lep"]), ("alpha", C["had"])]):
    v = [out[var][0][0], out[var][1][0]]; e = [out[var][0][1], out[var][1][1]]
    ax.bar(xp + (k - 0.5) * wd, v, wd, yerr=e, color=c, capsize=4,
           error_kw=dict(lw=1.2, ecolor="0.25"),
           label=r"$\tau$ (per $\times2$)" if var == "etau" else r"$\alpha$ (per $1\sigma$)")
ax.axhline(0, color="k", lw=1.0)
ax.set_xticks(xp); ax.set_xticklabels(["near anode", "full drift"])
ax.set_ylabel("response  [% shift]")
ax.set_title("the separating fingerprint")
ax.legend(frameon=False, fontsize=11.5)
fig.savefig(f"{OUT}/fig_drift.png", bbox_inches="tight")
print("fig_drift.png",
      {k: [f"{a:+.2f}+-{b:.2f}" for a, b in v] for k, v in out.items()})

# ---------------------------------------------------------------- 6. covariance
EDGES = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 9.0, 15.0, 30.0])
NB = len(EDGES) - 1
stems = df.stem.unique()
N = np.zeros((len(stems), NB))
for i, s_ in enumerate(stems):
    N[i], _ = np.histogram(df.calo[df.stem == s_], bins=EDGES)
mean = N.mean(axis=0)
V_tot = np.cov(N, rowvar=False)
frac_tot = np.sqrt(np.diag(V_tot)) / mean
frac_mc = np.sqrt(mean) / mean
frac_sub = np.sqrt(np.clip(np.diag(V_tot - np.diag(mean)), 0, None)) / mean
A = np.array([df.etau[df.stem == s_].iloc[0] for s_ in stems])
AL = np.array([df.alpha[df.stem == s_].iloc[0] for s_ in stems])
X = np.column_stack([np.ones_like(A), AL - NOMA, np.log10(A) - np.log10(NOMT)])
coef, *_ = np.linalg.lstsq(X, N, rcond=None)
V_rs = np.outer(coef[1], coef[1]) * 0.02**2 + np.outer(coef[2], coef[2]) * np.std(np.log10(A))**2
frac_rs = np.sqrt(np.clip(np.diag(V_rs), 0, None)) / mean

fig, ax = plt.subplots(figsize=(9.2, 5.2))
ax.stairs(frac_tot * 100, EDGES, color=C["had"], lw=2.4, label="naive ensemble spread")
ax.stairs(frac_mc * 100, EDGES, color="0.45", lw=2.0, ls="--", label="MC statistics alone")
ax.stairs(frac_sub * 100, EDGES, color=C["lep"], lw=2.2, label="after subtracting MC noise")
ax.stairs(frac_rs * 100, EDGES, color=C["range"], lw=2.6, label="response surface")
ax.set_xscale("log")
ax.set_xlabel(r"$E_{\rm calo}$   [GeV]"); ax.set_ylabel("fractional uncertainty  [%]")
ax.set_title("Universes hold different events — MC noise does not cancel")
ax.legend(frameon=False, fontsize=11.5, loc="upper left")
fig.savefig(f"{OUT}/fig_covariance.png", bbox_inches="tight")
print("fig_covariance.png")
print("  bin      naive  mcstat  subtracted  respsurf")
for i in range(NB):
    print(f"  {EDGES[i]:5g}-{EDGES[i+1]:<5g} {frac_tot[i]*100:6.1f} {frac_mc[i]*100:7.1f}"
          f" {frac_sub[i]*100:10.1f} {frac_rs[i]*100:9.1f}")

# ---------------------------------------------------------------- 7. lep/had
fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.8), gridspec_kw=dict(wspace=0.27))
ax = axes[0]
for k, c, lab in [("lep", C["lep"], r"$E_{\rm lep}$"), ("had", C["had"], r"$E_{\rm had}$")]:
    y = per[k] / per[k].median()
    qs = np.quantile(np.log10(per.etau), np.linspace(0, 1, 9))
    cx, cy, ce = [], [], []
    for a_, b_ in zip(qs[:-1], qs[1:]):
        m = (np.log10(per.etau) >= a_) & (np.log10(per.etau) <= b_)
        if m.sum() < 3: continue
        cx.append(np.median(per.etau[m])); cy.append(y[m].mean())
        ce.append(y[m].std() / np.sqrt(m.sum()))
    ax.errorbar(cx, cy, yerr=ce, fmt="o-", ms=5, lw=1.8, color=c, capsize=3, label=lab)
taufmt(ax); ax.axhline(1, color="k", lw=0.9, ls=":")
ax.set_xlabel(r"electron lifetime  $\tau$  [$\mu$s]"); ax.set_ylabel("relative response")
ax.set_title("hadronic responds more steeply"); ax.legend(frameon=False)
ax = axes[1]
y = per.fhad / per.fhad.median()
qs = np.quantile(np.log10(per.etau), np.linspace(0, 1, 9))
cx, cy, ce = [], [], []
for a_, b_ in zip(qs[:-1], qs[1:]):
    m = (np.log10(per.etau) >= a_) & (np.log10(per.etau) <= b_)
    if m.sum() < 3: continue
    cx.append(np.median(per.etau[m])); cy.append(y[m].mean()); ce.append(y[m].std()/np.sqrt(m.sum()))
ax.errorbar(cx, cy, yerr=ce, fmt="o-", ms=5, lw=1.8, color=C["calo"], capsize=3)
sf, sfe, _ = fit(per.etau.values, y.values, logx=True)
taufmt(ax); ax.axhline(1, color="k", lw=0.9, ls=":")
ax.set_xlabel(r"electron lifetime  $\tau$  [$\mu$s]")
ax.set_ylabel(r"relative  $E_{\rm had}/(E_{\rm had}+E_{\rm lep})$")
ax.set_title(rf"inelasticity shifts: ${sf*np.log10(2)*100:+.2f}\pm{sfe*np.log10(2)*100:.2f}\%$ "
             rf"per $\times2$  (${abs(sf/sfe):.0f}\sigma$)")
fig.savefig(f"{OUT}/fig_lephad.png", bbox_inches="tight")
print("fig_lephad.png")
