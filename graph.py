# Imports

from statistics import NormalDist

import plotly.graph_objects as go
from nicegui import events, ui


# Sample data

def bell_samples(mean: float, spread: float = 4, count: int = 2000) -> list[float]:
    """Create evenly spaced normal-distribution samples for a smooth bell shape."""
    distribution = NormalDist(mean, spread)
    return [distribution.inv_cdf((i + 0.5) / count) for i in range(count)]


# Each preview is centered on the corresponding person's age.
row_samples = {
    'Alice': bell_samples(25),
    'Bob': bell_samples(30),
    'Charlie': bell_samples(35),
}

# Histogram figure and display

# Shared bins and fixed axes keep the main chart and previews comparable.
histogram_bins = dict(start=10, end=50, size=0.75)
fig = go.Figure(go.Histogram(
    x=bell_samples(30),
    name='Current',
    xbins=histogram_bins,
    marker_color='#6366f1',
))

fig.add_trace(go.Histogram(
    x=[],
    name='Row preview',
    opacity=0.25,
    marker_color='orange',
    xbins=histogram_bins,
    visible=False,
))

fig.update_layout(
    height=240,
    margin=dict(l=45, r=15, t=15, b=40),
    template='plotly_white',
    showlegend=False,
    xaxis=dict(title='Age', range=[10, 50]),
    yaxis=dict(title='Count', range=[0, 170]),
    barmode='overlay',
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
    samples = row_samples.get(name, [])
    fig.data[1].update(x=samples, name=f'{name} preview', visible=bool(samples))
    plot.update()

def hide_preview() -> None:
    global hovered_name
    if hovered_name is None:
        return
    hovered_name = None
    fig.data[1].visible = False
    plot.update()


# Gets data from the selected row in the grid when checking
async def on_row_checked(event: events.GenericEventArguments) -> None:
    row = event.args.get('data') or {}
    checked = event.args.get('selected')

    if checked is None and event.args.get('rowId') is not None:
        checked = await grid.run_row_method(event.args['rowId'], 'isSelected')
    if not row or checked is None:
        return

    # Add your own processing here. This example displays the received values.
    action = 'Checked' if checked else 'Unchecked'
    ui.notify(f"{action}: {row.get('name')}, age {row.get('age')}")


# Data grid
grid = ui.aggrid({
    'defaultColDef': {'flex': 1, 'minWidth': 100},
    'columnDefs': [
        {'field': 'name', 'headerName': 'Name'},
        {'field': 'age', 'headerName': 'Age'}
    ],
    'rowData': [
        {'name': 'Alice', 'age': 25},
        {'name': 'Bob', 'age': 30},
        {'name': 'Charlie', 'age': 35}
    ],
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

