"""Insulation aging per IEEE Std C57.91-2011.

The aging acceleration factor is an Arrhenius-type law anchored at the
reference hot-spot temperature of 110 C, where F_AA = 1 by definition::

    F_AA = exp(15000/383 - 15000/(theta_H + 273))

The equivalent aging factor over a period averages F_AA over time, and the
percentage loss of insulation life divides by the guide's normal insulation
life of 180,000 h (~20.5 years at reference temperature)::

    F_EQA   = sum(F_AA,n * dt_n) / sum(dt_n)
    %LOL    = F_EQA * t * 100 / 180000
    hours consumed = F_EQA * t
"""

import numpy as np

NORMAL_LIFE_H = 180_000.0  # normal insulation life at 110 C hot-spot, hours
REFERENCE_THETA_H = 110.0  # degC, F_AA == 1 by definition here


def faa(theta_h):
    """Aging acceleration factor for hot-spot temperature(s) in degC."""
    theta_h = np.asarray(theta_h, dtype=float)
    return np.exp(15000.0 / 383.0 - 15000.0 / (theta_h + 273.0))


def feqa(faa_series):
    """Equivalent aging factor: time-average of the F_AA series."""
    faa_series = np.asarray(faa_series, dtype=float)
    if faa_series.size == 0:
        raise ValueError("faa_series must be non-empty")
    return float(np.mean(faa_series))


def loss_of_life_percent(feqa_value, hours, normal_life_h=NORMAL_LIFE_H):
    """Percentage of normal insulation life consumed."""
    return feqa_value * hours * 100.0 / normal_life_h


def life_hours_consumed(feqa_value, hours):
    """Equivalent hours of insulation life consumed at reference temperature."""
    return feqa_value * hours


def summarize(faa_series, theta_h_series, dt_h):
    """One-dict summary of an aging run.

    Returns F_EQA, total hours, equivalent life-hours consumed, % loss of
    life, peak hot-spot temperature and the fraction of time the hot-spot
    spent above the 110 C reference.
    """
    faa_series = np.asarray(faa_series, dtype=float)
    theta_h_series = np.asarray(theta_h_series, dtype=float)
    if faa_series.shape != theta_h_series.shape:
        raise ValueError("faa_series and theta_h_series must match in shape")
    hours = faa_series.size * dt_h
    feqa_value = feqa(faa_series)
    return {
        "feqa": feqa_value,
        "hours": hours,
        "life_hours_consumed": life_hours_consumed(feqa_value, hours),
        "loss_of_life_percent": loss_of_life_percent(feqa_value, hours),
        "theta_h_max": float(np.max(theta_h_series)),
        "frac_time_above_110c": float(np.mean(theta_h_series > REFERENCE_THETA_H)),
    }
