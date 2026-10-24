import numpy as np
import plotly.graph_objects as go
from math import lgamma

from data import Data

x = np.linspace(0, 1, 601)
MU, SIGMA = 0.5, 0.25


def perfect_normal(x, mu=MU, sigma=SIGMA):
    """Peak = 1 at mu; nonzero at the extremes for sigma ~0.25."""
    return np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def binom(trials, rate, x=x, height=0.9, bw=None, sigma=None):
    """Exact binomial proportion (k/trials), smoothed, peak scaled to `height`.
    sigma: if given, the smoothing width is chosen so the total SD equals sigma,
           which makes the curve follow a normal with that SD."""
    n, p = int(trials), float(np.clip(rate, 1e-9, 1 - 1e-9))
    k = np.arange(n + 1)
    logpmf = np.array([lgamma(n + 1) - lgamma(i + 1) - lgamma(n - i + 1) for i in k]) \
             + k * np.log(p) + (n - k) * np.log(1 - p)
    pmf = np.exp(logpmf)
    if sigma is not None:
        bw = np.sqrt(max(sigma**2 - p * (1 - p) / n, 1e-6))
    else:
        bw = bw or max(0.02, 0.6 / n)
    z = (x[:, None] - (k / n)[None, :]) / bw
    y = (pmf[None, :] * np.exp(-0.5 * z**2)).sum(axis=1)
    return height * y / y.max()


def make_data(y, name, color, width=2, dash=None, fill=None):
    """Wrap one curve in a single-trace Figure and return it as a Data object."""
    trace = go.Scatter(
        x=x, y=y, name=name, mode="lines",
        line=dict(color=color, width=width, **({"dash": dash} if dash else {})),
        **({"fill": "tozeroy", "fillcolor": fill} if fill else {}),
    )
    fig = go.Figure(trace)
    fig.update_layout(
        xaxis_title="Mean Squared Error",
        yaxis_title="Relative density (peak = 1)",
        xaxis=dict(range=[0, 1]),
        yaxis=dict(range=[0, 1.05]),
    )
    return Data(histogram=fig, name=name, color=color)


sample_data = [
    make_data(binom(50, 0.50, height=1.0, sigma=SIGMA), "Composite", "grey",
              fill="rgba(200,200,200,0.75)"),
    make_data(binom(20, 0.30), "Binomial n=20, p=0.3", "#636EFA"),
    make_data(binom(30, 0.65), "Binomial n=30, p=0.65", "#EF553B"),
    make_data(perfect_normal(x), "Perfect Normal", "black", width=3, dash="dot"),
]


if __name__ == "__main__":
    combined = go.Figure()
    for d in sample_data:
        combined.add_traces(d.histogram.data)
    combined.update_layout(sample_data[0].histogram.layout)
    combined.show()