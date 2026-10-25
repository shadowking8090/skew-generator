"""Site theme: palette ("Ink and Blue"), custom TTF font, header bar, figure styling.

Usage in main.py:

    import theme
    theme.style_figure(fig)
    theme.setup()      # fonts, page colors, grid colors (call before building the page)
    theme.header()     # logo bar across the top
    content = theme.fit_to_screen()   # centered column, scaled to the window
    with content: ...  # put the plot and table in it

Fonts: drop your .ttf files into static/fonts/, register each family in FONT_FILES,
then choose which family each part of the page uses in FONT_USE. A missing file is
skipped (the fallback font is used), so the page always renders.
"""

import base64
from pathlib import Path

from nicegui import app, ui

from palette import PALETTE, SERIES_COLORS, rgba  # noqa: F401  (re-exported)

STATIC_DIR = Path(__file__).parent / 'static'

# ------------------------------------------------------------------ palette

# PALETTE and SERIES_COLORS live in palette.py so sampleData.py can use them too.

# --------------------------------------------------------------------- font

# 1) Register font families: CSS family name -> {weight: .ttf path inside static/}.
#    Add as many families as you like. System fonts ("Georgia") need no entry here.
FONT_FILES = {
    'Skew Display': {400: 'fonts/Jost-Bold.ttf'},
    'Skew Display Light': {400: 'fonts/Jost-Light.ttf'},
    'Lekton': {400: 'fonts/Lekton-Regular.ttf', 700: 'fonts/Lekton-Bold.ttf'}
}

# 2) Choose which family each part of the page uses (a family from FONT_FILES, or any system font).
FONT_USE = {
    'page':       'Lekton',   # everything not listed below (buttons, labels, ...)
    'heading':    'Skew Display',   # the title above the plot            -> try 'Skew Display'
    'subheading': 'Skew Display Light',   # the line under the title
    'plot':       'Lekton',   # axis labels, ticks and hover tooltips
    'table':      'Lekton',   # the grid: header and cells
    'menu':       'Skew Display',   # the side drawer's project list
}
FONT_FALLBACK = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'


def font_stack(role: str) -> str:
    """CSS font-family value for a part of the page, e.g. font_stack('plot')."""
    return f'"{FONT_USE.get(role, FONT_USE["page"])}", {FONT_FALLBACK}'


def _slug(family: str) -> str:
    return family.lower().replace(' ', '-')

# ------------------------------------------------------------------- header

CONTENT_WIDTH = 640                # px; the plot and the table are both this wide at scale 1
MIN_SCALE, MAX_SCALE = 0.5, 1.5    # limits for scaling the content to the window
SCREEN_MARGIN = 24                 # px of breathing room kept around the scaled content
LOGO_FILE = STATIC_DIR / 'logo.png'
LOGO_ASPECT = 716 / 198            # width / height of static/logo.png
HEADER_HEIGHT = 48                 # px
LOGO_COLOR = '#FAFDED'             # the off-white inside logo.png and download.png (250, 253, 237)
LOGO_HEIGHT = 28                   # px


def _font_face_css() -> str:
    rules = []
    for family, files in FONT_FILES.items():
        for weight, rel in files.items():
            if (STATIC_DIR / rel).is_file():
                rules.append(
                    f'@font-face {{ font-family: "{family}"; '
                    f'src: url("/static/{rel}") format("truetype"); '
                    f'font-weight: {weight}; font-style: normal; font-display: swap; }}'
                )
            else:
                print(f'[theme] font file not found, using fallback: {STATIC_DIR / rel}')
    return '\n'.join(rules)


_FONT_ROLES = ('page', 'heading', 'subheading', 'plot', 'table', 'menu')


def _font_css() -> str:
    """One CSS variable per role, plus a .font-<family> utility class per registered family
    (e.g. ui.label('x').classes('font-skew-display') uses that family on any element)."""
    variables = ' '.join(f'--font-{role}: {font_stack(role)};' for role in _FONT_ROLES)
    utilities = '\n'.join(
        f'.font-{_slug(family)} {{ font-family: "{family}", {FONT_FALLBACK}; }}' for family in FONT_FILES)
    return f':root {{ {variables} }}\n{utilities}'


