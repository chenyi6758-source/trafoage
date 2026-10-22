import numpy as np
import pytest

from trafoage.thermal import (Transformer, simulate, ultimate_rises,
                              corrected_tau_to)


@pytest.fixture
def tr():
    return Transformer(nameplate_kva=250.0)


def test_rated_load_steady_state(tr):
    dtheta_to_u, dtheta_h_u = ultimate_rises(1.0, tr)
    assert dtheta_to_u == pytest.approx(55.0)
    assert dtheta_h_u == pytest.approx(25.0)


def test_constant_load_converges_to_steady_state(tr):
    k = np.full(24 * 4, 0.8)
    out = simulate(k, 30.0, tr, dt_h=0.25, warmup_repeats=3)
    dtheta_to_u, dtheta_h_u = ultimate_rises(0.8, tr)
    assert out["theta_h"][-1] == pytest.approx(30.0 + dtheta_to_u + dtheta_h_u,
                                              abs=0.05)


def test_zero_load_keeps_no_load_loss_heating(tr):
    # Even at zero load the core (no-load) loss heats the oil:
    # dtheta_TO = 55 * (1/6)^0.8 ~= 13.1 C, winding rise = 0.
    k = np.zeros(24 * 4)
    out = simulate(k, 30.0, tr, dt_h=0.25, warmup_repeats=3)
    assert out["dtheta_h"][-1] == pytest.approx(0.0, abs=0.05)
    assert out["theta_h"][-1] == pytest.approx(30.0 + 55.0 * (1 / 6) ** 0.8,
                                              abs=0.05)


def test_reverse_flow_heats_like_forward_flow(tr):
    k = np.linspace(0.2, 1.1, 48)
    fwd = simulate(k, 30.0, tr, dt_h=0.25)
    rev = simulate(-k, 30.0, tr, dt_h=0.25)
    np.testing.assert_allclose(fwd["theta_h"], rev["theta_h"], rtol=1e-12)


def test_time_step_refinement(tr):
    # Compare at hour *ends* (end-aligned sampling); the winding time
    # constant (5 min) is far below the coarse step, so start-aligned
    # sampling would compare different physical times.
    k = np.tile(np.linspace(0.3, 1.0, 24), 4)
    coarse = simulate(k, 30.0, tr, dt_h=1.0, warmup_repeats=2)["theta_h"]
    fine = simulate(np.repeat(k, 4), 30.0, tr, dt_h=0.25,
                    warmup_repeats=2)["theta_h"][3::4]
    finer = simulate(np.repeat(k, 8), 30.0, tr, dt_h=0.125,
                     warmup_repeats=2)["theta_h"][7::8]
    assert np.max(np.abs(coarse - fine)) < 0.5
    assert np.max(np.abs(fine - finer)) < 0.1


def test_corrected_tau_to_degenerates(tr):
    assert corrected_tau_to(55.0, 55.0, tr) == pytest.approx(tr.tau_to_r_h)


def test_corrected_tau_to_cold_start(tr):
    # Cold start: initial rise 0, ultimate = rated rise.
    tau = corrected_tau_to(55.0, 0.0, tr)
    expected = tr.tau_to_r_h * (1.0 - 0.0) / (1.0 ** (1 / 0.8) - 0.0)
    assert tau == pytest.approx(expected)


def test_ultimate_rises_vectorized(tr):
    d_to, d_h = ultimate_rises(np.array([0.0, 0.5, 1.0, 1.5]), tr)
    assert d_to.shape == (4,)
    assert d_to[0] == pytest.approx(55.0 * (1 / 6) ** 0.8)  # no-load rise
    assert d_h[2] == pytest.approx(25.0)
    assert d_h[3] > d_h[2]  # overload -> hotter


def test_ambient_array_accepted(tr):
    k = np.full(48, 0.7)
    ta = 25.0 + 5.0 * np.sin(np.linspace(0, 2 * np.pi, 48))
    out = simulate(k, ta, tr, dt_h=0.5)
    assert out["theta_h"].shape == (48,)


def test_invalid_inputs_raise(tr):
    with pytest.raises(ValueError):
        Transformer(nameplate_kva=-10.0)
    with pytest.raises(ValueError):
        simulate(np.array([]), 30.0, tr)
    with pytest.raises(ValueError):
        simulate(np.ones(10), np.ones(5), tr)
