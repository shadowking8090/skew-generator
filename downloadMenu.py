"""Download button for the top-left of the page, with a menu for exporting samples.

Clicking the button opens a small menu: slide to choose how many samples to draw from
the current composite curve (100 to 10,000, in steps of 100), then download them as a
CSV (see csv_export.py).

    from downloadMenu import download_menu

    download_menu(
        get_curve=lambda: (fig.data[COMPOSITE].x, fig.data[COMPOSITE].y),
        get_factors=lambda: checked_names,
    )

get_curve and get_factors are called when the person clicks Download, so every
export uses the curve and selection as they are at that moment.

Icon: put your PNG at static/download.png. If it is missing, a built-in icon is shown.
"""

import base64
import json
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

from nicegui import ui

from csv_export import MAX_POINTS, download_csv

ICON_FILE = Path(__file__).parent / 'static' / 'download.png'
ICON_SIZE = 22                              # px
# Set to 'brightness(0) invert(1)' to force the icon pure white. None keeps the PNG's own
# off-white (#FAFDED), which matches the SKEW logo.
ICON_FILTER = None
INSET = 12                                  # px from the left edge of the window
MIN_COUNT, MAX_COUNT, STEP = 100, 10_000, 100     # the slider: locked to multiples of STEP
DEFAULT_COUNT = 1000
assert MAX_COUNT <= MAX_POINTS and MIN_COUNT % STEP == 0 and MAX_COUNT % STEP == 0
MENU_WIDTH = 280                            # px

_TITLE_STYLE = 'font-size:16px; font-weight:700; line-height:1.2; color:#0F1B2D'
_NOTE_STYLE = 'font-size:13px; line-height:1.4; color:#5B6B7F'


def _icon_data_uri() -> str | None:
    """The icon as a data: URI, so it needs no separate request. None if missing."""
    if not ICON_FILE.is_file():
        print(f'[download_menu] icon not found, using a built-in one: {ICON_FILE}')
        return None
    return 'data:image/png;base64,' + base64.b64encode(ICON_FILE.read_bytes()).decode()


def _snap(value) -> int:
    """Round to the nearest multiple of STEP within [MIN_COUNT, MAX_COUNT]."""
    return max(MIN_COUNT, min(MAX_COUNT, round(float(value) / STEP) * STEP))


def download_menu(
    *,
    get_curve: Callable[[], tuple[Sequence[float], Sequence[float]]],
    get_factors: Callable[[], Iterable[str]],
    header_height: int = 48,
    get_plot: Callable[[], ui.plotly] | None = None,
    graph_filename: str = 'skew_graph',
) -> ui.button:
    """Create the button at the top-left, centered vertically in the header bar."""
    # A fixed-position wrapper, so the button sits over the left end of the header
    # without changing the header's layout (the logo stays centered).
    with ui.element('div').style(
        f'position:fixed; top:0; right:{INSET}px; height:{header_height}px; z-index:2100; '
        'display:flex; align-items:center'
    ):
        with ui.button().props('flat round dense color=white') as button:
            uri = _icon_data_uri()
            if uri:
                style = f'width:{ICON_SIZE}px; height:{ICON_SIZE}px'
                if ICON_FILTER:
                    style += f'; filter:{ICON_FILTER}'
                ui.image(uri).props('fit=contain no-spinner no-transition').style(style)
            else:
                ui.icon('download', size=f'{ICON_SIZE}px')

            with ui.menu().props('anchor="bottom left" self="top left"') as menu:
                with ui.column().classes('gap-3 p-4').style(f'width:{MENU_WIDTH}px'):
                    ui.label('Download data').style(_TITLE_STYLE)
                    summary = ui.label().style(_NOTE_STYLE)
                    with ui.row().classes('w-full items-baseline justify-between no-wrap gap-2'):
                        ui.label('# of samples').style(_NOTE_STYLE)
                        count_label = ui.label().style(_TITLE_STYLE)
                    amount = ui.slider(min=MIN_COUNT, max=MAX_COUNT, step=STEP, value=DEFAULT_COUNT) \
                        .props('snap label-color=primary').classes('w-full').style('--q-primary: #0F1B2D; accent-color: #0F1B2D')
                    count_label.bind_text_from(amount, 'value', backward=lambda v: f'{_snap(v):,}')
                    with ui.row().classes('w-full justify-between no-wrap').style('margin-top:-8px'):
                        ui.label(f'{MIN_COUNT:,}').style(_NOTE_STYLE)
                        ui.label(f'{MAX_COUNT:,}').style(_NOTE_STYLE)

                    def refresh_summary() -> None:
                        n = len(list(get_factors()))
                        summary.set_text(
                            'Random samples drawn from the current composite curve'
                            + (f' with {n} factor{"s" if n != 1 else ""} selected.' if n
                               else ' (no factors selected).'))

                    def download() -> None:
                        try:
                            count = _snap(amount.value)   # always a multiple of STEP
                            x, y = get_curve()          # read now: the current curve
                            download_csv(count, x, y, filename=f'skew_samples_{count}.csv')
                        except ValueError as error:
                            ui.notify(str(error), type='negative')
                            return
                        menu.close()
                        ui.notify(f'Downloaded {count:,} samples', type='positive')

                    ui.button('Download CSV', on_click=lambda: download()) \
                        .props('unelevated no-caps').classes('w-full').style('background-color: #0F1B2D !important; color: #FFFFFF !important;')
                    if get_plot is not None:
                        ui.separator()
                        ui.label('Download graph').style(_TITLE_STYLE)

                        async def download_graph() -> None:
                            try:
                                plot = get_plot()
                                await ui.run_javascript(
                                    'return (async () => {'
                                    f'const root = getHtmlElement({plot.id});'
                                    'const graph = root.matches(".js-plotly-plot") '
                                    '? root : root.querySelector(".js-plotly-plot");'
                                    'if (!graph) throw new Error("Graph is not ready");'
                                    'await Plotly.downloadImage(graph, {'
                                    'format: "png", scale: 3, '
                                    f'filename: {json.dumps(graph_filename)}'
                                    '}); return true; })();',
                                    timeout=30,
                                )
                            except Exception:
                                ui.notify('Could not download the graph. Please try again.', type='negative')
                                return
                            menu.close()

                        ui.button('Download PNG', on_click=download_graph) \
                            .props('unelevated no-caps').classes('w-full').style(
                                'background-color: #0F1B2D !important; color: #FFFFFF !important;')
                    menu.on('before-show', lambda: refresh_summary())
                    refresh_summary()
    return button
