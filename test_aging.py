import numpy as np
import pytest

from trafoage.aging import (faa, feqa, loss_of_life_percent,
                            life_hours_consumed, summarize, NORMAL_LIFE_H)


def test_faa_is_one_at_reference():
    assert faa(110.0) == pytest.approx(1.0, rel=1e-9)
    assert faa(np.array([110.0, 110.0])).tolist() == pytest.approx([1.0, 1.0])


def test_faa_monotonic_and_known_value():
    assert faa(90.0) < faa(110.0) < faa(130.0)
    # exp(15000/383 - 15000/413) -- independently computed reference
    assert faa(140.0) == pytest.approx(17.195, abs=0.05)


def test_feqa_of_constant_series():
    assert feqa(np.full(100, 2.5)) == pytest.approx(2.5)
    with pytest.raises(ValueError):
        feqa(np.array([]))


def test_rated_load_day_consumes_one_day_of_life():
    # At constant rated load with 30 C ambient the hot-spot sits at the
    # 110 C reference, so one 24 h day consumes ~24 h of the 180,000 h
    # normal insulation life.
    from trafoage.thermal import Transformer, simulate
    tr = Transformer(nameplate_kva=250.0)
    out = simulate(np.full(96, 1.0), 30.0, tr, dt_h=0.25, warmup_repeats=3)
    s = summarize(faa(out["theta_h"]), out["theta_h"], dt_h=0.25)
    assert s["feqa"] == pytest.approx(1.0, abs=0.02)
    assert s["life_hours_consumed"] == pytest.approx(24.0, abs=0.5)
    assert s["loss_of_life_percent"] == pytest.approx(24.0 / NORMAL_LIFE_H * 100,
                                                     abs=1e-3)


def test_summarize_keys_and_shapes():
    f = np.linspace(0.5, 3.0, 48)
    th = np.linspace(80.0, 125.0, 48)
    s = summarize(f, th, dt_h=0.5)
    assert s["hours"] == pytest.approx(24.0)
    assert s["theta_h_max"] == pytest.approx(125.0)
    assert 0.0 < s["frac_time_above_110c"] < 1.0
    with pytest.raises(ValueError):
        summarize(f, th[:10], dt_h=0.5)


def test_overload_ages_faster_than_reference():
    assert life_hours_consumed(3.0, 24.0) == pytest.approx(72.0)
    assert loss_of_life_percent(3.0, 24.0) > loss_of_life_percent(1.0, 24.0)