def setup() -> None:
    """Serve ./static, load the font, and color the page, Quasar widgets and the grid."""
    p = PALETTE
    app.add_static_files('/static', str(STATIC_DIR))
    ui.colors(primary=p['accent'])

    ui.add_css(_font_face_css())
    ui.add_css(f'''
        {_font_css()}
        html, body, .q-btn, .q-field__native, .q-item, .q-tab {{ font-family: var(--font-page); }}
        body, .q-page, .nicegui-content {{ background: {p['page']} !important; color: {p['text']}; }}

        /* heading above the plot */
        .theme-heading {{
            font-family: var(--font-heading);
            font-size: 24px; font-weight: 700; line-height: 1.2;
            letter-spacing: -0.01em; color: {p['ink']};
        }}
        .theme-subheading {{
            font-family: var(--font-subheading);
            font-size: 14px; font-weight: 400; line-height: 1.4; color: {p['muted']};
        }}

        /* home screen project cards: title in the heading font, description in the subheading font */
        .theme-card-title {{
            font-family: var(--font-heading);
            font-size: 18px; font-weight: 700; line-height: 1.2;
            letter-spacing: -0.01em; color: {p['ink']};
        }}
        .theme-card-text {{
            font-family: var(--font-subheading);
            font-size: 14px; line-height: 1.4; color: {p['muted']};
        }}

        /* side drawer (projects menu) */
        .q-drawer, .q-drawer .q-item, .q-drawer .q-item__label {{ font-family: var(--font-menu); }}
        .theme-drawer-title {{
            font-family: var(--font-heading);
            font-size: 12px; letter-spacing: 0.08em; color: {p['muted']};
        }}

        /* white cards for the plot and the grid */
        .theme-card {{
            background: {p['panel']};
            border: 1px solid {p['border']};
            border-radius: 8px;
            overflow: hidden;
        }}

        /* ag-grid */
        .ag-theme-quartz, .ag-theme-alpine, .ag-theme-balham, .ag-theme-material {{
            --ag-font-family: var(--font-table);
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
            --ag-font-size: 14px;
            --ag-header-font-weight: 700;
            --ag-borders: none;                              /* the card supplies the border */
            --ag-header-column-separator-display: none;
            --ag-cell-horizontal-padding: 14px;
        }}
        :is(.ag-theme-quartz, .ag-theme-alpine, .ag-theme-balham, .ag-theme-material) .ag-root-wrapper {{ border: none; }}
        :is(.ag-theme-quartz, .ag-theme-alpine, .ag-theme-balham, .ag-theme-material) .ag-header-cell-resize {{ display: none; }}
        :is(.ag-theme-quartz, .ag-theme-alpine, .ag-theme-balham, .ag-theme-material) .ag-header-cell-text {{
            font-size: 11px; font-weight: 700 !important;
            letter-spacing: 0.08em; text-transform: uppercase;
        }}
        :is(.ag-theme-quartz, .ag-theme-alpine, .ag-theme-balham, .ag-theme-material) .ag-header-cell-label {{ font-weight: 700 !important; display: flex; align-items: center; }}
        :is(.ag-theme-quartz, .ag-theme-alpine, .ag-theme-balham, .ag-theme-material) .ag-cell {{ display: flex; align-items: center; }}
        .skew-weight {{
            display: flex; align-items: center; gap: 8px; width: 100%;
        }}
        /* Slider: same light grey track on every row; the knob uses the row's color (--thumb). */
        .skew-weight input[type=range] {{
            flex: 1; min-width: 0; height: 16px; margin: 0;
            -webkit-appearance: none; appearance: none; background: transparent; cursor: pointer;
        }}
        .skew-weight input[type=range]::-webkit-slider-runnable-track {{
            height: 6px; border-radius: 3px; background: #e5e7eb;
        }}
        .skew-weight input[type=range]::-moz-range-track {{
            height: 6px; border-radius: 3px; background: #e5e7eb;
        }}
        .skew-weight input[type=range]::-webkit-slider-thumb {{
            -webkit-appearance: none; appearance: none; margin-top: -5px;
            width: 16px; height: 16px; border-radius: 50%; border: none;
            background: var(--thumb, {p['accent']});
            box-shadow: 0 0 0 0 transparent; transition: box-shadow 0.35s ease-out;
        }}
        .skew-weight input[type=range]::-moz-range-thumb {{
            width: 16px; height: 16px; border-radius: 50%; border: none;
            background: var(--thumb, {p['accent']});
            box-shadow: 0 0 0 0 transparent; transition: box-shadow 0.35s ease-out;
        }}
        /* Latched onto the default weight: a faint ring that fades in and out. */
        .skew-weight.skew-latch input[type=range]::-webkit-slider-thumb {{
            box-shadow: 0 0 0 4px color-mix(in srgb, var(--thumb, {p['accent']}) 22%, transparent);
            transition-duration: 0.08s;
        }}
        .skew-weight.skew-latch input[type=range]::-moz-range-thumb {{
            box-shadow: 0 0 0 4px color-mix(in srgb, var(--thumb, {p['accent']}) 22%, transparent);
            transition-duration: 0.08s;
        }}
        .skew-weight-label {{
            width: 38px; text-align: right; font-variant-numeric: tabular-nums;
            color: {p['text']}; font-size: 13px;
        }}
        :is(.ag-theme-quartz, .ag-theme-alpine, .ag-theme-balham, .ag-theme-material) :is(.ag-body-vertical-scroll, .ag-body-horizontal-scroll) {{ display: none !important; }}
        :is(.ag-theme-quartz, .ag-theme-alpine, .ag-theme-balham, .ag-theme-material) .ag-body-viewport {{ overflow: hidden !important; }}

        /* scale-to-fit wrapper (see fit_to_screen) */
        .fit-inner {{ transform-origin: top center; flex: none; }}
        :is(.ag-theme-quartz, .ag-theme-alpine, .ag-theme-balham, .ag-theme-material) .ag-cell-focus:not(.ag-cell-range-selected):focus-within {{ border-color: transparent !important; }}
    ''')


