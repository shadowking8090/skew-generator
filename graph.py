# Imports

from statistics import NormalDist
from uuid import uuid4

import plotly.graph_objects as go
from nicegui import events, ui

from data import Data


# Sample data

def bell_samples(mean: float, spread: float = 4, count: int = 2000) -> list[float]:
    """Create evenly spaced normal-distribution samples for a smooth bell shape."""
    distribution = NormalDist(mean, spread)
    return [distribution.inv_cdf((i + 0.5) / count) for i in range(count)]


# Keep the original objects in Python; only row metadata goes to the browser.
data_items: dict[str, Data] = {}

# Histogram figure and display

# Demo histogram bins; incoming figures retain their own bin settings.
histogram_bins = dict(start=10, end=50, size=0.75)
fig = go.Figure(go.Histogram(
    x=bell_samples(30),
    name='Current',
    xbins=histogram_bins,
    marker_color='#6366f1',
))

fig.update_layout(
    height=240,
    margin=dict(l=45, r=15, t=15, b=40),
    template='plotly_white',
    showlegend=False,
    xaxis=dict(title='Value'),
    yaxis=dict(title='Count / value'),
    barmode='overlay',
    uirevision='keep-view',
)

plot = ui.plotly(fig).classes('w-full').style('max-width: 640px; height: 240px')


# Hover state and callbacks

hovered_id = None


def preview_traces(item: Data) -> list:
    """Copy all traces so preview styling never changes the original figure."""
    traces = list(go.Figure(item.histogram).data)
    for trace in traces:
        trace.update(name=item.name, opacity=0.25, visible=True)
        if hasattr(trace, 'marker'):
            trace.update(marker_color=item.color)
        if hasattr(trace, 'line'):
            trace.update(line_color=item.color)
        if hasattr(trace, 'fillcolor'):
            trace.update(fillcolor=item.color)
    return traces


def show_preview(event: events.GenericEventArguments) -> None:
    global hovered_id
    row_id = (event.args.get('data') or {}).get('id')
    if row_id not in data_items:
        hide_preview()
        return
    if row_id == hovered_id:
        return
    hovered_id = row_id
    fig.data = fig.data[:1]
    fig.add_traces(preview_traces(data_items[row_id]))
    plot.update()


def hide_preview() -> None:
    global hovered_id
    if hovered_id is None:
        return
    hovered_id = None
    fig.data = fig.data[:1]
    plot.update()


# Gets data from the selected row in the grid when checking
async def on_row_checked(event: events.GenericEventArguments) -> None:
    row = event.args.get('data') or {}
    checked = event.args.get('selected')

    if checked is None and event.args.get('rowId') is not None:
        checked = await grid.run_row_method(event.args['rowId'], 'isSelected')
    if not row or checked is None:
        return

    # This is your original Data object, including its histogram figure.
    item = data_items.get(row.get('id'))
    if item is None:
        return

    # Add your own processing with item.histogram, item.name, and item.color.
    action = 'Checked' if checked else 'Unchecked'
    ui.notify(f"{action}: {item.name} ({item.color})")


# Data grid
grid = ui.aggrid({
    'defaultColDef': {'flex': 1, 'minWidth': 100},
    'columnDefs': [
        {'field': 'name', 'headerName': 'Name'},
        {'field': 'color', 'headerName': 'Color'}
    ],
    'rowData': [],
    ':getRowId': 'params => params.data.id',
    'rowSelection': {'mode': 'multiRow'},
}).classes('w-full').style('max-width: 640px; height: 210px')




def add_data(item: Data) -> str:
    """Add a Data object to the grid and return its unique row ID.

    Example: add_data(Data(my_figure, 'Experiment A', '#22c55e'))
    Duplicate names are allowed because rows use independent IDs.
    """
    if not isinstance(item, Data):
        raise TypeError('Expected a Data object')
    if not isinstance(item.histogram, go.Figure):
        raise TypeError('Data.histogram must be a Plotly Figure')
    preview_traces(item)  # Validate the figure and color before adding the row.
    row_id = uuid4().hex
    data_items[row_id] = item
    grid.options['rowData'].append({
        'id': row_id,
        'name': item.name,
        'color': item.color,
    })
    grid.update()
    return row_id


# Checkbox and hover event connections

grid.on('rowSelected', on_row_checked, ['data', 'selected', 'rowId'])
grid.on('cellMouseOver', show_preview, ['data'])
grid.on('mouseout', hide_preview, js_handler='''(event) => {
    const row = event.target.closest('.ag-row');
    if (row && !row.contains(event.relatedTarget)) emit();
}''')
grid.on('mouseleave', hide_preview)



# Demo objects: replace these with add_data(your_data_object) calls.
for name, age, color in [
    ('Alice', 25, '#f97316'),
    ('Bob', 30, '#22c55e'),
    ('Charlie', 35, '#ec4899'),
]:
    histogram = go.Figure(go.Histogram(x=bell_samples(age), xbins=histogram_bins))
    add_data(Data(histogram, name, color))


# Start the app

ui.run()

