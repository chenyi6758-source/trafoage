"""Transient thermal model from IEEE Std C57.91-2011.

Mineral-oil-immersed distribution transformer, ONAN cooling. The model tracks
two thermal states -- top-oil rise over ambient and hot-spot rise over top-oil --
each approaching its load-dependent ultimate value with first-order dynamics:

    dtheta_TO(t) = (dtheta_TO,u - dtheta_TO,i) * (1 - exp(-t / tau_TO)) + dtheta_TO,i
    dtheta_H(t)  = (dtheta_H,u  - dtheta_H,i)  * (1 - exp(-t / tau_W))  + dtheta_H,i

    dtheta_TO,u = dtheta_TO,R * ((K_u^2 * R + 1) / (R + 1)) ^ n
    dtheta_H,u  = dtheta_H,R  * K_u ^ (2 * m)
    theta_H     = theta_A + dtheta_TO + dtheta_H

The top-oil time constant is load-corrected per the guide:

    tau_TO = tau_TO,R * ((du - di) / (du^(1/n) - di^(1/n)))

where du/di are the ultimate/initial top-oil rises in per unit of rated rise.
When ultimate == initial the corrected constant reduces to tau_TO,R.

Default nameplate values are literature-typical for ONAN distribution
transformers (e.g. Swift, Molinski & Lehn 1998 and the many studies that reuse
them: dtheta_TO,R = 55 C, dtheta_H,R = 25 C, R = 5, n = m = 0.8,
tau_TO,R = 3 h, tau_W = 5 min). They are adjustable -- pass your test-report
values when you have them.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class Transformer:
    """Nameplate + thermal parameters of one distribution transformer."""

    nameplate_kva: float
    dtheta_to_r: float = 55.0  # rated top-oil rise over ambient, degC
    dtheta_h_r: float = 25.0  # rated hot-spot rise over top-oil, degC
    r: float = 5.0  # ratio of load loss to no-load loss at rated load
    n: float = 0.8  # oil exponent (ONAN)
    m: float = 0.8  # winding exponent (ONAN)
    tau_to_r_h: float = 3.0  # rated top-oil time constant, hours
    tau_w_h: float = 5.0 / 60.0  # winding time constant, hours

    def __post_init__(self):
        for field in ("nameplate_kva", "dtheta_to_r", "dtheta_h_r", "r",
                      "n", "m", "tau_to_r_h", "tau_w_h"):
            if getattr(self, field) <= 0:
                raise ValueError(f"{field} must be positive")


def ultimate_rises(k, tr: Transformer):
    """Ultimate (steady-state) rises for per-unit loading ``k``.

    Heating depends on current magnitude, so reverse power flow (PV export)
    is handled with ``abs(k)`` -- the windings cannot tell which way the
    current flows.
    """
    k = np.abs(np.asarray(k, dtype=float))
    dtheta_to_u = tr.dtheta_to_r * ((k ** 2 * tr.r + 1.0) / (tr.r + 1.0)) ** tr.n
    dtheta_h_u = tr.dtheta_h_r * k ** (2.0 * tr.m)
    return dtheta_to_u, dtheta_h_u


def corrected_tau_to(dtheta_to_u, dtheta_to_i, tr: Transformer):
    """Load-corrected top-oil time constant (IEEE C57.91-2011, eq. 7.4)."""
    du = np.asarray(dtheta_to_u, dtype=float) / tr.dtheta_to_r
    di = np.asarray(dtheta_to_i, dtype=float) / tr.dtheta_to_r
    num = du - di
    den = du ** (1.0 / tr.n) - di ** (1.0 / tr.n)
    with np.errstate(divide="ignore", invalid="ignore"):
        tau = np.where(np.abs(den) > 1e-12, tr.tau_to_r_h * num / den,
                       tr.tau_to_r_h)
    return tau


def simulate(k, theta_a, tr: Transformer, dt_h=0.25, warmup_repeats=1):
    """Run the thermal model over a loading profile.

    Parameters
    ----------
    k : array_like
        Per-unit loading of each step (signed values allowed; magnitude is
        used for heating).
    theta_a : float or array_like
        Ambient temperature, degC (scalar or one value per step).
    tr : Transformer
        Transformer parameters.
    dt_h : float
        Step length in hours.
    warmup_repeats : int
        The profile is prepended this many times so thermal states settle;
        the warmup portion is discarded from the returned series.

    Returns
    -------
    dict of np.ndarray: ``theta_h`` (hot-spot, degC), ``dtheta_to``,
    ``dtheta_h`` -- one value per input step.
    """
    k = np.asarray(k, dtype=float)
    if k.ndim != 1 or k.size == 0:
        raise ValueError("k must be a non-empty 1-D array")
    if np.isscalar(theta_a):
        theta_a = np.full(k.shape, float(theta_a))
    else:
        theta_a = np.asarray(theta_a, dtype=float)
        if theta_a.shape != k.shape:
            raise ValueError("theta_a must be scalar or match k in shape")

    kk = np.tile(k, warmup_repeats + 1)
    ta = np.tile(theta_a, warmup_repeats + 1)

    dtheta_to_u, dtheta_h_u = ultimate_rises(kk, tr)
    # Initial states: steady state at the first step's loading.
    dtheta_to = np.empty_like(kk)
    dtheta_h = np.empty_like(kk)
    dtheta_to[0], dtheta_h[0] = dtheta_to_u[0], dtheta_h_u[0]

    for t in range(1, len(kk)):
        tau_to = corrected_tau_to(dtheta_to_u[t], dtheta_to[t - 1], tr)
        dtheta_to[t] = ((dtheta_to_u[t] - dtheta_to[t - 1])
                        * (1.0 - np.exp(-dt_h / tau_to)) + dtheta_to[t - 1])
        dtheta_h[t] = ((dtheta_h_u[t] - dtheta_h[t - 1])
                       * (1.0 - np.exp(-dt_h / tr.tau_w_h)) + dtheta_h[t - 1])

    theta_h = ta + dtheta_to + dtheta_h
    n = k.size
    return {
        "theta_h": theta_h[-n:],
        "dtheta_to": dtheta_to[-n:],
        "dtheta_h": dtheta_h[-n:],
    }
