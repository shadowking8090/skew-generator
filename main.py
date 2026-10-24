# Imports

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


# Figure and display

# Trace order is draw order (first = furthest back):
# always-shown traces, then the hover-preview trace, then checked rows.
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
    line=dict(color='orange', width=3, dash='dash'),
    opacity=0.6,
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

def show_preview(event: events.GenericEventArguments) -> None:
    global hovered_name
    row = event.args.get('data') or {}
    name = row.get('name')
    if name == hovered_name:
        return
    hovered_name = name
    data = data_by_name.get(name)
    if data is None:
        fig.data[PREVIEW].visible = False
    else:
        fig.data[PREVIEW].update(x=data.trace.x, y=data.trace.y,
                           name=f'{name} preview', visible=True)
    plot.update()

def hide_preview() -> None:
    global hovered_name
    if hovered_name is None:
        return
    hovered_name = None
    fig.data[PREVIEW].visible = False
    plot.update()


# Adds or removes the row's trace on the main plot when checking
async def on_row_checked(event: events.GenericEventArguments) -> None:
    row = event.args.get('data') or {}
    checked = event.args.get('selected')

    if checked is None and event.args.get('rowId') is not None:
        checked = await grid.run_row_method(event.args['rowId'], 'isSelected')
    data = data_by_name.get(row.get('name'))
    if data is None or checked is None:
        return

    shown = any(t.name == data.name for t in fig.data[PREVIEW + 1:])
    if checked and not shown:
        fig.add_trace(go.Scatter(data.trace, showlegend=False))
    elif not checked and shown:
        fig.data = list(fig.data[:PREVIEW + 1]) + [t for t in fig.data[PREVIEW + 1:] if t.name != data.name]
    plot.update()


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