"""DER loading scenarios for a distribution transformer.

All shapes are synthetic but documented: they encode the qualitative facts
that matter for transformer aging -- a residential evening peak, PV
generation centred on solar noon (which *unloads* the transformer by day),
EV home charging stacked on the evening peak, and heat-pump load on cold
winter days. Magnitudes come from the caller's kW assumptions, not from the
shapes, so the tool stays honest about what is measured vs assumed.

Convention: positive k = power flowing grid -> customers; negative k =
reverse flow (PV export). The thermal model uses |k|.
"""

import numpy as np


def hours_of_day(n_steps=96):
    """Hour-of-day stamps for a 24 h profile (default 15-min resolution)."""
    return np.linspace(0.0, 24.0, n_steps, endpoint=False)


def _gauss(h, mu, sigma):
    d = np.minimum(np.abs(h - mu), 24.0 - np.abs(h - mu))
    return np.exp(-0.5 * (d / sigma) ** 2)


def residential_base(h):
    """Normalized residential load shape, peaks ~0.62 at 19:00.

    Morning shoulder + evening peak, night valley ~0.25. Values are relative;
    scale by the transformer's base peak kW.
    """
    h = np.asarray(h, dtype=float)
    shape = (0.25
             + 0.10 * _gauss(h, 7.5, 1.6)
             + 0.37 * _gauss(h, 19.0, 2.4))
    return shape / np.max(shape) * 0.62


def pv_shape(h):
    """Normalized PV generation shape, 1.0 at solar noon.

    sin^1.2 bell between 06:00 and 18:00, zero at night.
    """
    h = np.asarray(h, dtype=float)
    s = np.sin(np.pi * np.clip((h - 6.0) / 12.0, 0.0, 1.0))
    out = np.where((h >= 6.0) & (h <= 18.0), s ** 1.2, 0.0)
    return out / np.max(out)


def ev_shape(h, peak_hour=20.0):
    """Normalized EV home-charging shape, 1.0 at the evening peak."""
    h = np.asarray(h, dtype=float)
    shape = _gauss(h, peak_hour, 2.0) + 0.35 * _gauss(h, peak_hour + 4.5, 2.5)
    return shape / np.max(shape)


def heatpump_shape(h):
    """Normalized extra winter heat-pump load shape (morning + evening)."""
    h = np.asarray(h, dtype=float)
    shape = 0.55 * _gauss(h, 7.0, 2.0) + 0.75 * _gauss(h, 19.5, 2.6) + 0.30
    return shape / np.max(shape)


def make_loading(h, trafo_kva, base_peak_kw, pv_kw=0.0, ev_kw=0.0,
                 heatpump_kw=0.0, power_factor=0.95):
    """Build a per-unit loading series for one day.

    Parameters
    ----------
    h : array_like
        Hour-of-day stamps (see :func:`hours_of_day`).
    trafo_kva : float
        Transformer nameplate rating.
    base_peak_kw : float
        Residential peak demand (kW) at the shape's maximum.
    pv_kw : float
        Installed PV behind the transformer (kW AC at shape maximum).
    ev_kw : float
        Coincident EV charging peak (kW).
    heatpump_kw : float
        Extra heat-pump peak (kW), e.g. a cold winter day.
    power_factor : float
        Assumed constant power factor for kVA conversion.

    Returns
    -------
    np.ndarray
        Per-unit loading, signed (negative = reverse flow into the grid).
    """
    h = np.asarray(h, dtype=float)
    p_kw = (base_peak_kw * residential_base(h)
            + ev_kw * ev_shape(h)
            + heatpump_kw * heatpump_shape(h)
            - pv_kw * pv_shape(h))
    # Sign of real power sets the flow direction; magnitude drives heating.
    kva_signed = np.abs(p_kw) / power_factor * np.where(p_kw >= 0, 1.0, -1.0)
    return kva_signed / trafo_kva


def ambient_daily(h, t_mean=30.0, t_swing=5.0, peak_hour=15.0):
    """Simple diurnal ambient temperature, degC."""
    h = np.asarray(h, dtype=float)
    return t_mean + t_swing * np.cos(2.0 * np.pi * (h - peak_hour) / 24.0)
