"""Optional bridge: per-unit transformer loading from a pandapower network.

This module is the link to the hosting-capacity line of tools
(``pvhostcap`` / ``pvhost-prob``): build a feeder in pandapower, run a
time series of load/PV dispatches, and hand the resulting transformer
loading straight into the IEEE C57.91 thermal model.

pandapower is an *optional* dependency -- importing this module without it
raises an informative error instead of breaking the core package.
"""

import numpy as np

try:
    import pandapower as pp
except ImportError:  # pragma: no cover
    pp = None


def _require_pp():
    if pp is None:
        raise ImportError(
            "pandapower is required for trafoage.pandapower_link; "
            "install it with `pip install pandapower`."
        )


def loading_from_timeseries(net, trafo_index, load_p_mw, sgen_p_mw=None,
                            dt_h=1.0):
    """Per-unit transformer loading from a manual pandapower time series.

    Parameters
    ----------
    net : pandapowerNet
        Network containing the transformer of interest.
    trafo_index : int
        Index into ``net.trafo``.
    load_p_mw : dict[int, array_like]
        Active-power series (MW) keyed by ``net.load`` index. Every series
        must have the same length; that length sets the number of steps.
    sgen_p_mw : dict[int, array_like], optional
        PV/static-generator active-power series (MW) keyed by
        ``net.sgen`` index. Positive values = generation.
    dt_h : float
        Step length in hours (returned for convenience, unused in the loop).

    Returns
    -------
    np.ndarray
        Per-unit loading ``|S| / sn_mva`` of the transformer per step
        (always non-negative; direction is irrelevant for heating).
    """
    _require_pp()
    lengths = {len(v) for d in (load_p_mw, sgen_p_mw or {}) for v in d.values()}
    if len(lengths) != 1:
        raise ValueError("all profile series must have the same length")
    n_steps = lengths.pop()
    sn_mva = float(net.trafo.sn_mva.at[trafo_index])

    k = np.empty(n_steps)
    for t in range(n_steps):
        for idx, series in load_p_mw.items():
            net.load.p_mw.at[idx] = float(series[t])
        for idx, series in (sgen_p_mw or {}).items():
            net.sgen.p_mw.at[idx] = float(series[t])
        pp.runpp(net)
        res = net.res_trafo.loc[trafo_index]
        s_mva = abs(complex(res.p_hv_mw, res.q_hv_mvar))
        k[t] = s_mva / sn_mva
    return k


def demo_feeder():
    """Tiny 2-bus LV feeder (for tests and examples).

    0.4 kV, one 400 kVA Dyn transformer feeding a lumped 200 kW load bus
    with 150 kWp of rooftop PV.
    """
    _require_pp()
    net = pp.create_empty_network(sn_mva=0.4)
    hv = pp.create_bus(net, vn_kv=10.0, name="HV")
    lv = pp.create_bus(net, vn_kv=0.4, name="LV")
    pp.create_ext_grid(net, bus=hv)
    pp.create_transformer(net, hv_bus=hv, lv_bus=lv, std_type="0.4 MVA 10/0.4 kV")
    pp.create_load(net, bus=lv, p_mw=0.20, q_mvar=0.05, name="residential")
    pp.create_sgen(net, bus=lv, p_mw=0.0, q_mvar=0.0, name="rooftop PV")
    return net
