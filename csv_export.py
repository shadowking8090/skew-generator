"""Sample SKEW's current composite curve and download a CSV.

Put this file beside main.py. Call download_csv from the existing button's
callback, passing the requested count and the Composite trace's current x/y:

    from csv_export import download_csv

    def on_download():
        curve = fig.data[COMPOSITE]
        download_csv(
            amount_input.value,          # replace with your number input
            curve.x,
            curve.y,
            selected_factors=checked_names,
        )

Read curve.x/y inside the callback so each download uses the current selection.
No main.py/sampleData.py import is needed. No button is created here.
The CSV contains continuous synthetic MSE scores, not individual test answers.
"""

import csv
import io
from collections.abc import Iterable
from numbers import Integral, Real
from secrets import randbits

import numpy as np


MAX_POINTS = 100000 


def _resolve_seed(seed: int | None) -> int:
    if seed is None:
        return randbits(32)
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, Integral) or seed < 0:
        raise ValueError("seed must be a nonnegative integer or None")
    return int(seed)


def sample_curve(
    num_points: int | float,
    x_values,
    y_values,
    *,
    seed: int | None = None,
) -> np.ndarray:
    """Draw independent values from the area under a nonnegative curve.

    Accept whole-number floats because NiceGUI number inputs can return floats.
    Values of x must increase strictly and lie within [0, 1]. Heights need not
    be normalized: multiplying every height by a constant has no effect.
    Between supplied points, the density is treated as a straight line.
    """
    if (
        isinstance(num_points, (bool, np.bool_))
        or not isinstance(num_points, Real)
        or not 1 <= num_points <= MAX_POINTS
        or int(num_points) != num_points
    ):
        raise ValueError(f"num_points must be a whole number from 1 to {MAX_POINTS:,}")
    count = int(num_points)

    x = np.array(x_values, dtype=float, copy=True)
    y = np.array(y_values, dtype=float, copy=True)
    if x.ndim != 1 or y.ndim != 1 or x.size != y.size or x.size < 2:
        raise ValueError("x_values and y_values must be 1D arrays of equal length >= 2")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("The curve must contain only finite numbers")
    if np.any(np.diff(x) <= 0) or x[0] < 0 or x[-1] > 1:
        raise ValueError("x_values must increase strictly within [0, 1]")
    if np.any(y < 0) or y.max() <= 0:
        raise ValueError("y_values must be nonnegative with a positive area")

    # Rescale for stability; relative probabilities remain unchanged.
    y /= y.max()
    widths = np.diff(x)
    areas = widths * (y[:-1] + y[1:]) / 2
    cumulative = np.concatenate(([0.0], np.cumsum(areas)))
    total_area = cumulative[-1]
    if total_area <= 0:
        raise ValueError("The curve must have positive area")

    rng = np.random.Generator(np.random.PCG64(_resolve_seed(seed)))
    # Uniform draws over total area are equivalent to a unit-area PDF/CDF.
    targets = np.minimum(rng.random(count) * total_area, np.nextafter(total_area, 0.0))
    intervals = np.searchsorted(cumulative, targets, side="right") - 1

    # Invert the integral of the linear density within each selected interval.
    # Work in relative interval coordinates to support unevenly spaced x values.
    fraction = np.clip(
        (targets - cumulative[intervals]) / areas[intervals], 0.0, 1.0
    )
    left = y[intervals]
    right = y[intervals + 1]
    area_fraction = fraction * (left + right) / 2
    root = np.sqrt(np.maximum((1 - fraction) * left**2 + fraction * right**2, 0.0))
    denominator = left + root
    position = np.divide(
        2 * area_fraction,
        denominator,
        out=np.zeros_like(fraction),
        where=denominator > 0,
    )
    position = np.clip(position, 0.0, 1.0)
    return x[intervals] + widths[intervals] * position


def build_csv(
    num_points: int | float,
    x_values,
    y_values,
    *,
    selected_factors: Iterable[str] = (),
    seed: int | None = None,
) -> bytes:
    """Return UTF-8 CSV bytes without requiring NiceGUI or writing a disk file.

    Columns: sample_id, mse, selected_factors, seed.
    A fresh seed is generated and recorded when seed=None. To repeat an export,
    pass the recorded seed with the same curve, count, and NumPy version.
    Factor names describe the scenario and do not alter the supplied curve.
    """
    actual_seed = _resolve_seed(seed)
    samples = sample_curve(num_points, x_values, y_values, seed=actual_seed)
    if isinstance(selected_factors, str):
        selected_factors = (selected_factors,)
    factors = ";".join(sorted(set(selected_factors)))

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["sample_id", "mse", "selected_factors", "seed"])
    writer.writerows(
        (index, float(value), factors, actual_seed)
        for index, value in enumerate(samples, start=1)
    )
    return output.getvalue().encode("utf-8")


def download_csv(
    num_points: int | float,
    x_values,
    y_values,
    *,
    selected_factors: Iterable[str] = (),
    seed: int | None = None,
    filename: str = "synthetic_data.csv",
) -> None:
    """Generate a CSV and trigger the connected user's NiceGUI download.

    Call from a NiceGUI event handler. Invalid inputs raise ValueError so the
    button's handler can display the message with ui.notify if desired.
    """
    from nicegui import ui

    content = build_csv(
        num_points,
        x_values,
        y_values,
        selected_factors=selected_factors,
        seed=seed,
    )
    ui.download.content(content, filename=filename, media_type="text/csv; charset=utf-8")
