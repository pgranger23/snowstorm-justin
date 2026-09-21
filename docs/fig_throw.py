"""Schematic of the throw: where the key comes from, how a dial is declared,
and how the wrapping fcl is written.

Laid out on a 100x100 grid over a 13.2 x 8.2 in canvas, so one y-unit is
0.082 in and a 9 pt line is ~1.55 units tall -- LH below is the line pitch that
keeps text clear of its own box.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = "/exp/dune/data/users/pgranger/repos/snowstorm-justin/docs/fig_throw.png"
INK, INK2, INK3 = "#101820", "#44515c", "#7d8d9b"
BLUE, RED, GREEN = "#2166ac", "#b2182b", "#1b7837"
TINT, RULE, PAPER = "#f2f6f9", "#ccd7e0", "#ffffff"
MF = "DejaVu Sans Mono"
LH = 2.75                      # line pitch for 9.2 pt mono

fig, ax = plt.subplots(figsize=(13.2, 8.2))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

def card(x, y, w, h, ec=RULE, fc=TINT, lw=1.3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.45",
                                fc=fc, ec=ec, lw=lw, zorder=2))

def head(x, y, t, c=INK):
    ax.text(x, y, t, fontsize=10.5, color=c, va="bottom", zorder=4,
            family=MF, weight="bold")

def m(x, y, t, s=9.2, c=INK, w="normal"):
    ax.text(x, y, t, fontsize=s, color=c, va="top", zorder=4, family=MF, weight=w)

def sans(x, y, t, s=9.2, c=INK3, style="normal", ha="left"):
    ax.text(x, y, t, fontsize=s, color=c, va="top", ha=ha, zorder=4, style=style)

def arrow(p, q, c=INK2, rad=0.0, lw=1.6, ls="-"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=14,
                                 lw=lw, color=c, linestyle=ls, zorder=3,
                                 connectionstyle=f"arc3,rad={rad}"))

# ======================================================= 1. the key
head(1.5, 95.5, "1 · THE KEY")
card(1, 66, 45, 27, RULE, PAPER)
m(3, 91.0, "SEED", 10.5, BLUE, "bold"); m(13, 91.0, '"atmnu-hd-2026a"', 10.5)
sans(3, 87.6, "chosen once, by the submitter")
m(3, 83.0, "stem", 10.5, BLUE, "bold"); m(13, 83.0, '"dune10kt_1x2x6_000252"', 10.5)
sans(3, 79.6, "the justin-get-file counter, or the input file name")
ax.plot([3, 44], [76.4, 76.4], color=RULE, lw=1.1, zorder=4)
m(3, 74.6, "job key =", 9.6, INK3)
m(15, 74.6, '"atmnu-hd-2026a/dune10kt_1x2x6_000252"', 9.6, INK)
sans(3, 70.6, "no workflow ID  →  a retried job lands on the same θ",
     9.2, RED, "italic")

# ======================================================= 2. the dial file
head(54.5, 95.5, "2 · THE DIAL FILE")
card(54, 66, 45, 27, RULE, PAPER)
m(56, 91.0, "dials/recomb_lifetime_v1.json", 9.6, INK2)
for i, (t, c) in enumerate([
        ('  "alpha": {', INK),
        ('    "fcl":   "services.LArG4Parameters.ModBoxA",', GREEN),
        ('    "stage": "g4",  "process": "G4",', BLUE),
        ('    "dist": "gaus", "nominal": 0.93,', RED),
        ('    "sigma": 0.02,  "clip": [0.85, 1.01] },', RED),
        ('  "etau": {', INK),
        ('    "fcl":   "...wcls_main.structs.lifetime",', GREEN),
        ('    "stage": "detsim",', BLUE),
        ('    "dist": "loguniform", "range": [3000, 35000] }', RED)]):
    m(56, 87.4 - i * 2.05, t, 8.6, c)
for x, c, t in [(56, GREEN, "which fcl parameter"), (76.5, BLUE, "which stage"),
                (88.5, RED, "the prior")]:
    ax.plot([x, x + 1.6], [67.8, 67.8], color=c, lw=2.2, zorder=4)
    ax.text(x + 2.4, 67.8, t, fontsize=8.6, color=c, va="center", zorder=4)

# ======================================================= the tool
arrow((23, 65.5), (36, 58.5), rad=-0.15)
arrow((76, 65.5), (64, 58.5), rad=0.15)
card(25, 46, 50, 11, INK, "#eef2f6", 1.8)
m(27, 55.6, "bin/snowstorm_params.py", 11.5, INK, "bold")
m(27, 52.2, "--seed $SEED  --stem $stem  --dials $DIALS", 9.2, INK2)
m(27, 49.4, "--stage g4", 9.6, GREEN, "bold")
sans(77, 55.0, "sha256(key + dial name)", 9.2, INK3, "italic")
sans(77, 51.8, "→ one uniform per dial", 9.2, INK3, "italic")
sans(77, 48.6, "→ dials stay independent", 9.2, INK3, "italic")

# ======================================================= 3. the wrapping fcl
head(1.5, 41.5, "3 · THE WRAPPING FCL")
arrow((40, 45.5), (24, 40.0), rad=0.18)
card(1, 22, 45, 16, RULE, PAPER)
sans(3, 36.6, "stdout of --stage g4", 9.2, INK3)
m(3, 33.2, "# SnowStorm overrides, stage=g4,", 8.6, INK3)
m(3, 30.8, "#   key=atmnu-hd-2026a/dune10kt_1x2x6_000252", 8.6, INK3)
m(3, 27.8, "services.LArG4Parameters.ModBoxA: 0.9178211451", 8.8)
m(3, 25.4, "services.LArG4Parameters.ModBoxB: 0.2121058428", 8.8)

arrow((47, 30), (53, 30), rad=0)

card(54, 22, 45, 16, GREEN, PAPER, 1.7)
sans(56, 36.6, "local_g4.fcl   — written by the jobscript", 9.2, INK3)
m(56, 33.2, '#include "standard_g4_dune10kt_1x2x6.fcl"', 8.8, GREEN)
m(56, 30.4, "services.LArG4Parameters.ModBoxA: 0.9178211451", 8.4, INK2)
m(56, 28.2, "services.LArG4Parameters.ModBoxB: 0.2121058428", 8.4, INK2)
ax.plot([56, 97], [26.4, 26.4], color=RULE, lw=1.1, zorder=4)
m(56, 25.2, "lar -c local_g4.fcl -o out.root in.root", 9.6, INK, "bold")

sans(50, 19.6, "your own fcl, unchanged — the throw is simply prepended to it",
     9.2, INK3, "italic", ha="center")

# ======================================================= the output name
arrow((76, 21.5), (76, 15.5), rad=0)
card(1, 2, 98, 12, BLUE, "#eef4fa", 1.7)
ax.text(50, 11.4, "snowstorm_dune10kt_1x2x6_000252_e1d55d70_s2ea20f_caf.root",
        fontsize=13, color=INK, ha="center", va="top", zorder=4,
        family=MF, weight="bold")
X0, CW = 26.5, 0.824          # left edge and character advance of the name
for lo, hi, t, c in [(10, 31, "stem", BLUE), (32, 40, "dial hash", RED),
                     (42, 48, "seed hash", RED)]:
    x = X0 + CW * (lo + hi) / 2
    ax.plot([X0 + CW * lo, X0 + CW * hi], [8.7, 8.7], color=c, lw=1.6, zorder=4)
    ax.plot([x, x], [8.7, 7.6], color=c, lw=1.2, zorder=4)
    ax.text(x, 7.1, t, fontsize=8.8, color=c, ha="center", va="top",
            zorder=4, family=MF)
sans(50, 3.6, "fingerprints from --dial-hash and --seed-hash:  a changed prior changes "
     "the dial hash, so a lookup refuses instead of returning wrong numbers",
     9.0, INK3, "italic", ha="center")

fig.savefig(OUT, bbox_inches="tight", dpi=170, facecolor="white")
print("wrote", OUT)
