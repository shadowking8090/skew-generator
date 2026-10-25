# Imports

import numpy as np
import plotly.graph_objects as go
from nicegui import app, events, ui

from sampleData import LAYOUT, sample_data
    
from data import Data
from transitions import animate_traces, hide_curve, rescale_curve, show_curve
import theme

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

# A small pool of hover-preview traces. Each hover claims the next one, so the
# row you just left can shrink away on its own trace while the new row grows in.
PREVIEW = len(always_data)  # index of the first preview trace
PREVIEW_SLOTS = 4
for slot in range(PREVIEW_SLOTS):
    fig.add_trace(go.Scatter(
        x=[], y=[],
        name=f'Row preview {slot}',
        mode='lines',
        line=dict(color=theme.PALETTE['preview'], width=2, dash='dot'),  # recolored per row on hover
        visible=False,
        showlegend=False,
        hoverinfo='skip',
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

# Palette and font on the figure layout and axes (trace colors come from sampleData.py)
theme.style_figure(fig)

# Hide the toolbar (zoom, pan, download, etc.) and the legend
ui.add_css('.modebar-container, .js-plotly-plot .legend { display: none !important; }')

# Theme: serves ./static, loads the TTF font, colors the page and grid, then the header bar
theme.setup()
theme.header()

# Everything below sits in one centered column. The plot and the table are the same width,
# and the whole block is scaled to fit the window (theme.fit_to_screen).
TITLE = 'left and right accuracy'.upper()
SUBTITLE = 'what is love?'.upper()

content = theme.fit_to_screen()
with content:
    theme.heading(TITLE, SUBTITLE)
    plot = ui.plotly(fig).classes('theme-card').style(f'width: {theme.CONTENT_WIDTH}px; height: 240px')


# Hover state and callbacks

hovered_name = None
active_slot = None   # trace index of the preview for the hovered row
next_slot = 0        # round-robin counter for claiming preview traces

def update_preview(rescale_only: bool = False) -> None:
    """Draw the hovered row's curve (dotted, in that row's color) at the height it
    has in the composite, whether or not the row is checked.

    The previous row's preview always shrinks away on its own trace, including
    when the mouse goes straight from one row to another. Everything is sent
    straight to the browser; plot.update() would resend the whole figure and
    snap the composite / cancel its transition."""
    global active_slot, next_slot
    data = data_by_name.get(hovered_name)

    if data is None:                          # nothing hovered: shrink the active preview
        if not rescale_only and active_slot is not None:
            fig.data[active_slot].visible = False
            hide_curve(plot, active_slot)
            active_slot = None
        return

    scale = scale_for(checked_names | {data.name})
    x, y = data.trace.x, scale * np.asarray(data.trace.y)

    if rescale_only:                          # composite scale changed: no grow/shrink
        if active_slot is not None:
            fig.data[active_slot].update(y=y)
            rescale_curve(plot, active_slot, y)
        return

    if active_slot is not None:               # moved to another row: old one shrinks
        fig.data[active_slot].visible = False
        hide_curve(plot, active_slot)
    active_slot = PREVIEW + next_slot % PREVIEW_SLOTS
    next_slot += 1
    fig.data[active_slot].update(x=x, y=y, name=f'{data.name} preview',
                                 line_color=data.color, visible=True)
    show_curve(plot, active_slot, x, y, color=data.color)   # grows from 0 height

def show_preview(event: events.GenericEventArguments) -> None:
    global hovered_name
    row = event.args.get('data') or {}
    name = row.get('name')
    if name == hovered_name:
        return
    hovered_name = name
    update_preview()

def hide_preview() -> None:
    global hovered_name
    if hovered_name is None:
        return
    hovered_name = None
    update_preview()


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
    Binomials are never drawn as solid traces; they only appear (dotted, in the row's color)
    as the hover preview, which is redrawn here at the new scale."""
    old_y = np.asarray(fig.data[COMPOSITE].y)
    new_y = scale_for(checked_names) * composite_raw(checked_names)
    fig.data[COMPOSITE].y = new_y   # keep the server-side figure in sync
    update_preview(rescale_only=True)   # preview follows the new scale, no grow/shrink

    # Only the composite tweens; nothing here calls plot.update().
    animate_traces(plot, {COMPOSITE: new_y}, starts={COMPOSITE: old_y})


# Syncs the checked binomials with the grid's selection
async def on_selection_changed(event: events.GenericEventArguments) -> None:
    """Runs once per selection change, however many rows changed. Select-all and
    deselect-all select every row in one go, so reading the whole selection here
    gives one composite update (one smooth transition) instead of one per row."""
    rows = await grid.get_selected_rows()
    names = {row.get('name') for row in rows} & data_by_name.keys()
    if names == checked_names:
        return
    checked_names.clear()
    checked_names.update(names)
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
    grid.options['rowData'].append({'name': item.name, 'color': item.color})
    grid.update()


# Data grid. The first column is a color swatch matching the row's preview color.
COLOR_SWATCH = '''params => {
    const dot = document.createElement('span');
    dot.style.cssText = 'display:inline-block; width:12px; height:12px; border-radius:50%; '
        + 'vertical-align:middle; box-shadow:0 0 0 1px rgba(15,27,45,0.12); background:' + params.value;
    return dot;
}'''

# Fixed layout: every size below is in pixels, so the table never reflows.
SELECT_W, SWATCH_W = 48, 48                                  # checkbox and color columns
NAME_W = theme.CONTENT_WIDTH - 2 - SELECT_W - SWATCH_W       # 2 = the card's border
GRID_ROW_H = GRID_HEADER_H = 40

with content:
    grid = ui.aggrid({
        # No flex, resizing, sorting, reordering or header menus: columns keep their widths.
        'defaultColDef': {'resizable': False, 'sortable': False, 'suppressMovable': True,
                          'suppressHeaderMenuButton': True},
        'columnDefs': [
            {'field': 'color', 'headerName': '', ':cellRenderer': COLOR_SWATCH,
             'width': SWATCH_W, 'minWidth': SWATCH_W, 'maxWidth': SWATCH_W},
            {'field': 'name', 'headerName': 'Name', 'width': NAME_W},
        ],
        'selectionColumnDef': {'width': SELECT_W, 'minWidth': SELECT_W, 'maxWidth': SELECT_W,
                               'resizable': False},
        'rowData': [{'name': d.name, 'color': d.color} for d in selectable_data],
        'rowSelection': {'mode': 'multiRow'},
        'domLayout': 'autoHeight',       # as tall as its rows, so there is never a scrollbar
        'rowHeight': GRID_ROW_H,
        'headerHeight': GRID_HEADER_H,
        'suppressCellFocus': True,
        'suppressHorizontalScroll': True,
    }).classes('theme-card').style(f'width: {theme.CONTENT_WIDTH}px; height: auto')

grid.on('selectionChanged', on_selection_changed)
grid.on('cellMouseOver', show_preview, ['data'])
grid.on('mouseout', hide_preview, js_handler='''(event) => {
    const row = event.target.closest('.ag-row');
    if (row && !row.contains(event.relatedTarget)) emit();
}''')
grid.on('mouseleave', hide_preview)

# Start the app

ui.run(title='SKEW')