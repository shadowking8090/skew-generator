"""The plot + selectable grid page, built from a Project.

This is the body of the old main.py wrapped in a function. All state (figure,
checked rows, hover slots) lives inside the call, so each visit, and each
project, gets its own independent copy."""

import numpy as np
import plotly.graph_objects as go
from nicegui import events, ui

import theme
from data import Data
from downloadMenu import download_menu
from projects import Project
from transitions import animate_traces, hide_curve, rescale_curve, show_curve


def build_project_page(project: Project) -> None:
    # Data

    sample_data = project.load()
    always_shown = set(project.always_shown)
    not_hoverable = set(project.not_hoverable)

    always_data = [d for d in sample_data if d.name in always_shown]
    selectable_data = [d for d in sample_data if d.name not in always_shown]
    data_by_name = {d.name: d for d in selectable_data}

    COMPOSITE = next(i for i, d in enumerate(always_data) if d.name == project.composite)
    base_y = np.asarray(always_data[COMPOSITE].trace.y)
    checked_names: set[str] = set()

    # Figure

    fig = go.Figure()
    for d in always_data:
        fig.add_trace(go.Scatter(
            d.trace,
            showlegend=False,
            hoverinfo='skip' if d.name in not_hoverable else None,
        ))

    PREVIEW = len(always_data)
    PREVIEW_SLOTS = 4
    for slot in range(PREVIEW_SLOTS):
        fig.add_trace(go.Scatter(
            x=[], y=[],
            name=f'Row preview {slot}',
            mode='lines',
            line=dict(color=theme.PALETTE['preview'], width=2, dash='dot'),
            visible=False,
            showlegend=False,
            hoverinfo='skip',
        ))

    fig.update_layout(
        **project.layout(),
        height=240,
        margin=dict(l=45, r=15, t=15, b=40),
        template='plotly_white',
        showlegend=False,
        uirevision='keep-view',
        hovermode='closest',
        dragmode=False,
        xaxis_fixedrange=True,
        yaxis_fixedrange=True,
    )
    theme.style_figure(fig)

    ui.add_css('.modebar-container, .js-plotly-plot .legend { display: none !important; }')

    theme.setup()
    theme.header()

    download_menu(
        get_curve=lambda: (fig.data[COMPOSITE].x, fig.data[COMPOSITE].y),
        get_factors=lambda: checked_names,
        header_height=theme.HEADER_HEIGHT,
    )

    content = theme.fit_to_screen()
    with content:
        ui.link('← Projects', '/')
        theme.heading(project.title.upper(), project.subtitle.upper())
        plot = ui.plotly(fig).classes('theme-card').style(
            f'width: {theme.CONTENT_WIDTH}px; height: 240px')

    # Hover state and callbacks

    hovered_name = None
    active_slot = None
    next_slot = 0

    def composite_raw(names: set[str]) -> np.ndarray:
        chosen = [d for d in selectable_data if d.name in names]
        return base_y + sum((np.asarray(d.trace.y) for d in chosen), np.zeros_like(base_y))

    def scale_for(names: set[str]) -> float:
        return 1 / composite_raw(names).max()

    def update_preview(rescale_only: bool = False) -> None:
        nonlocal active_slot, next_slot
        data = data_by_name.get(hovered_name)

        if data is None:
            if not rescale_only and active_slot is not None:
                fig.data[active_slot].visible = False
                hide_curve(plot, active_slot)
                active_slot = None
            return

        scale = scale_for(checked_names | {data.name})
        x, y = data.trace.x, scale * np.asarray(data.trace.y)

        if rescale_only:
            if active_slot is not None:
                fig.data[active_slot].update(y=y)
                rescale_curve(plot, active_slot, y)
            return

        if active_slot is not None:
            fig.data[active_slot].visible = False
            hide_curve(plot, active_slot)
        active_slot = PREVIEW + next_slot % PREVIEW_SLOTS
        next_slot += 1
        fig.data[active_slot].update(x=x, y=y, name=f'{data.name} preview',
                                     line_color=data.color, visible=True)
        show_curve(plot, active_slot, x, y, color=data.color)

    def show_preview(event: events.GenericEventArguments) -> None:
        nonlocal hovered_name
        row = event.args.get('data') or {}
        name = row.get('name')
        if name == hovered_name:
            return
        hovered_name = name
        update_preview()

    def hide_preview() -> None:
        nonlocal hovered_name
        if hovered_name is None:
            return
        hovered_name = None
        update_preview()

    def refresh_plot() -> None:
        old_y = np.asarray(fig.data[COMPOSITE].y)
        new_y = scale_for(checked_names) * composite_raw(checked_names)
        fig.data[COMPOSITE].y = new_y
        update_preview(rescale_only=True)
        animate_traces(plot, {COMPOSITE: new_y}, starts={COMPOSITE: old_y})

    async def on_selection_changed(event: events.GenericEventArguments) -> None:
        rows = await grid.get_selected_rows()
        names = {row.get('name') for row in rows} & data_by_name.keys()
        if names == checked_names:
            return
        checked_names.clear()
        checked_names.update(names)
        refresh_plot()

    def add_data(item: Data) -> None:
        """Add a Data object to this page's grid (names must be unique)."""
        if not isinstance(item, Data):
            raise TypeError('add_data expects a Data object')
        if not isinstance(item.trace, go.Scatter):
            raise TypeError('Data.trace must be a go.Scatter trace, not a Figure')
        if item.name in data_by_name or item.name in always_shown:
            raise ValueError(f'A row or fixed curve named {item.name!r} already exists')
        go.Scatter(item.trace, name=item.name, line_color=item.color)
        data_by_name[item.name] = item
        selectable_data.append(item)
        grid.options['rowData'].append({'name': item.name, 'color': item.color})
        grid.update()

    # Grid

    COLOR_SWATCH = '''params => {
        const dot = document.createElement('span');
        dot.style.cssText = 'display:inline-block; width:12px; height:12px; border-radius:50%; '
            + 'vertical-align:middle; box-shadow:0 0 0 1px rgba(15,27,45,0.12); background:' + params.value;
        return dot;
    }'''

    SELECT_W, SWATCH_W = 48, 48
    NAME_W = theme.CONTENT_WIDTH - 2 - SELECT_W - SWATCH_W
    GRID_ROW_H = GRID_HEADER_H = 40

    with content:
        grid = ui.aggrid({
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
            'domLayout': 'autoHeight',
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

