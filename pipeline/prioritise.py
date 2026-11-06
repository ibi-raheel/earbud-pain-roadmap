"""RICE prioritisation and experiment sizing."""
from math import ceil

from scipy.stats import norm

# Effort is an ASSUMPTION (engineering person-months to move the pain meaningfully in a
# next-generation true-wireless product). It is stated, not measured, and is editable in the UI.
EFFORT_PM = {
    "fit_comfort": 6.0,       # new nozzle angle / shell geometry, tip set, ear-scan fit study
    "battery": 8.0,           # cell + power budget; firmware power states
    "charging_case": 4.0,     # hinge, magnet and pogo-contact redesign + case firmware
    "connectivity": 3.0,      # firmware / antenna tuning, mostly software
    "sound_quality": 4.0,     # tuning, driver choice
    "anc_noise": 5.0,         # mic placement + DSP
    "call_mic": 4.0,          # beamforming / DSP, vent design
    "controls": 2.0,          # touch-threshold firmware, gesture mapping
    "failure": 6.0,           # reliability: drop, sweat ingress, solder joints
    "app_software": 2.0,      # companion app / OTA
}


def rice(reach: float, impact: float, confidence: float, effort: float) -> float:
    """Reach as % of reviews, Impact in stars lost, Confidence 0-1, Effort in person-months."""
    return reach * impact * confidence / effort


def n_per_arm(p1: float, p2: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Two-sided two-proportion z-test, unpooled variance:
    n = (z_{1-a/2} + z_{1-b})^2 [p1(1-p1) + p2(1-p2)] / (p1 - p2)^2"""
    za = norm.ppf(1 - alpha / 2)
    zb = norm.ppf(power)
    return ceil((za + zb) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p1 - p2) ** 2)


def n_per_arm_statsmodels(p1: float, p2: float, alpha: float = 0.05, power: float = 0.8) -> int:
    from statsmodels.stats.power import NormalIndPower
    from statsmodels.stats.proportion import proportion_effectsize
    h = proportion_effectsize(p1, p2)
    return ceil(NormalIndPower().solve_power(effect_size=abs(h), alpha=alpha, power=power, ratio=1.0))


def effort_sensitivity(themes: list, draws: int = 5000, lo: float = 0.5, hi: float = 2.0, seed: int = 5) -> dict:
    """Because Effort is assumed, scale every theme's effort independently by a factor drawn
    log-uniformly from [lo, hi] and count how often each theme ranks first / in the top 3."""
    import numpy as np
    rng = np.random.default_rng(seed)
    base = np.array([t["rice"] * t["effort_pm"] for t in themes])  # R*I*C
    eff = np.array([t["effort_pm"] for t in themes])
    f = np.exp(rng.uniform(np.log(lo), np.log(hi), size=(draws, len(themes))))
    score = base / (eff * f)
    order = np.argsort(-score, axis=1)
    first = np.bincount(order[:, 0], minlength=len(themes)) / draws
    top3 = np.zeros(len(themes))
    for j in range(3):
        top3 += np.bincount(order[:, j], minlength=len(themes))
    top3 /= draws
    return {t["key"]: {"p_first": float(first[i]), "p_top3": float(top3[i])} for i, t in enumerate(themes)}