def _logo_data_uri() -> str | None:
    """The logo as a data: URI, so the page needs no separate request for it
    (immune to caching, ad blockers and static-route problems). None if missing."""
    if not LOGO_FILE.is_file():
        print(f'[theme] logo not found: {LOGO_FILE}')
        return None
    return 'data:image/png;base64,' + base64.b64encode(LOGO_FILE.read_bytes()).decode()


def header(home_link: bool = True) -> None:
    """Navy bar across the top with the logo centered. Clicking the logo goes home,
    unless home_link is False (used on the home screen itself)."""
    width = round(LOGO_HEIGHT * LOGO_ASPECT)
    uri = _logo_data_uri()
    with ui.header(fixed=True).classes('items-center justify-center px-4 py-0 shadow-none') \
            .style(f'background:{PALETTE["ink"]}; height:{HEADER_HEIGHT}px; min-height:{HEADER_HEIGHT}px'):
        if uri:
            logo = ui.image(uri).props('fit=contain no-spinner no-transition') \
                .style(f'width:{width}px; height:{LOGO_HEIGHT}px') \
                .classes('cursor-pointer' if home_link else '')
            if home_link:
                logo.on('click', lambda: ui.navigate.to('/'))   # logo = home
        else:   # fallback if the file is missing
            logo = ui.label('SKEW').classes('text-white text-lg font-bold')
            if home_link:
                logo.classes('cursor-pointer').on('click', lambda: ui.navigate.to('/'))


_FIT_JS = '''
(() => {
    const MIN = __MIN__, MAX = __MAX__, MARGIN = __MARGIN__;
    let queued = false;
    const fit = () => {
        queued = false;
        const outer = document.querySelector('.fit-outer');
        const inner = document.querySelector('.fit-inner');
        if (!outer || !inner) return;
        const header = document.querySelector('.q-header');
        const w = inner.offsetWidth, h = inner.offsetHeight;   // layout size: unaffected by the scale
        if (!w || !h) return;
        const availW = window.innerWidth - 2 * MARGIN;
        const availH = window.innerHeight - (header ? header.offsetHeight : 0) - 2 * MARGIN;
        const scale = Math.max(MIN, Math.min(MAX, availW / w, availH / h));
        inner.style.transform = 'scale(' + scale + ')';
        outer.style.height = (h * scale) + 'px';                // scaled boxes don't take up layout space
    };
    const schedule = () => { if (!queued) { queued = true; requestAnimationFrame(fit); } };
    window.addEventListener('resize', schedule);
    const attach = () => {
        const inner = document.querySelector('.fit-inner');
        if (!inner) return false;
        new ResizeObserver(schedule).observe(inner);             // rows added, fonts loaded, etc.
        schedule();
        return true;
    };
    if (!attach()) {
        const mo = new MutationObserver(() => { if (attach()) mo.disconnect(); });
        mo.observe(document.documentElement, {childList: true, subtree: true});
    }
})();
'''


