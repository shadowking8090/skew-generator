import math

import numpy as np
import plotly.graph_objects as go


def clamp_weight(value, default: float = 0.2) -> float:
    """Keep a population share in (0, 1]. Invalid values fall back to default."""
    try:
        weight = float(value)
    except (TypeError, ValueError):
        weight = default
    if not math.isfinite(weight) or weight <= 0:
        weight = default
    return min(weight, 1.0)


class Data:
    def __init__(self, trace: go.Scatter | go.Figure, name: str, color: str,
                 weight: float = 0.2, weight_source: str = ''):
        self.trace = trace
        self.name = name
        self.color = color
        self.weight = clamp_weight(weight)
        self.weight_source = weight_source.strip() if isinstance(weight_source, str) else ''


def _density(x, y) -> np.ndarray:
    """Rescale a curve so its area is 1. Curves are stored peak-scaled for display,
    so without this a wide curve would count for more people than a narrow one."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    area = float(np.sum((y[1:] + y[:-1]) * np.diff(x)) / 2)
    return y / area if area > 0 else y


def mixture_weights(factors: list[Data]) -> tuple[float, list[float]]:
    """(baseline share, factor shares) for the checked factors.

    Each factor's weight is the share of the population it represents; the rest
    stays on the baseline. If the shares add up to more than 1 (overlapping
    groups), they are renormalized to sum to 1 and the baseline drops out.
    """
    weights = [clamp_weight(item.weight) for item in factors]
    total = sum(weights)
    if total <= 1:
        return 1.0 - total, weights
    return 0.0, [w / total for w in weights]


def weighted_composite(base_y, factors: list[Data]) -> np.ndarray:
    """Mix the baseline with the checked factors by population share.

    Every curve is turned into a density (area 1) before mixing, so a 10% share
    means 10% of the population whatever the curve's width. The result is in
    density units; callers rescale it to a peak of 1 for display.
    """
    base = np.asarray(base_y, dtype=float)
    if not factors:
        return base.copy()
    x = factors[0].trace.x
    base_share, shares = mixture_weights(factors)
    mixed = base_share * _density(x, base)
    for share, item in zip(shares, factors):
        mixed = mixed + share * _density(item.trace.x, item.trace.y)
    return mixed


def factor_contribution(item: Data, factors: list[Data]) -> np.ndarray:
    """The part of weighted_composite(base_y, factors) that comes from `item`
    (same units), e.g. for drawing a factor's slice of the composite."""
    _, shares = mixture_weights(factors)
    share = next(s for s, f in zip(shares, factors) if f is item)
    return share * _density(item.trace.x, item.trace.y)
