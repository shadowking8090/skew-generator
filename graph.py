# Imports

import plotly.graph_objects as go
from nicegui import events, ui

from sampleData import LAYOUT, sample_data


# Sample data

data_by_name = {d.name: d for d in sample_data}


# Figure and display

# fig.data[0] is a reserved hover-preview trace; checked rows are appended after it.
fig = go.Figure(go.Scatter(
    x=[], y=[],
    name='Row preview',
    mode='lines',
    line=dict(color='orange', width=3, dash='dash'),
    opacity=0.6,
    visible=False,
))

fig.update_layout(
    **LAYOUT,
    height=240,
    margin=dict(l=45, r=15, t=15, b=40),
    template='plotly_white',
    showlegend=True,
    uirevision='keep-view',
)

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
        fig.data[0].visible = False
    else:
        fig.data[0].update(x=data.trace.x, y=data.trace.y,
                           name=f'{name} preview', visible=True)
    plot.update()

def hide_preview() -> None:
    global hovered_name
    if hovered_name is None:
        return
    hovered_name = None
    fig.data[0].visible = False
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

    shown = any(t.name == data.name for t in fig.data[1:])
    if checked and not shown:
        fig.add_trace(go.Scatter(data.trace))
    elif not checked and shown:
        fig.data = [fig.data[0]] + [t for t in fig.data[1:] if t.name != data.name]
    plot.update()


# Data grid
grid = ui.aggrid({
    'defaultColDef': {'flex': 1, 'minWidth': 100},
    'columnDefs': [
        {'field': 'name', 'headerName': 'Name'},
        {'field': 'color', 'headerName': 'Color'},
    ],
    'rowData': [{'name': d.name, 'color': d.color} for d in sample_data],
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