def fit_to_screen() -> ui.column:
    """A centered column that is CONTENT_WIDTH wide at scale 1 and is scaled, as one
    unit, to fit the window (between MIN_SCALE and MAX_SCALE). Returns the column;
    build the plot and table inside it:

        content = theme.fit_to_screen()
        with content:
            plot = ui.plotly(...)

    Scaling the whole block keeps the table's fixed layout intact (no reflow),
    and Plotly's hover stays accurate inside the scaled block."""
    ui.add_head_html('<script>' + (_FIT_JS
                     .replace('__MIN__', str(MIN_SCALE))
                     .replace('__MAX__', str(MAX_SCALE))
                     .replace('__MARGIN__', str(SCREEN_MARGIN))) + '</script>')
    with ui.column().classes('fit-outer w-full items-center gap-0'):
        return ui.column().classes('fit-inner items-center gap-4') \
            .style(f'width: {CONTENT_WIDTH}px')


# Slider cell in the factor table. While dragging it emits 'factor-weight-live'
# (the factor's own line follows the slider); on release it emits 'factor-weight'
# (the composite updates once, when the person stops dragging).
# Dragging within SNAP points of the row's default_weight clicks onto the default
# (except at the very ends, so small defaults can still reach 1%).
WEIGHT_SLIDER_JS = '''params => {
    const wrap = document.createElement('div');
    wrap.className = 'skew-weight';
    const slider = document.createElement('input');
    slider.type = 'range';
    slider.min = '1';
    slider.max = '100';
    slider.step = '1';
    const pct = Math.round(Number(params.value) * 100);
    slider.value = String(Number.isFinite(pct) && pct >= 1 ? Math.min(100, pct) : 20);
    if (params.data && params.data.color) slider.style.setProperty('--thumb', params.data.color);
    const SNAP = 2;
    const def = Math.round(Number(params.data && params.data.default_weight) * 100);
    let last = Number(slider.value);   // last value shown while dragging
    let sent = last;                   // last value sent to the graph
    const label = document.createElement('span');
    label.className = 'skew-weight-label';
    const sync = () => { label.textContent = slider.value + '%'; };
    sync();
    const stop = event => event.stopPropagation();
    ['pointerdown', 'mousedown', 'click', 'dblclick', 'touchstart'].forEach(
        type => slider.addEventListener(type, stop));
    slider.addEventListener('input', () => {
        let value = Number(slider.value);
        if (Number.isFinite(def) && value !== 1 && value !== 100 && Math.abs(value - def) <= SNAP) {
            value = def;
            slider.value = String(def);
        }
        sync();
        if (value === last) return;   // held at the default: nothing changed
        if (value === def) {          // just latched: brief ring around the knob
            wrap.classList.add('skew-latch');
            clearTimeout(wrap._latchTimer);
            wrap._latchTimer = setTimeout(() => wrap.classList.remove('skew-latch'), 450);
        }
        last = value;
        emitEvent('factor-weight-live', {name: params.data.name, weight: value / 100});
    });
    // Released: now update the graph, once.
    slider.addEventListener('change', () => {
        const value = Number(slider.value);
        if (value === sent) return;
        sent = value;
        const weight = value / 100;
        params.data.weight = weight;
        emitEvent('factor-weight', {name: params.data.name, weight: weight});
    });
    wrap.append(slider, label);
    return wrap;
}'''


def heading(title: str, subtitle: str | None = None, *, align: str = 'center') -> None:
    """A title (and optional subtitle) for the current container.
    Fonts come from FONT_USE['heading'] and FONT_USE['subheading']; align is 'center' or 'left'."""
    side = 'items-center text-center' if align == 'center' else 'items-start text-left'
    with ui.column().classes(f'w-full gap-1 {side}'):
        ui.label(title).classes('theme-heading')
        if subtitle:
            ui.label(subtitle).classes('theme-subheading')


def style_figure(fig) -> None:
    """Apply the palette and font to a Plotly figure's layout and axes.
    Trace colors come from sampleData.py (Data.color), which uses the same palette."""
    p = PALETTE
    fig.update_layout(
        paper_bgcolor=p['panel'],
        plot_bgcolor=p['panel'],
        font=dict(family=font_stack('plot'), color=p['text'], size=12),
        hoverlabel=dict(bgcolor=p['ink'], font=dict(family=font_stack('plot'), color='white')),
    )
    for update_axes in (fig.update_xaxes, fig.update_yaxes):
        update_axes(
            gridcolor=p['border'], zerolinecolor=p['border'], linecolor=p['border'],
            tickfont=dict(color=p['muted']), title_font=dict(color=p['muted']),
        )