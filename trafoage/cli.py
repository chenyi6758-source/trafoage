"""Command-line interface: ``python -m trafoage --scenario pv+ev --out results/``."""

import argparse
import csv
import os

from .thermal import Transformer, simulate
from .aging import faa, summarize
from .scenarios import (hours_of_day, make_loading, ambient_daily)

SCENARIOS = {
    "base": dict(pv_kw=0.0, ev_kw=0.0, heatpump_kw=0.0),
    "pv": dict(pv_kw=120.0, ev_kw=0.0, heatpump_kw=0.0),
    "ev": dict(pv_kw=0.0, ev_kw=90.0, heatpump_kw=0.0),
    "pv+ev": dict(pv_kw=120.0, ev_kw=90.0, heatpump_kw=0.0),
    "winter-hp": dict(pv_kw=0.0, ev_kw=40.0, heatpump_kw=110.0),
}


def run_case(name, trafo_kva=200.0, base_peak_kw=120.0, t_mean=30.0,
             dt_h=0.25):
    """Run one scenario; returns (loading, hot-spot series, summary dict)."""
    h = hours_of_day(int(24 / dt_h))
    spec = SCENARIOS[name]
    k = make_loading(h, trafo_kva, base_peak_kw, power_factor=0.95, **spec)
    theta_a = ambient_daily(h, t_mean=t_mean)
    tr = Transformer(nameplate_kva=trafo_kva)
    out = simulate(k, theta_a, tr, dt_h=dt_h, warmup_repeats=2)
    summary = summarize(faa(out["theta_h"]), out["theta_h"], dt_h)
    summary["scenario"] = name
    return h, k, out, summary


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Transformer thermal aging under DER scenarios "
                    "(IEEE C57.91-2011).")
    ap.add_argument("--scenario", default="pv+ev", choices=list(SCENARIOS),
                    help="which DER scenario to run (default: pv+ev)")
    ap.add_argument("--compare", action="store_true",
                    help="run all scenarios and print a comparison table")
    ap.add_argument("--kva", type=float, default=200.0,
                    help="transformer nameplate rating in kVA")
    ap.add_argument("--peak-kw", type=float, default=120.0,
                    help="residential base peak demand in kW")
    ap.add_argument("--out", default=None,
                    help="output directory for CSV report (and PNG if "
                         "matplotlib is installed)")
    args = ap.parse_args(argv)

    names = list(SCENARIOS) if args.compare else [args.scenario]
    rows = []
    last = None
    for name in names:
        h, k, out, summary = run_case(name, trafo_kva=args.kva,
                                     base_peak_kw=args.peak_kw)
        rows.append(summary)
        last = (h, k, out, name)

    print(f"{'scenario':<10} {'F_EQA':>7} {'life-h/day':>10} "
          f"{'max THS(C)':>10} {'>110C':>6}")
    for r in rows:
        print(f"{r['scenario']:<10} {r['feqa']:>7.3f} "
              f"{r['life_hours_consumed']:>10.2f} "
              f"{r['theta_h_max']:>10.1f} "
              f"{r['frac_time_above_110c'] * 100:>5.1f}%")

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "summary.csv"), "w",
                  newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        h, k, out, name = last
        with open(os.path.join(args.out, f"timeseries_{name}.csv"), "w",
                  newline="") as f:
            w = csv.writer(f)
            w.writerow(["hour", "k_pu", "theta_h_C", "faa"])
            w.writerows(zip(h, k, out["theta_h"], faa(out["theta_h"])))
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
            axes[0].plot(h, out["theta_h"], label="hot-spot")
            axes[0].axhline(110, ls="--", c="r", label="110 C reference")
            axes[0].set_ylabel("degC")
            axes[0].legend()
            axes[1].plot(h, k, label="loading (pu)")
            axes[1].set_ylabel("pu")
            axes[1].set_xlabel("hour of day")
            axes[1].legend()
            fig.suptitle(f"trafoage: {name} scenario")
            fig.tight_layout()
            fig.savefig(os.path.join(args.out, f"timeseries_{name}.png"),
                        dpi=110)
            print(f"wrote {args.out}/")
        except ImportError:
            print(f"wrote CSVs to {args.out}/ (matplotlib not installed, "
                  "skipped PNG)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
