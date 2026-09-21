"""Schematic of bin/snowstorm_lookup.py: three independent routes back from a
file to the parameter point that produced it."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = "/exp/dune/data/users/pgranger/repos/snowstorm-justin/docs/fig_lookup.png"
INK, INK2, INK3 = "#101820", "#44515c", "#7d8d9b"
BLUE, RED, GREEN, VIOLET = "#2166ac", "#b2182b", "#1b7837", "#762a83"
TINT, RULE, PAPER = "#f2f6f9", "#ccd7e0", "#ffffff"
MF = "DejaVu Sans Mono"

fig, ax = plt.subplots(figsize=(13.2, 9.0))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

def card(x, y, w, h, ec=RULE, fc=TINT, lw=1.3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.45",
                                fc=fc, ec=ec, lw=lw, zorder=2))

def m(x, y, t, s=8.6, c=INK, w="normal", ha="left"):
    ax.text(x, y, t, fontsize=s, color=c, va="top", ha=ha, zorder=4,
            family=MF, weight=w)

def sans(x, y, t, s=8.8, c=INK3, style="normal", ha="left", w="normal"):
    ax.text(x, y, t, fontsize=s, color=c, va="top", ha=ha, zorder=4,
            style=style, weight=w)

def arrow(p, q, c=INK2, rad=0.0, lw=1.6, ls="-"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=14,
                                 lw=lw, color=c, linestyle=ls, zorder=3,
                                 connectionstyle=f"arc3,rad={rad}"))

# ================================================================= the file
sans(50, 99, "bin/snowstorm_lookup.py  —  recovering the parameters that made a file",
     11, INK, ha="center", w="bold")
card(13, 88.5, 74, 8.0, BLUE, "#eef4fa", 1.7)
ax.text(50, 95.0, "snowstorm_dune10kt_1x2x6_000252_e1d55d70_s2ea20f_caf.root",
        fontsize=12, color=INK, ha="center", va="top", zorder=4,
        family=MF, weight="bold")
sans(50, 91.4, "the name carries the stem and the two fingerprints", ha="center")

X = [1, 34.5, 68]; W = 31
for x in X:
    arrow((x + W / 2, 88.2), (x + W / 2, 85.6))

# ================================================================= route 1
x = X[0]
card(x, 28, W, 56, GREEN, PAPER, 1.7)
m(x + 2, 82.3, "--from-name", 11, GREEN, "bold")
sans(x + 2, 79.0, "offline · instant · never opens the file")
ax.plot([x + 2, x + W - 2], [76.6, 76.6], color=RULE, lw=1.1, zorder=4)
sans(x + 2, 75.0, "needs", 8.4, INK3)
m(x + 2, 72.4, "the name + --seed + --dials", 8.4, INK2)
sans(x + 2, 68.6, "parse_name  reads from the RIGHT:", 8.8, INK2)
m(x + 2, 65.8, 's<6 hex>  preceded by  <8 hex>', 8.4)
sans(x + 2, 63.0, "stems are input file names — they", 8.4)
sans(x + 2, 60.6, "contain underscores themselves", 8.4)
for i, (t, sub) in enumerate([
        ("dial hash  !=  --dials given", "someone edited the priors"),
        ("seed hash  !=  --seed given", "wrong production seed")]):
    yy = 57.6 - i * 9.4
    card(x + 2, yy - 6.4, W - 4, 6.6, RED, "#fdeeee", 1.2)
    m(x + 3.4, yy - 0.5, t, 8.2, RED, "bold")
    sans(x + 3.4, yy - 3.4, f"{sub}  →  REFUSES", 8.0, RED)
m(x + 2, 37.8, "throw(key, name, dial)", 9.0, INK, "bold")
sans(x + 2, 34.8, "the same function the production", 8.4)
sans(x + 2, 32.4, "used — not a stored copy", 8.4)

# ================================================================= route 2
x = X[1]
card(x, 28, W, 56, BLUE, PAPER, 1.7)
m(x + 2, 82.3, "--from-metacat", 11, BLUE, "bold")
sans(x + 2, 79.0, "needs network · the bulk-query route")
ax.plot([x + 2, x + W - 2], [76.6, 76.6], color=RULE, lw=1.1, zorder=4)
sans(x + 2, 75.0, "needs", 8.4, INK3)
m(x + 2, 72.4, "metacat setup + a file DID", 8.4, INK2)
m(x + 2, 68.6, "metacat file show --json", 8.4, INK2)
m(x + 2, 66.0, "     --metadata <did>", 8.4, INK2)
sans(x + 2, 62.2, "reads the sidecar written at", 8.4)
sans(x + 2, 59.8, "output time:", 8.4)
card(x + 2, 45.4, W - 4, 11.6, RULE, TINT, 1.1)
for i, t in enumerate(["snowstorm.alpha  0.9178211451",
                       "snowstorm.beta   0.2121058428",
                       "snowstorm.etau   6485.068827",
                       "snowstorm.dial_hash  e1d55d70"]):
    m(x + 3.4, 55.6 - i * 2.5, t, 8.0, INK2)
card(x + 2, 34.6, W - 4, 9.2, BLUE, "#eef4fa", 1.2)
sans(x + 3.4, 42.4, "the only route that answers", 8.4, BLUE)
m(x + 3.4, 39.6, '"every file with tau < 6000"', 8.2, BLUE, "bold")
sans(x + 3.4, 36.8, "without touching any file", 8.4, BLUE)
sans(x + 2, 32.2, "absent if the output went", 8.2, INK3)
sans(x + 2, 29.9, "somewhere Rucio does not manage", 8.2, INK3)

# ================================================================= route 3
x = X[2]
card(x, 28, W, 56, VIOLET, PAPER, 1.7)
m(x + 2, 82.3, "--from-file", 11, VIOLET, "bold")
sans(x + 2, 79.0, "slowest · ground truth")
ax.plot([x + 2, x + W - 2], [76.6, 76.6], color=RULE, lw=1.1, zorder=4)
sans(x + 2, 75.0, "needs", 8.4, INK3)
m(x + 2, 72.4, "the file itself + dunesw", 8.4, INK2)
m(x + 2, 68.6, "config_dumper -P <file>", 9.0, VIOLET, "bold")
sans(x + 2, 65.6, "splits the art process history", 8.4)
sans(x + 2, 63.2, "into per-process blocks, then", 8.4)
sans(x + 2, 60.8, "matches each dial's leaf name", 8.4)
sans(x + 2, 58.4, "inside its own  \"process\"", 8.4)
card(x + 2, 42.6, W - 4, 12.4, RED, "#fdeeee", 1.2)
m(x + 3.4, 53.8, "-P, never -S", 8.6, RED, "bold")
sans(x + 3.4, 51.0, "-S collapses every process into", 8.0, RED)
sans(x + 3.4, 48.8, "one block, so a stage that left", 8.0, RED)
sans(x + 3.4, 46.6, "the dial at nominal overwrites", 8.0, RED)
sans(x + 3.4, 44.4, "the value the earlier stage used", 8.0, RED)
card(x + 2, 32.2, W - 4, 8.2, VIOLET, "#f6eef8", 1.2)
sans(x + 3.4, 39.0, "works on files produced", 8.4, VIOLET)
sans(x + 3.4, 36.6, "before any of this tooling", 8.4, VIOLET)
sans(x + 3.4, 34.2, "existed — nothing is assumed", 8.4, VIOLET)

# ================================================================= converge
for x, c in zip(X, [GREEN, BLUE, VIOLET]):
    arrow((x + W / 2, 27.6), (x + W / 2, 24.2), c=c)
ax.plot([16.5, 83.5], [24.0, 24.0], color=INK3, lw=1.2, zorder=3)
arrow((50, 24.0), (50, 21.2))
card(13, 7.5, 74, 13.0, INK, "#eef2f6", 1.8)
ax.text(50, 18.6, "alpha 0.9178211451     beta 0.2121058428     etau 6485.068827",
        fontsize=11.5, color=INK, ha="center", va="top", zorder=4,
        family=MF, weight="bold")
sans(50, 14.2, "the three routes must agree — if they do not, something is wrong "
     "and you want to know", 9.6, INK2, "italic", ha="center")
sans(50, 11.0, "route 1 is what analysis loops use; route 3 is what you reach for "
     "when routes 1 and 2 disagree", 8.8, INK3, "italic", ha="center")

sans(50, 4.2, "the inverse of the throw: nothing is stored centrally, so every route "
     "recomputes rather than looks up", 9.2, INK3, "italic", ha="center")

fig.savefig(OUT, bbox_inches="tight", dpi=170, facecolor="white")
print("wrote", OUT)
