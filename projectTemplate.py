"""The plot + selectable grid page, built from a Project.

This is the body of the old main.py wrapped in a function. All state (figure,
checked rows, hover slots) lives inside the call, so each visit, and each
project, gets its own independent copy."""

import json
import logging
from copy import deepcopy

import numpy as np
import plotly.graph_objects as go
from nicegui import events, run, ui

import theme
from data import Data, clamp_weight, factor_contribution, weighted_composite
from downloadMenu import download_menu
from projects import Project
from palette import SERIES_COLORS
from homeButton import home_button
from loadingScreen import install_project_loader
from transitions import animate_traces, hide_curve, rescale_curve, show_curve
from wrapper import generate_data, project_error_message


def build_project_page(project: Project) -> None:
    # Data

    # Own copy per visit, so slider weights never leak into other visits or users.
    sample_data = deepcopy([item for item in project.load() + project.extra_parameters
                            if item.name not in project.removed_parameters])
    always_shown = set(project.always_shown)
    not_hoverable = set(project.not_hoverable)

    always_data = [d for d in sample_data if d.name in always_shown]
    selectable_data = [d for d in sample_data if d.name not in always_shown]
    data_by_name = {d.name: d for d in selectable_data}
    default_weights = {d.name: d.weight for d in selectable_data}   # sliders snap back to these

    COMPOSITE = next(i for i, d in enumerate(always_data) if d.name == project.composite)
    base_y = np.asarray(always_data[COMPOSITE].trace.y)
    checked_names: set[str] = set()

    # Figure

    fig = go.Figure()
    for d in always_data:
        trace = go.Scatter(
            d.trace,
            showlegend=False,
            hoverinfo='skip' if d.name in not_hoverable else None,
        )
        # One tooltip for every always-shown curve (set even for not_hoverable ones: Plotly
        # can still show a trace's own hovertemplate, which is what made Perfect Normal differ).
        # The name is the bold first line of the same box, then identical MSE / Density lines.
        trace.hovertemplate = ('<b>%{fullData.name}</b><br>'
                               'Mean Squared Error %{x:.3f}<br>Relative Density %{y:.3f}<extra></extra>')
        fig.add_trace(trace)

    PREVIEW = len(always_data)
    PREVIEW_SLOTS = 4
    for slot in range(PREVIEW_SLOTS):
        fig.add_trace(go.Scatter(
            x=[], y=[],
            name=f'Row preview {slot}',
            mode='lines',
            line=dict(color=theme.PALETTE['preview'], width=3, dash='solid'),
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
        hoverlabel=dict(font_size=11, align='left', namelength=-1),
    )
    theme.style_figure(fig)

    # One "0" in the bottom-left corner: the x axis keeps its 0, the y axis skips it.
    # (Every curve is peak-scaled to 1, so these ticks suit every project.)
    fig.update_yaxes(tickmode='array', tickvals=[0.25, 0.5, 0.75, 1.0])

    ui.add_css('.modebar-container, .js-plotly-plot .legend { display: none !important; }')
    # Let hover labels draw outside the plot's SVG and card instead of being clipped
    ui.add_css('''
        .js-plotly-plot .plotly .main-svg, .js-plotly-plot .plotly .svg-container
            { overflow: visible !important; }
        .theme-card:has(.js-plotly-plot) { overflow: visible !important; position: relative; z-index: 5; }
        html, body { overflow-x: hidden; }
        .skew-project-grid .ag-body-viewport,
        .skew-project-grid .ag-center-cols-viewport { overflow: hidden !important; }
        .skew-project-grid, .skew-project-grid * { scrollbar-width: none; }
        .skew-project-grid ::-webkit-scrollbar { width: 0; height: 0; display: none; }
        .skew-project-grid .ag-body-vertical-scroll,
        .skew-project-grid .ag-body-horizontal-scroll,
        .skew-project-grid .ag-horizontal-left-spacer,
        .skew-project-grid .ag-horizontal-right-spacer {
            display: none !important; width: 0 !important; min-width: 0 !important;
            max-width: 0 !important; height: 0 !important; min-height: 0 !important;
        }
        .skew-project-grid .ag-header, .skew-project-grid .ag-header-viewport,
        .skew-project-grid .ag-body-viewport, .skew-project-grid .ag-center-cols-clipper,
        .skew-project-grid .ag-center-cols-viewport { padding-right: 0 !important; margin-right: 0 !important; }
        .skew-project-grid .ag-row-last { border-bottom-color: transparent !important; }
        .skew-project-grid .ag-header-cell-text {
            font-weight: 700 !important;
            text-transform: uppercase;
        }
        .parameter-remove {
            border: none; background: transparent; color: #5B6B7F;
            width: 24px; height: 24px; padding: 0; flex-shrink: 0;
            border-radius: 50%; cursor: pointer; font-size: 19px; line-height: 1;
            opacity: 0.25; transition: opacity 150ms ease, background-color 150ms ease;
        }
        .parameter-remove:hover, .parameter-remove:focus-visible {
            color: #B42318; background: #FEE4E2;
            opacity: 1;
        }
        .skew-project-grid .parameter-remove-cell {
            padding: 0 !important;
            justify-content: center;
        }
        .skew-project-grid .parameter-remove-cell .ag-cell-wrapper,
        .skew-project-grid .parameter-remove-cell .ag-cell-value {
            width: 100%; display: flex; justify-content: center;
            overflow: visible; text-overflow: clip;
        }
        .skew-project-plot .xtitle, .skew-project-plot .ytitle {
            font-weight: 700 !important;
        }
    ''')
    # Plotly draws hover boxes as SVG paths. A matching rounded stroke softens
    # their corners; CSS border-radius does not apply to these paths.
    ui.add_css(f'''
        .skew-project-plot .hoverlayer .hovertext path {{
            stroke: {theme.PALETTE['ink']} !important;
            stroke-width: 8px !important;
            stroke-linejoin: round;
        }}
    ''')

    install_project_loader()   # loading screen, until the graph entrance is ready
    theme.setup()
    theme.header()

    download_menu(
        get_curve=lambda: (fig.data[COMPOSITE].x, fig.data[COMPOSITE].y),
        get_factors=lambda: checked_names,
        header_height=theme.HEADER_HEIGHT,
        get_plot=lambda: plot,
        graph_filename=project.id,
    )

    home_button(current_id=project.id)

    content = theme.fit_to_screen()
    with content:
        theme.heading(project.title.upper(), project.subtitle.upper())
        plot = ui.plotly(fig).classes('theme-card skew-project-plot').style(
            f'width: {theme.CONTENT_WIDTH}px; height: 240px')

    # Use the graph's hover-label styling instead of browser-native SVG titles.
    axis_tooltips_js = r'''
        const root = getHtmlElement(__PLOT_ID__);
        if (root._axisTooltipCleanup) root._axisTooltipCleanup();
        const explanations = {
            '.xtitle': ['Mean Squared Error', 'Closer to 0 means less error.'],
            '.ytitle': ['Relative Density', 'Higher values mean more concentrated errors.']
        };
        const tooltip = document.createElement('div');
        tooltip.setAttribute('role', 'tooltip');
        tooltip.id = 'axis-tooltip-__PLOT_ID__';
        Object.assign(tooltip.style, {
            position: 'absolute', display: 'none', pointerEvents: 'none',
            zIndex: '20', background: __BG__, color: 'white',
            borderRadius: '4px', padding: '7px 8px', fontFamily: __FONT__,
            fontSize: '11px', lineHeight: '1.3', textAlign: 'left',
            width: '150px', boxSizing: 'border-box', whiteSpace: 'normal',
            overflowWrap: 'break-word'
        });
        const heading = document.createElement('b');
        const description = document.createElement('div');
        tooltip.append(heading, description);
        root.appendChild(tooltip);
        const findLabel = event => event.target.closest?.('.xtitle, .ytitle');
        const hide = () => { tooltip.style.display = 'none'; };
        const show = event => {
            const label = findLabel(event);
            if (!label || !root.contains(label)) return;
            const [title, explanation] = explanations[label.matches('.xtitle') ? '.xtitle' : '.ytitle'];
            heading.textContent = title;
            description.textContent = explanation;
            tooltip.style.display = 'block';
            const box = root.getBoundingClientRect();
            const anchor = label.getBoundingClientRect();
            const sx = box.width / root.offsetWidth || 1;
            const sy = box.height / root.offsetHeight || 1;
            const isY = label.matches('.ytitle');
            const gap = 4;
            const sideRoom = isY
                ? anchor.left - 8 - gap * sx
                : window.innerWidth - 8 - anchor.right - gap * sx;
            tooltip.style.width = Math.min(isY ? 150 : 135, Math.max(80, sideRoom / sx)) + 'px';
            const left = isY
                ? (anchor.left - box.left) / sx - tooltip.offsetWidth - gap
                : (anchor.right - box.left) / sx + gap;
            const top = (anchor.top + anchor.height / 2 - box.top) / sy
                - tooltip.offsetHeight / 2 + (isY ? 0 : tooltip.offsetHeight * 1.375);
            // Allow the box outside the chart, keeping it inside the viewport.
            const minLeft = (8 - box.left) / sx;
            const maxLeft = (window.innerWidth - 8 - box.left) / sx - tooltip.offsetWidth;
            const minTop = (8 - box.top) / sy;
            const maxTop = (window.innerHeight - 8 - box.top) / sy - tooltip.offsetHeight;
            tooltip.style.left = Math.max(minLeft, Math.min(left, maxLeft)) + 'px';
            tooltip.style.top = Math.max(minTop, Math.min(top, maxTop)) + 'px';
        };
        const attach = () => {
            for (const selector of Object.keys(explanations)) {
                for (const label of root.querySelectorAll(selector)) {
                    label.querySelector('title')?.remove();
                    label.style.pointerEvents = 'all';
                    label.style.cursor = 'help';
                    label.setAttribute('tabindex', '0');
                    label.setAttribute('aria-describedby', tooltip.id);
                }
            }
        };
        attach();
        const observer = new MutationObserver(records => {
            if (records.some(record => !tooltip.contains(record.target))) attach();
        });
        observer.observe(root, {childList: true, subtree: true});
        const leave = event => { if (findLabel(event)) hide(); };
        root.addEventListener('pointerover', show);
        root.addEventListener('pointerout', leave);
        root.addEventListener('pointerleave', hide);
        root.addEventListener('focusin', show);
        root.addEventListener('focusout', leave);
        root._axisTooltipCleanup = () => {
            observer.disconnect();
            root.removeEventListener('pointerover', show);
            root.removeEventListener('pointerout', leave);
            root.removeEventListener('pointerleave', hide);
            root.removeEventListener('focusin', show);
            root.removeEventListener('focusout', leave);
            tooltip.remove();
        };
    '''.replace('__PLOT_ID__', str(plot.id)).replace(
        '__BG__', json.dumps(theme.PALETTE['ink'])).replace(
        '__FONT__', json.dumps(theme.font_stack('plot')))
    ui.timer(0.1, lambda: ui.run_javascript(axis_tooltips_js), once=True)

    # Hover state and callbacks

    hovered_name = None
    active_slot = None
    next_slot = 0

    def chosen(names: set[str]) -> list[Data]:
        return [d for d in selectable_data if d.name in names]

    def composite_raw(names: set[str]) -> np.ndarray:
        return weighted_composite(base_y, chosen(names))

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

        # The hovered factor's slice of the composite it would be part of,
        # at its current population share and the composite's display scale.
        names = checked_names | {data.name}
        x = data.trace.x
        y = scale_for(names) * factor_contribution(data, chosen(names))

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
        show_curve(plot, active_slot, x, y, color=data.color)   # line only, no fill

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

    def refresh_plot(*, duration: int | None = None) -> None:
        old_y = np.asarray(fig.data[COMPOSITE].y)
        new_y = scale_for(checked_names) * composite_raw(checked_names)
        fig.data[COMPOSITE].y = new_y
        update_preview(rescale_only=True)
        animate_traces(plot, {COMPOSITE: new_y}, starts={COMPOSITE: old_y},
                       duration=500 if duration is None else duration)

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
        default_weights[item.name] = item.weight
        project.extra_parameters.append(deepcopy(item))
        row = {
            'name': item.name, 'color': item.color, 'weight': item.weight,
            'default_weight': item.weight, 'weight_source': item.weight_source,
        }
        grid.options['rowData'].append(row)
        grid.style(f'height: {grid_height()}px')
        # Add just this row. grid.update() would rebuild every row, which clears the
        # checkmarks and snaps every slider back to its starting position.
        grid.run_grid_method('applyTransaction', {'add': [row]})
        update_add_button()

    # Grid

    COLOR_SWATCH = '''params => {
        const dot = document.createElement('span');
        dot.style.cssText = 'display:inline-block; width:12px; height:12px; border-radius:50%; '
            + 'vertical-align:middle; box-shadow:0 0 0 1px rgba(15,27,45,0.12); background:' + params.value;
        return dot;
    }'''

    PARAMETER_REMOVE = '''params => {
        const remove = document.createElement('button');
        remove.textContent = '\u00d7';
        remove.type = 'button';
        remove.title = 'Remove ' + params.data.name;
        remove.setAttribute('aria-label', remove.title);
        remove.className = 'parameter-remove';
        ['pointerdown', 'mousedown', 'dblclick', 'touchstart', 'keydown'].forEach(
            type => remove.addEventListener(type, event => event.stopPropagation()));
        remove.addEventListener('click', event => {
            event.stopPropagation();
            emitEvent('factor-remove', {name: params.data.name});
        });
        return remove;
    }'''

    SELECT_W, SWATCH_W, WEIGHT_W, REMOVE_W = 48, 48, 168, 48
    NAME_W = theme.CONTENT_WIDTH - 2 - SELECT_W - SWATCH_W - WEIGHT_W - REMOVE_W
    GRID_ROW_H = GRID_HEADER_H = 40
    GRID_MIN_ROWS = 3
    MAX_PARAMETERS = 10
    # A few spare pixels so the rows never measure even 1px taller than the table body
    # (browser zoom rounds). If they do, the grid assumes a vertical scroll bar is coming
    # and keeps a scroll-bar-wide strip empty on the right of every row.
    GRID_SLACK = 4

    def grid_height() -> int:
        """Exact pixel height for the current rows (at least GRID_MIN_ROWS tall)."""
        rows = max(len(selectable_data), GRID_MIN_ROWS)
        return GRID_HEADER_H + rows * GRID_ROW_H + 2 + GRID_SLACK   # +2: border

    def on_weight_changed(event: events.GenericEventArguments) -> None:
        args = event.args if isinstance(event.args, dict) else {}
        data = data_by_name.get(args.get('name'))
        if data is None:
            return
        data.weight = clamp_weight(args.get('weight'), default=data.weight)
        if data.name in checked_names:
            refresh_plot()                    # also rescales the hover preview
        elif data.name == hovered_name:
            update_preview(rescale_only=True)  # unchecked but hovered: preview follows the slider

    def on_weight_live(event: events.GenericEventArguments) -> None:
        """While dragging: only the factor's own line follows the slider;
        the composite waits for on_weight_changed (slider released)."""
        args = event.args if isinstance(event.args, dict) else {}
        data = data_by_name.get(args.get('name'))
        if data is None:
            return
        data.weight = clamp_weight(args.get('weight'), default=data.weight)
        if data.name == hovered_name:
            update_preview(rescale_only=True)

    def remove_parameter(event: events.GenericEventArguments) -> None:
        args = event.args if isinstance(event.args, dict) else {}
        names = {args.get('name')} & data_by_name.keys()
        if not names:
            return
        if hovered_name in names:
            hide_preview()
        was_checked = bool(names & checked_names)
        checked_names.difference_update(names)
        for name in names:
            data_by_name.pop(name, None)
            default_weights.pop(name, None)
        selectable_data[:] = [item for item in selectable_data if item.name not in names]
        project.extra_parameters[:] = [item for item in project.extra_parameters if item.name not in names]
        project.removed_parameters.update(names)
        grid.options['rowData'][:] = [row for row in grid.options['rowData'] if row['name'] not in names]
        grid.run_grid_method('applyTransaction', {'remove': [{'name': name} for name in names]})
        grid.style(f'height: {grid_height()}px')
        update_add_button()
        if was_checked:
            refresh_plot()
        ui.notify(f'Removed {len(names)} parameter(s).', type='positive')


    ui.on('factor-remove', remove_parameter)
    ui.on('factor-weight', on_weight_changed)
    ui.on('factor-weight-live', on_weight_live)

    with content:
        grid = ui.aggrid({
            'defaultColDef': {'resizable': False, 'sortable': False, 'suppressMovable': True,
                              'suppressHeaderMenuButton': True},
            'columnDefs': [
                {'field': 'color', 'headerName': '', ':cellRenderer': COLOR_SWATCH,
                 'width': SWATCH_W, 'minWidth': SWATCH_W, 'maxWidth': SWATCH_W},
                {'field': 'name', 'headerName': 'NAME', 'flex': 1, 'minWidth': 120},   # takes all leftover width
                {'field': 'weight', 'headerName': 'WEIGHT', 'width': WEIGHT_W,
                 'minWidth': WEIGHT_W, 'maxWidth': WEIGHT_W,
                 ':cellRenderer': theme.WEIGHT_SLIDER_JS},
                {'colId': 'remove', 'headerName': '', 'width': REMOVE_W,
                 'minWidth': REMOVE_W, 'maxWidth': REMOVE_W,
                 'cellClass': 'parameter-remove-cell',
                 ':cellRenderer': PARAMETER_REMOVE},
            ],
            'selectionColumnDef': {'width': SELECT_W, 'minWidth': SELECT_W, 'maxWidth': SELECT_W,
                                   'resizable': False},
            'rowData': [{'name': d.name, 'color': d.color, 'weight': d.weight,
                         'default_weight': default_weights[d.name],
                         'weight_source': d.weight_source} for d in selectable_data],
            'rowSelection': {'mode': 'multiRow'},
            'domLayout': 'normal',
            # Rows jump straight to their place. Sliding rows pass under the mouse one by
            # one, which fired a hover preview for each and made the graph flicker.
            'animateRows': False,
            'rowHeight': GRID_ROW_H,
            'headerHeight': GRID_HEADER_H,
            'suppressCellFocus': True,
            'suppressHorizontalScroll': True,
            # No space reserved for scroll bars (the grid is always sized to fit its rows).
            'scrollbarWidth': 0,
            ':getRowId': 'params => params.data.name',
        }).classes('theme-card skew-project-grid').style(
        f'width: {theme.CONTENT_WIDTH}px; height: {grid_height()}px; transition: height 200ms ease')

    grid.on('selectionChanged', on_selection_changed)
    grid.on('cellMouseOver', show_preview, ['data'])
    grid.on('mouseout', hide_preview, js_handler='''(event) => {
        const row = event.target.closest('.ag-row');
        if (row && !row.contains(event.relatedTarget)) emit();
    }''')
    grid.on('mouseleave', hide_preview)

    with content, ui.row().classes('add-parameter-row w-full items-center gap-3'):
        with ui.button('ADD PARAMETER', icon='add').props('unelevated no-caps') \
                .classes('add-parameter-button action-btn create-project-btn self-start').style(
                    f'background-color: {theme.PALETTE["ink"]} !important; '
                    f'color: {theme.LOGO_COLOR} !important;') as add_button:
            # Opens to the right of the button, in line with it.
            with ui.menu().props('anchor="center right" self="center left" :offset="[12, 0]" '
                                 'transition-show="fade" transition-hide="fade" '
                                 'transition-duration="120"') \
                    as parameter_menu:
                # Width comes from --add-parameter-width, which is computed up front (and on
                # resize) by the script at the bottom, so its right edge lines up with the
                # right edge of the row and the box doesn't shift on the first open.
                with ui.row().classes('items-center gap-3 no-wrap p-3') \
                        .style('width: var(--add-parameter-width, 600px)'):
                    parameter_prompt = ui.input(placeholder='Describe a new parameter...') \
                        .props('outlined dense').classes('add-parameter-input') \
                        .style('flex: 1 1 auto; min-width: 0')

                    async def submit_parameter() -> None:
                        if not parameter_submit.enabled:
                            return
                        if len(selectable_data) >= MAX_PARAMETERS:
                            ui.notify(f'You can have at most {MAX_PARAMETERS} parameters. '
                                      'Remove one to add another.', type='negative')
                            return
                        description = (parameter_prompt.value or '').strip()
                        if not description:
                            ui.notify('Describe the parameter you want to add.', type='negative')
                            return
                        parameter_submit.disable().props('loading')
                        parameter_prompt.disable()
                        parameter_menu.props('persistent')
                        try:
                            prompt = (
                                f'Project: {project.title}. {project.subtitle}\n'
                                f'Existing parameters: {", ".join(data_by_name)}\n'
                                'Create one new parameter related to the user description '
                                'for this project, using the same normalized MSE scale.\n'
                                f'User description: {description}'
                            )
                            items = await run.io_bound(generate_data, prompt, count=1)
                            item = items[0]
                            name = item.name
                            suffix = 2
                            used = set(data_by_name) | always_shown | {
                                d.name for d in project.load() + project.extra_parameters}
                            while item.name in used:
                                item.name = f'{name} ({suffix})'
                                suffix += 1
                            in_use = {d.color for d in selectable_data}
                            item.color = next((c for c in SERIES_COLORS if c not in in_use),
                                              SERIES_COLORS[len(selectable_data) % len(SERIES_COLORS)])
                            item.trace.update(name=item.name, line_color=item.color)
                            add_data(item)
                        except Exception as error:
                            logging.getLogger(__name__).exception('Parameter creation failed')
                            ui.notify(project_error_message(error), type='negative',
                                      close_button='Dismiss', timeout=10_000)
                            return
                        finally:
                            parameter_submit.enable().props(remove='loading')
                            parameter_prompt.enable()
                            parameter_menu.props(remove='persistent')
                        parameter_prompt.set_value('')
                        parameter_menu.close()
                        ui.notify(f'Added {item.name}. Select it to include it in the graph.', type='positive')

                    parameter_submit = ui.button('ADD', on_click=submit_parameter) \
                        .props('unelevated no-caps').classes('action-btn').style(
                            f'background-color: {theme.PALETTE["ink"]} !important; '
                            f'color: {theme.LOGO_COLOR} !important; height: 40px; padding: 0 20px; '
                            'flex-shrink: 0;')

                    parameter_prompt.on('keydown.enter', submit_parameter)

                # Set the menu width ahead of time (the row is created after page load, so wait
                # for it) and keep it current on resize. Doing this in 'before-show' made the
                # box resize after Quasar had already positioned it on the first open.
                ui.add_body_html('''
                <script>
                (function () {
                    const update = () => {
                        const button = document.querySelector('.add-parameter-button');
                        const row = button && button.closest('.add-parameter-row');
                        if (!row) return false;
                        const gap = 12;   // matches the menu's offset
                        const width = row.getBoundingClientRect().right
                            - button.getBoundingClientRect().right - gap;
                        document.documentElement.style.setProperty(
                            '--add-parameter-width', Math.max(280, Math.floor(width)) + 'px');
                        return true;
                    };
                    const wait = setInterval(() => { if (update()) clearInterval(wait); }, 50);
                    window.addEventListener('resize', update);
                })();
                </script>
                ''')
                # Focus on the client instead of a server round trip.
                parameter_menu.on('show', js_handler='''() => {
                    const input = document.querySelector('.add-parameter-input input');
                    if (input) input.focus();
                }''')

        def update_add_button() -> None:
            """Grey out ADD PARAMETER while the table is full."""
            if len(selectable_data) >= MAX_PARAMETERS:
                add_button.props('disable')
                add_button.style(replace='background-color: #B8C0CC !important; '
                                         'color: #FFFFFF !important;')
            else:
                add_button.props(remove='disable')
                add_button.style(replace=f'background-color: {theme.PALETTE["ink"]} !important; '
                                         f'color: {theme.LOGO_COLOR} !important;')

        update_add_button()