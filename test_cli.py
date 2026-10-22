import csv
import os

import pytest

from trafoage.cli import run_case, main, SCENARIOS


def test_run_case_summary_shape():
    h, k, out, summary = run_case("pv+ev")
    assert len(h) == len(k) == len(out["theta_h"]) == 96
    for key in ("feqa", "life_hours_consumed", "loss_of_life_percent",
                "theta_h_max", "frac_time_above_110c", "scenario"):
        assert key in summary
    assert summary["scenario"] == "pv+ev"


def test_ev_ages_faster_than_base():
    base = run_case("base")[3]
    ev = run_case("ev")[3]
    assert ev["feqa"] > base["feqa"]
    assert ev["theta_h_max"] > base["theta_h_max"]


def test_winter_heatpump_is_harshest():
    feqas = {name: run_case(name)[3]["feqa"] for name in SCENARIOS}
    assert feqas["winter-hp"] == max(feqas.values())


def test_cli_compare_prints_table(capsys):
    assert main(["--compare"]) == 0
    out = capsys.readouterr().out
    for name in SCENARIOS:
        assert name in out


def test_cli_out_writes_csv(tmp_path):
    assert main(["--scenario", "pv", "--out", str(tmp_path)]) == 0
    summary = list(csv.DictReader(open(tmp_path / "summary.csv")))
    assert summary[0]["scenario"] == "pv"
    ts = list(csv.DictReader(open(tmp_path / "timeseries_pv.csv")))
    assert len(ts) == 96
    assert set(ts[0].keys()) == {"hour", "k_pu", "theta_h_C", "faa"}
