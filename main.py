# Imports

import numpy as np
import plotly.graph_objects as go
from nicegui import events, ui

from sampleData import LAYOUT, sample_data


# Sample data

# Always plotted, never listed in the grid
ALWAYS_SHOWN = {'Composite', 'Perfect Normal'}
NOT_HOVERABLE = {'Perfect Normal'}

always_data = [d for d in sample_data if d.name in ALWAYS_SHOWN]
selectable_data = [d for d in sample_data if d.name not in ALWAYS_SHOWN]
data_by_name = {d.name: d for d in selectable_data}

# The composite starts as the base Composite curve; checked binomials add to it.
COMPOSITE = next(i for i, d in enumerate(always_data) if d.name == 'Composite')
base_y = np.asarray(always_data[COMPOSITE].trace.y)
checked_names: set[str] = set()


# Figure and display

# Trace order is draw order (first = furthest back):
# always-shown traces, then the hover-preview trace (the only place a binomial is drawn).
fig = go.Figure()

for d in always_data:
    fig.add_trace(go.Scatter(
        d.trace,
        showlegend=False,
        hoverinfo='skip' if d.name in NOT_HOVERABLE else None,
    ))

PREVIEW = len(always_data)  # index of the hover-preview trace
fig.add_trace(go.Scatter(
    x=[], y=[],
    name='Row preview',
    mode='lines',
    line=dict(color='orange', width=2, dash='dot'),
    visible=False,
    showlegend=False,
))

fig.update_layout(
    **LAYOUT,
    height=240,
    margin=dict(l=45, r=15, t=15, b=40),
    template='plotly_white',
    showlegend=False,
    uirevision='keep-view',
    # Hover tooltips only: no drag/zoom/pan
    hovermode='closest',
    dragmode=False,
    xaxis_fixedrange=True,
    yaxis_fixedrange=True,
)

# Hide the toolbar (zoom, pan, download, etc.) and the legend
ui.add_css('.modebar-container, .js-plotly-plot .legend { display: none !important; }')

plot = ui.plotly(fig).classes('w-full').style('max-width: 640px; height: 240px')


# Hover state and callbacks

hovered_name = None

def update_preview() -> None:
    """Draw the hovered row's curve (orange, dotted) at the height it has in the
    composite, whether or not the row is checked. Hidden when nothing is hovered."""
    data = data_by_name.get(hovered_name)
    if data is None:
        fig.data[PREVIEW].visible = False
        return
    scale = scale_for(checked_names | {data.name})
    fig.data[PREVIEW].update(x=data.trace.x, y=scale * np.asarray(data.trace.y),
                             name=f'{data.name} preview', visible=True)

def show_preview(event: events.GenericEventArguments) -> None:
    global hovered_name
    row = event.args.get('data') or {}
    name = row.get('name')
    if name == hovered_name:
        return
    hovered_name = name
    update_preview()
    plot.update()

def hide_preview() -> None:
    global hovered_name
    if hovered_name is None:
        return
    hovered_name = None
    update_preview()
    plot.update()


def composite_raw(names: set[str]) -> np.ndarray:
    """Base composite plus every binomial in `names` (unscaled)."""
    chosen = [d for d in selectable_data if d.name in names]
    return base_y + sum((np.asarray(d.trace.y) for d in chosen), np.zeros_like(base_y))

def scale_for(names: set[str]) -> float:
    """Factor that brings the composite of `names` to a peak of 1."""
    return 1 / composite_raw(names).max()


# Rebuilds the composite for the checked binomials
def refresh_plot() -> None:
    """Composite = base + every checked binomial, rescaled so its peak is 1.
    Binomials are never drawn as solid traces; they only appear (orange, dotted)
    as the hover preview, which is redrawn here at the new scale."""
    fig.data[COMPOSITE].y = scale_for(checked_names) * composite_raw(checked_names)
    update_preview()
    plot.update()


# Adds or removes the row's binomial when checking
async def on_row_checked(event: events.GenericEventArguments) -> None:
    row = event.args.get('data') or {}
    checked = event.args.get('selected')

    if checked is None and event.args.get('rowId') is not None:
        checked = await grid.run_row_method(event.args['rowId'], 'isSelected')
    data = data_by_name.get(row.get('name'))
    if data is None or checked is None:
        return

    if checked:
        checked_names.add(data.name)
    else:
        checked_names.discard(data.name)
    refresh_plot()


# Data grid
grid = ui.aggrid({
    'defaultColDef': {'flex': 1, 'minWidth': 100},
    'columnDefs': [
        {'field': 'name', 'headerName': 'Name'},
    ],
    'rowData': [{'name': d.name} for d in selectable_data],
    'rowSelection': {'mode': 'multiRow'},
}).classes('w-full').style('max-width: 640px; height: 210px')

grid.on('rowSelected', on_row_checked, ['data', 'selected', 'rowId'])
grid.on('cellMouseOver', show_preview, ['data'])
grid.on('mouseout', hide_preview, js_handler='''(event) => {
    const row = event.target.closest('.ag-row');
    if (row && !row.contains(event.relatedTarget)) emit();
}''')
grid.on('mouseleave', hide_preview)

# Start the app

ui.run()