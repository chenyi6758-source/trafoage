"""trafoage: distribution-transformer thermal aging under DER scenarios.

Implements the IEEE Std C57.91-2011 transient thermal model and insulation
aging law, wired to DER loading scenarios (PV, EV charging, heat pumps) and
optionally to pandapower time-series results.
"""

from .thermal import Transformer, simulate, ultimate_rises, corrected_tau_to
from .aging import (faa, feqa, loss_of_life_percent, life_hours_consumed,
                    summarize, NORMAL_LIFE_H, REFERENCE_THETA_H)
from .scenarios import (hours_of_day, residential_base, pv_shape, ev_shape,
                        heatpump_shape, make_loading, ambient_daily)

__version__ = "0.1.0"

__all__ = [
    "Transformer", "simulate", "ultimate_rises", "corrected_tau_to",
    "faa", "feqa", "loss_of_life_percent", "life_hours_consumed",
    "summarize", "NORMAL_LIFE_H", "REFERENCE_THETA_H",
    "hours_of_day", "residential_base", "pv_shape", "ev_shape",
    "heatpump_shape", "make_loading", "ambient_daily",
]
