import numpy as np
import pytest

pp = pytest.importorskip("pandapower")

from trafoage.pandapower_link import loading_from_timeseries, demo_feeder


def test_demo_feeder_loading_length_and_sign():
    net = demo_feeder()
    n = 24
    load = {0: np.full(n, 0.20)}
    sgen = {0: np.concatenate([np.zeros(6), np.full(12, 0.15), np.zeros(6)])}
    k = loading_from_timeseries(net, 0, load, sgen)
    assert k.shape == (n,)
    assert np.all(k >= 0.0)
    # midday PV export unloads the transformer vs the night hours
    assert k[12] < k[0]


def test_mismatched_series_length_raises():
    net = demo_feeder()
    with pytest.raises(ValueError):
        loading_from_timeseries(net, 0, {0: np.zeros(24), 1: np.zeros(10)})
