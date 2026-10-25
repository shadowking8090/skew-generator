# Imports

import numpy as np
import plotly.graph_objects as go
from nicegui import events, ui
from graph_entrance import animate_graph_loading

from sampleData import LAYOUT, sample_data
    
from data import Data

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
    fill='tozeroy',
    opacity=0.45,
    visible=False,
    showlegend=False,
))

fig.update_layout(
    **LAYOUT,
    autosize=True,
    margin=dict(l=65, r=16, t=20, b=60),
    template='plotly_white',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Arial, sans-serif', size=16, weight=700, color='#f1f5f9'),
    hoverlabel=dict(bgcolor='#26292f', font=dict(weight=700, color='#f1f5f9')),
    showlegend=False,
    uirevision='keep-view',
    # Hover tooltips only: no drag/zoom/pan
    hovermode='closest',
    dragmode=False,
    xaxis_fixedrange=True,
    yaxis_fixedrange=True,
)
fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, ticks='', title_font_size=28, automargin=True)
fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, ticks='', title_font_size=28, automargin=True)

# Hide the toolbar (zoom, pan, download, etc.) and the legend
ui.add_css('''
    body {
        min-height: 100vh;
        isolation: isolate;
        background-color: #191b1f;
        background-image:
            repeating-linear-gradient(45deg, rgba(255,255,255,0.055) 0 1px, transparent 1px 40px),
            repeating-linear-gradient(-45deg, rgba(255,255,255,0.055) 0 1px, transparent 1px 40px),
            radial-gradient(ellipse at top left, #3c4047 0%, #26292f 45%, #17191d 100%);
        background-size: auto, auto, 100% 100%;
        background-attachment: fixed;
    }
    /* Fixed ambient layers stay behind the app and never intercept clicks. */
    body::before,
    body::after {
        content: '';
        position: fixed;
        inset: -20vh -20vw;
        pointer-events: none;
        z-index: -1;
        will-change: transform, opacity;
    }
    body::before {
        background:
            radial-gradient(ellipse at 20% 30%, #6366f16b 0%, transparent 42%),
            radial-gradient(ellipse at 80% 60%, #06b6d44d 0%, transparent 40%),
            radial-gradient(ellipse at 50% 85%, #a855f74d 0%, transparent 38%);
        filter: blur(45px);
        animation: ambient-drift 24s ease-in-out infinite alternate;
    }
    body::after {
        background:
            radial-gradient(ellipse at 65% 25%, #c4b5fd30 0%, transparent 30%),
            radial-gradient(ellipse at 25% 70%, #67e8f930 0%, transparent 35%);
        filter: blur(28px);
        animation: ambient-drift 18s ease-in-out -9s infinite alternate-reverse;
    }
    @keyframes ambient-drift {
        0% { transform: translate3d(-4%, -3%, 0) rotate(-5deg) scale(1); opacity: .65; }
        50% { transform: translate3d(3%, 4%, 0) rotate(2deg) scale(1.08); opacity: 1; }
        100% { transform: translate3d(5%, -2%, 0) rotate(7deg) scale(1.04); opacity: .8; }
    }
    @media (prefers-reduced-motion: reduce) {
        body::before, body::after { animation: none; will-change: auto; }
    }
    .nicegui-content {
        background: transparent; font-weight: 700;
        width: 100%; box-sizing: border-box;
        padding: clamp(12px, 3vw, 32px); align-items: center;
    }
    .responsive-chart {
        width: 100%; max-width: 1100px; min-width: 0;
        height: clamp(280px, 55svh, 520px);
    }
    .compact-grid {
        width: 100%; max-width: 800px; min-width: 0;
        margin-top: clamp(16px, 5svh, 48px);
    }
    @media (max-width: 600px) {
        .responsive-chart .xtitle,
        .responsive-chart .ytitle { font-size: 22px !important; }
    }
    .js-plotly-plot text,
    .compact-grid .ag-cell,
    .compact-grid .ag-header-cell-text { font-weight: 700 !important; }
''')
ui.add_css('.modebar-container, .js-plotly-plot .legend { display: none !important; }')

plot = ui.plotly(fig).classes('responsive-chart self-center')
animate_graph_loading(plot)


# Hover state and callbacks

hovered_name = None

def update_preview() -> None:
    """Fill the hovered curve in its own color at the composite's scale.

    Partial opacity lets overlapping filled areas blend into a different color.
    The preview disappears when no row is hovered.
    """
    data = data_by_name.get(hovered_name)
    if data is None:
        fig.data[PREVIEW].visible = False
        return
    scale = scale_for(checked_names | {data.name})
    fig.data[PREVIEW].update(x=data.trace.x, y=scale * np.asarray(data.trace.y),
                             name=f'{data.name} preview', visible=True,
                             line_color=data.color, fillcolor=data.color)

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
    Binomials appear as colored, filled hover previews, which are redrawn here
    at the new scale."""
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

def add_data(item: Data) -> None:
    """Add a Data object to the grid; call after the grid has been created.

    Example: add_data(Data(go.Scatter(x=[0, 1], y=[0, 1]), 'New curve', 'red'))
    Names must be unique because the hover and checkbox callbacks use them.
    """
    if not isinstance(item, Data):
        raise TypeError('add_data expects a Data object')
    if not isinstance(item.trace, go.Scatter):
        raise TypeError('Data.trace must be a go.Scatter trace, not a Figure')
    if item.name in data_by_name or item.name in ALWAYS_SHOWN:
        raise ValueError(f'A row or fixed curve named {item.name!r} already exists')

    # Validate styling before changing the grid or its lookup table.
    go.Scatter(item.trace, name=item.name, line_color=item.color)
    data_by_name[item.name] = item
    selectable_data.append(item)
    grid.options['rowData'].append({'name': item.name})
    grid.update()


# Data grid
ui.add_css('''
    .compact-grid .ag-layout-auto-height .ag-center-cols-viewport,
    .compact-grid .ag-layout-auto-height .ag-center-cols-container {
        min-height: 0 !important;
    }
    .compact-grid .ag-checkbox-input-wrapper:focus-within,
    .compact-grid .ag-checkbox-input:focus {
        outline: none !important;
        box-shadow: none !important;
    }
''')

grid = ui.aggrid({
    'defaultColDef': {'flex': 1, 'minWidth': 100, 'resizable': False},
    'selectionColumnDef': {'resizable': False},
    'domLayout': 'autoHeight',
    'columnDefs': [
        {'field': 'name', 'headerName': 'Name', 'wrapText': True, 'autoHeight': True},
    ],
    'rowData': [{'name': d.name} for d in selectable_data],
    'rowSelection': {
        'mode': 'multiRow',
        'checkboxes': True,
        'headerCheckbox': False,
        'enableClickSelection': False,
    },
    'suppressCellFocus': True,
}).classes('w-full self-center compact-grid').style(
    'height: auto; resize: none'
)

grid.on('rowSelected', on_row_checked, ['data', 'selected', 'rowId'])
grid.on('cellMouseOver', show_preview, ['data'])
grid.on('mouseout', hide_preview, js_handler='''(event) => {
    const row = event.target.closest('.ag-row');
    if (row && !row.contains(event.relatedTarget)) emit();
}''')
grid.on('mouseleave', hide_preview)

# Start the app

ui.run()
