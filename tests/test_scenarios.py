import numpy as np
import pytest

from trafoage.scenarios import (hours_of_day, residential_base, pv_shape,
                                ev_shape, heatpump_shape, make_loading,
                                ambient_daily)


def test_shapes_bounded_and_shaped():
    h = hours_of_day(96)
    for fn in (residential_base, pv_shape, ev_shape, heatpump_shape):
        s = fn(h)
        assert s.shape == (96,)
        assert np.all(s >= 0.0) and np.all(s <= 1.0 + 1e-12)


def test_base_load_peaks_in_evening():
    h = hours_of_day(96)
    s = residential_base(h)
    assert h[np.argmax(s)] == pytest.approx(19.0, abs=0.5)
    assert np.max(s) == pytest.approx(0.62)


def test_pv_zero_at_night_peak_at_noon():
    h = hours_of_day(96)
    s = pv_shape(h)
    assert s[h < 6.0].max() == 0.0 and s[h > 18.0].max() == 0.0
    assert h[np.argmax(s)] == pytest.approx(12.0, abs=0.5)


def test_make_loading_reverse_flow_with_high_pv():
    h = hours_of_day(96)
    k_base = make_loading(h, 250.0, 140.0)
    assert np.all(k_base >= 0.0)
    k_pv = make_loading(h, 250.0, 140.0, pv_kw=400.0)
    assert np.any(k_pv < 0.0)  # midday export exceeds local demand
    # evening peak unchanged by PV
    assert k_pv[np.argmax(k_base)] == pytest.approx(k_base.max())


def test_make_loading_magnitude():
    h = hours_of_day(96)
    k = make_loading(h, 250.0, 140.0, power_factor=0.95)
    # peak: 140 kW * 0.62 (shape max) / 0.95 / 250 kVA
    assert k.max() == pytest.approx(140.0 * 0.62 / 0.95 / 250.0, rel=1e-3)


def test_ambient_daily():
    h = hours_of_day(96)
    ta = ambient_daily(h, t_mean=30.0, t_swing=5.0, peak_hour=15.0)
    assert ta.mean() == pytest.approx(30.0, abs=0.05)
    assert h[np.argmax(ta)] == pytest.approx(15.0, abs=0.5)
