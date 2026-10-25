# home.py

"""Home screen: the NEW button (left-aligned) above a grid of project cards.

Each card shows an image preview, the project title and its description. The preview is
either an image you provide (Project.preview, a path inside static/) or, by default, a
sparkline of the project's composite curve drawn automatically from its data."""

import base64
from pathlib import Path

import numpy as np
from nicegui import ui

import theme
from projects import PROJECTS, Project

PAGE_WIDTH = 960        # px; max width of the title, button and card grid
CARD_MIN_WIDTH = 280    # px; the grid fits as many columns of at least this width as it can
PREVIEW_HEIGHT = 130    # px

P = theme.PALETTE

CSS = f'''
    /* the home page manages its own padding so the NEW band can run edge to edge */
    .nicegui-content {{ padding: 0 !important; gap: 0 !important; }}
    .new-band {{
        background: {theme.rgba(P['ink'], 0.04)};
        border-top: 1px solid {P['border']};
        border-bottom: 1px solid {P['border']};
    }}
    .project-card {{
        transition: border-color .15s ease, transform .15s ease;
    }}
    .project-card:hover {{ border-color: {P['accent']}; transform: translateY(-2px); }}
    .project-band-title {{
        font-family: var(--font-heading);
        font-size: 22px; font-weight: 700; line-height: 1;
        letter-spacing: -0.01em; color: {P['ink']};
    }}
    .project-band-subheading {{
        font-family: var(--font-subheading);
        font-size: 14px; font-weight: 400; line-height: 1.4; color: {P['muted']};
    }}
    .project-card-text {{
        font-family: var(--font-subheading);
        font-size: 14px; line-height: 1.4; color: {P['muted']};
    }}
    .project-card-meta {{
        font-family: var(--font-page);
        font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
        text-transform: uppercase; color: {P['muted']};
    }}
    .action-btn {{
        font-family: var(--font-heading) !important;
        letter-spacing: 0.04em;
    }}
    .
'''


# Previews

_cache: dict[str, str | None] = {}   # project id -> preview image src


def _sparkline_uri(x, y, color: str, width: int = 280, height: int = PREVIEW_HEIGHT) -> str:
    """A small area-and-line chart of one curve, as an SVG data URI (no extra libraries)."""
    pad = 14
    xs, ys = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    step = max(1, len(xs) // 90)
    xs, ys = xs[::step], ys[::step]
    px = pad + (xs - xs.min()) / ((xs.max() - xs.min()) or 1) * (width - 2 * pad)
    py = height - pad - ys / (ys.max() or 1) * (height - 2 * pad)
    line = 'M ' + ' L '.join(f'{a:.1f},{b:.1f}' for a, b in zip(px, py))
    area = f'{line} L {px[-1]:.1f},{height - pad} L {px[0]:.1f},{height - pad} Z'
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="none">'
        f'<rect width="{width}" height="{height}" fill="{P["page"]}"/>'
        f'<line x1="{pad}" y1="{height - pad}" x2="{width - pad}" y2="{height - pad}" '
        f'stroke="{P["border"]}" stroke-width="1" vector-effect="non-scaling-stroke"/>'
        f'<path d="{area}" fill="{color}" fill-opacity="0.15"/>'
        f'<path d="{line}" fill="none" stroke="{color}" stroke-width="2.5" '
        f'stroke-linejoin="round" vector-effect="non-scaling-stroke"/>'
        f'</svg>'
    )
    return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()


def _preview_for(project: Project) -> str | None:
    """The preview image src, or None if no preview can be made."""
    if project.id in _cache:
        return _cache[project.id]
    result: str | None = None
    try:
        data = project.load()
        custom = getattr(project, 'preview', None)
        if custom and (theme.STATIC_DIR / custom).is_file():
            result = f'/static/{custom}'
        else:
            curve = next(d for d in data if d.name == project.composite)
            result = _sparkline_uri(curve.trace.x, curve.trace.y, project.color)
    except Exception as e:   # a broken project must not take the home screen down
        print(f'[home] no preview for {project.id!r}: {e}')
    _cache[project.id] = result
    return result


# Page

def home_page() -> None:
    theme.setup()
    theme.header(home_link=False)   # already home: the logo isn't a link here
    ui.add_css(CSS)

    # NEW band: full-width, slightly off-color strip ending right after the button container
    with ui.column().classes('new-band w-full items-center') \
            .style(f'padding: 32px 16px 24px'):
        with ui.column().classes('w-full gap-3').style(f'max-width: {PAGE_WIDTH}px'):
            ui.label('PROJECTS').classes('project-band-title')
            ui.label('Something about projects that is very profound.'.upper()).classes('project-band-subheading')

            # Combined long button with the + sign and CREATE PROJECT text, controlling a dropdown
            with ui.menu() as menu:
                with ui.card().classes('p-3 gap-2').style('width: 280px'):
                    textbox = ui.textarea(placeholder='Enter project details...').props('outlined rows=2').classes('w-full')
                    textbox.style('resize: none;')  # Prevent manual resizing / expanding
                    ui.button('Submit', on_click=lambda: (print(textbox.value), menu.close())) \
                        .props('unelevated').classes('action-btn w-full') \
                        .style(f'background-color: {P["ink"]} !important; color: {theme.LOGO_COLOR}')

            ui.button('CREATE PROJECT', icon='add', on_click=lambda: menu.open()) \
                .props('unelevated') \
                .classes('action-btn self-start items-center') \
                .style(f'background-color: {P["ink"]} !important; color: {theme.LOGO_COLOR}; height: 40px; padding: 0 20px; font-weight: 600; border-radius: 9999px;')

    # Projects: heading and the grid of cards
    with ui.column().classes('w-full items-center').style('padding: 24px 16px 32px'):
        with ui.column().classes('w-full gap-4').style(f'max-width: {PAGE_WIDTH}px'):

            if not PROJECTS:
                ui.label('No projects yet. Add one to projects.py.')

            with ui.element('div').classes('w-full').style(
                    f'display: grid; gap: 16px; '
                    f'grid-template-columns: repeat(auto-fill, minmax({CARD_MIN_WIDTH}px, 1fr))'):
                for project in PROJECTS:
                    src = _preview_for(project)
                    with ui.card().props('flat').classes('theme-card project-card p-0 gap-0 cursor-pointer') \
                            .on('click', lambda p=project: ui.navigate.to(f'/project/{p.id}')):
                        if src:
                            ui.image(src).props('fit=cover no-spinner no-transition') \
                                .style(f'width: 100%; height: {PREVIEW_HEIGHT}px')
                        else:
                            ui.element('div').style(
                                f'width: 100%; height: {PREVIEW_HEIGHT}px; background: {P["page"]}')
                        with ui.column().classes('gap-1 w-full').style('padding: 14px 16px 16px'):
                            ui.label(project.title.upper()).classes('project-card-title')
                            ui.label(project.subtitle).classes('project-card-text')