import numpy as np
import plotly.graph_objects as go
from math import lgamma

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

fig = go.Figure()

fig.add_trace(go.Scatter(x=x, y=binom(50, 0.50, height=1.0, sigma=SIGMA),
                         name="Composite",
                         mode="lines", line=dict(color="grey", width=2),
                         fill="tozeroy", fillcolor="rgba(200,200,200,0.75)"))

for trials, rate in [(20, 0.30), (30, 0.65)]:
    fig.add_trace(go.Scatter(x=x, y=binom(trials, rate), name=f"Binomial n={trials}, p={rate}",
                             mode="lines", line=dict(width=2)))

fig.add_trace(go.Scatter(x=x, y=perfect_normal(x), name=f"Perfect Normal",
                         mode="lines", line=dict(color="black", width=3, dash="dot")))

fig.update_layout(xaxis_title="Mean Squared Error", yaxis_title="Relative density (peak = 1)",
                  xaxis=dict(range=[0, 1]), yaxis=dict(range=[0, 1.05]))
fig.show()