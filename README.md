# Distribution Preview

A small NiceGUI app that plots probability-density-style curves with Plotly. A table lists selectable curves: hovering a row previews its curve on the plot, and checking a row adds it.

## Files

| File | Purpose |
|---|---|
| `data.py` | `Data` class: holds one curve as a Plotly `go.Scatter` trace, plus its `name` and `color`. |
| `sampleData.py` | Generates the sample curves and exposes them as `sample_data` (a list of `Data` objects) and `LAYOUT` (shared axis titles and ranges). |
| `main.py` | The NiceGUI app: plot, table, hover preview, and check/uncheck behavior. |

Keep all three in the same folder.

## Setup

```bash
pip install nicegui plotly numpy
python main.py
```

## How it works

### Data (`data.py`, `sampleData.py`)

`Data(trace, name, color)` wraps a single `go.Scatter` trace. `sampleData.py` builds four curves with `make_data(y, name, color, ...)`:

| Name | Color | Notes |
|---|---|---|
| Composite | `grey` | Binomial (n=50, p=0.5) smoothed to SD 0.25, translucent fill |
| Binomial n=20, p=0.3 | `#636EFA` | Smoothed binomial proportion |
| Binomial n=30, p=0.65 | `#EF553B` | Smoothed binomial proportion |
| Perfect Normal | `black` | Dotted line, width 3, mean 0.5 and SD 0.25 |

Each curve is plotted over `x = linspace(0, 1, 601)`, with the axes labelled "Mean Squared Error" (x) and "Relative density (peak = 1)" (y).

Running `python sampleData.py` directly merges all the traces into one figure and shows it, which is useful for previewing the curves on their own.

### App (`main.py`)

- **Always shown:** Composite and Perfect Normal are plotted on load and do not appear in the table.
- **Table:** Lists the remaining curves (the two binomials) in a single Name column, with checkboxes.
- **Hover preview:** Hovering a table row draws that curve as an orange dashed line. It disappears when the mouse leaves the table row.
- **Checking a row:** Adds that curve to the plot in its own color. Unchecking removes it.
- **Layering:** Traces are drawn in the order they are added: Composite and Perfect Normal at the back, then the hover preview, then checked rows on top.
- **Perfect Normal is not hoverable:** It has no tooltip and does not take hover from the curves beneath it.
- **Plot interactions:** Only hover tooltips are enabled. Drag, zoom, pan, legend clicks and the toolbar are all disabled or hidden, and the legend is hidden.

## Customizing

All of these are near the top of `main.py` unless noted.

- **Add a curve:** Add a `make_data(...)` entry to `sample_data` in `sampleData.py`. It appears in the table automatically.
- **Always show a curve (and hide it from the table):** Add its name to `ALWAYS_SHOWN`.
- **Make a curve unhoverable:** Add its name to `NOT_HOVERABLE`.
- **Axes:** Edit `LAYOUT` in `sampleData.py`.

Curve names must be unique, since they are used as lookup keys in the table and plot.

## Notes

- Hover preview and the checkbox handlers are wired to the grid's `cellMouseOver`, `mouseout`, `mouseleave` and `rowSelected` events.
- The plot has no zoom or pan, so the axis ranges set in `LAYOUT` are fixed.