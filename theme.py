"""Site theme: palette ("Ink and Blue"), custom TTF font, header bar, figure styling.

Usage in main.py:

    import theme
    theme.style_figure(fig)
    theme.setup()      # fonts, page colors, grid colors (call before building the page)
    theme.header()     # logo bar across the top

Custom font: drop your .ttf file(s) into static/fonts/ and set FONT_FAMILY and
FONT_FILES below. A missing file is skipped (the fallback font is used).
"""

import base64
from pathlib import Path

from nicegui import app, ui

from palette import PALETTE, SERIES_COLORS, rgba  # noqa: F401  (re-exported)

STATIC_DIR = Path(__file__).parent / 'static'

# ------------------------------------------------------------------ palette

# PALETTE and SERIES_COLORS live in palette.py so sampleData.py can use them too.

# --------------------------------------------------------------------- font

FONT_FAMILY = 'Skew Sans'          # any name; used in CSS and in the plot
FONT_FILES = {                     # weight -> path inside static/
    400: 'fonts/Regular.ttf',
    700: 'fonts/Bold.ttf',
}
FONT_FALLBACK = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
FONT_STACK = f'"{FONT_FAMILY}", {FONT_FALLBACK}'

# ------------------------------------------------------------------- header

LOGO_FILE = STATIC_DIR / 'logo.png'
LOGO_ASPECT = 716 / 198            # width / height of static/logo.png
HEADER_HEIGHT = 48                 # px
LOGO_HEIGHT = 28                   # px


def _font_face_css() -> str:
    rules = []
    for weight, rel in FONT_FILES.items():
        if (STATIC_DIR / rel).is_file():
            rules.append(
                f'@font-face {{ font-family: "{FONT_FAMILY}"; '
                f'src: url("/static/{rel}") format("truetype"); '
                f'font-weight: {weight}; font-style: normal; font-display: swap; }}'
            )
        else:
            print(f'[theme] font file not found, using fallback: {STATIC_DIR / rel}')
    return '\n'.join(rules)


def setup() -> None:
    """Serve ./static, load the font, and color the page, Quasar widgets and the grid."""
    p = PALETTE
    app.add_static_files('/static', str(STATIC_DIR))
    ui.colors(primary=p['accent'])

    ui.add_css(_font_face_css())
    ui.add_css(f'''
        :root {{ --font: {FONT_STACK}; }}
        html, body, .q-btn, .q-field__native, .q-item, .q-tab {{ font-family: var(--font); }}
        body, .q-page, .nicegui-content {{ background: {p['page']} !important; color: {p['text']}; }}

        /* white cards for the plot and the grid */
        .theme-card {{
            background: {p['panel']};
            border: 1px solid {p['border']};
            border-radius: 8px;
            overflow: hidden;
        }}

        /* ag-grid */
        .ag-theme-quartz, .ag-theme-alpine, .ag-theme-balham, .ag-theme-material {{
            --ag-font-family: var(--font);
            --ag-background-color: {p['panel']};
            --ag-foreground-color: {p['text']};
            --ag-header-background-color: {p['page']};
            --ag-header-foreground-color: {p['muted']};
            --ag-border-color: {p['border']};
            --ag-row-border-color: {p['border']};
            --ag-row-hover-color: {p['hover']};
            --ag-selected-row-background-color: {p['selected']};
            --ag-checkbox-checked-color: {p['accent']};
            --ag-range-selection-border-color: {p['accent']};
        }}
    ''')


def _logo_data_uri() -> str | None:
    """The logo as a data: URI, so the page needs no separate request for it
    (immune to caching, ad blockers and static-route problems). None if missing."""
    if not LOGO_FILE.is_file():
        print(f'[theme] logo not found: {LOGO_FILE}')
        return None
    return 'data:image/png;base64,' + base64.b64encode(LOGO_FILE.read_bytes()).decode()


def header() -> None:
    """Navy bar across the top with the logo on the left."""
    width = round(LOGO_HEIGHT * LOGO_ASPECT)
    uri = _logo_data_uri()
    with ui.header(fixed=True).classes('items-center justify-start px-4 py-0 shadow-none') \
            .style(f'background:{PALETTE["ink"]}; height:{HEADER_HEIGHT}px; min-height:{HEADER_HEIGHT}px'):
        if uri:
            ui.image(uri).props('fit=contain no-spinner no-transition') \
                .style(f'width:{width}px; height:{LOGO_HEIGHT}px')
        else:
            ui.label('SKEW').classes('text-white text-lg font-bold')   # fallback if the file is missing


def style_figure(fig) -> None:
    """Apply the palette and font to a Plotly figure's layout and axes.
    Trace colors come from sampleData.py (Data.color), which uses the same palette."""
    p = PALETTE
    fig.update_layout(
        paper_bgcolor=p['panel'],
        plot_bgcolor=p['panel'],
        font=dict(family=FONT_STACK, color=p['text'], size=12),
        hoverlabel=dict(bgcolor=p['ink'], font=dict(family=FONT_STACK, color='white')),
    )
    for update_axes in (fig.update_xaxes, fig.update_yaxes):
        update_axes(
            gridcolor=p['border'], zerolinecolor=p['border'], linecolor=p['border'],
            tickfont=dict(color=p['muted']), title_font=dict(color=p['muted']),
        )