"""Quickstart: one command, five DER scenarios, two plots.

Run from the repo root::

    python examples/quickstart.py

Writes examples/quickstart_hotspot.png and examples/quickstart_aging.png,
and prints the headline comparison table.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from trafoage.cli import run_case, SCENARIOS

HERE = os.path.dirname(os.path.abspath(__file__))

fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
summaries = []
for name in SCENARIOS:
    h, k, out, s = run_case(name)
    summaries.append(s)
    axes[0].plot(h, k, label=name)
    axes[1].plot(h, out["theta_h"], label=name)

axes[0].axhline(1.0, ls="--", c="k", lw=1, label="rated load")
axes[0].axhline(0.0, c="k", lw=0.8)
axes[0].set_ylabel("loading (pu, signed)")
axes[0].legend(ncol=3, fontsize=9)
axes[0].set_title("Transformer loading by DER scenario (200 kVA ONAN)")
axes[1].axhline(110, ls="--", c="r", lw=1, label="110 C reference")
axes[1].set_ylabel("hot-spot temp (degC)")
axes[1].set_xlabel("hour of day")
axes[1].legend(ncol=3, fontsize=9)
axes[1].set_title("Hot-spot temperature (IEEE C57.91-2011 transient model)")
fig.tight_layout()
fig.savefig(os.path.join(HERE, "quickstart_loading_hotspot.png"), dpi=110)

names = [s["scenario"] for s in summaries]
life_h = [s["life_hours_consumed"] for s in summaries]
fig2, ax = plt.subplots(figsize=(8, 4.5))
bars = ax.bar(names, life_h)
ax.set_ylabel("insulation life consumed per day (hours)")
ax.set_title("Daily transformer life consumption by scenario")
for b, v in zip(bars, life_h):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:.2f}",
            ha="center", va="bottom", fontsize=9)
fig2.tight_layout()
fig2.savefig(os.path.join(HERE, "quickstart_aging.png"), dpi=110)

print(f"{'scenario':<10} {'F_EQA':>7} {'life-h/day':>10} "
      f"{'max THS(C)':>10} {'>110C':>6}")
for s in summaries:
    print(f"{s['scenario']:<10} {s['feqa']:>7.3f} "
          f"{s['life_hours_consumed']:>10.2f} "
          f"{s['theta_h_max']:>10.1f} "
          f"{s['frac_time_above_110c'] * 100:>5.1f}%")
print("\nwrote examples/quickstart_loading_hotspot.png, "
      "examples/quickstart_aging.png")
