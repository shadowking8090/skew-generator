
"""Home screen with project creation button and project preview cards."""

import base64
from typing import Callable

import numpy as np
from nicegui import ui

import theme
from projects import PROJECTS, Project

PAGE_WIDTH = 960
CARD_MIN_WIDTH = 280
PREVIEW_HEIGHT = 130

P = theme.PALETTE

CSS = f'''
    .nicegui-content {{ padding: 0 !important; gap: 0 !important; }}

    .new-band {{
        background: {theme.rgba(P['ink'], 0.04)};
        border-top: 1px solid {P['border']};
        border-bottom: 1px solid {P['border']};
    }}

    .project-card {{
        transition: border-color .15s ease, transform .15s ease;
    }}
    .project-card:hover {{
        border-color: {P['accent']};
        transform: translateY(-2px);
    }}
    .project-band-title {{
        font-family: var(--font-heading);
        font-size: 22px; font-weight: 700; line-height: 1;
        letter-spacing: -0.01em; color: {P['ink']};
    }}
    .project-band-subheading {{
        font-family: var(--font-subheading);
        font-size: 14px; font-weight: 400; line-height: 1.4;
        color: {P['muted']};
    }}
    .project-card-title {{
        font-family: var(--font-heading);
        font-size: 18px; font-weight: 700; line-height: 1.2;
        letter-spacing: -0.01em; color: {P['ink']};
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

    /* Center the plus icon in the left rounded end. */
    .create-project-btn {{
        height: 40px !important;
        padding: 0 20px 0 8px !important;
        font-weight: 600 !important;
        border-radius: 9999px !important;
    }}
    .create-project-btn .q-btn__content {{
        display: flex;
        align-items: center;
        justify-content: flex-start;
    }}
    .create-project-btn .q-icon.on-left {{
        font-size: 24px !important;
        margin-left: 0 !important;
        margin-right: 10px !important;
    }}

    /* Fixed two-line textarea. */
    .create-project-textarea textarea {{
        height: 48px !important;
        min-height: 48px !important;
        max-height: 48px !important;
        box-sizing: border-box !important;
        padding-top: 4px !important;
        padding-bottom: 4px !important;
        line-height: 20px !important;
        resize: none !important;
        overflow-y: hidden !important;
        overflow-x: hidden !important;
    }}
'''

# Reject input that would exceed two visible lines.
# This also handles wrapped text and pasted content.
TWO_LINE_SCRIPT = r'''
<script>
(() => {
    if (window.__homeTwoLineLimitInstalled) return;
    window.__homeTwoLineLimitInstalled = true;

    const selector = '.create-project-textarea textarea';
    const lastValid = new WeakMap();

    document.addEventListener('focusin', event => {
        const field = event.target;
        if (!field.matches?.(selector)) return;

        lastValid.set(field, {
            value: field.value,
            cursor: field.selectionStart ?? 0,
        });
    }, true);

    document.addEventListener('input', event => {
        const field = event.target;
        if (!field.matches?.(selector)) return;

        const previous = lastValid.get(field) ?? {
            value: '',
            cursor: 0,
        };

        const style = getComputedStyle(field);
        const lineHeight = parseFloat(style.lineHeight) || 20;
        const top = parseFloat(style.paddingTop) || 0;
        const bottom = parseFloat(style.paddingBottom) || 0;
        const maxScrollHeight = 2 * lineHeight + top + bottom + 1;

        const noThirdNewline = field.value.split('\n').length <= 2;
        const noThirdVisualLine = field.scrollHeight <= maxScrollHeight;

        if (noThirdNewline && noThirdVisualLine) {
            lastValid.set(field, {
                value: field.value,
                cursor: field.selectionStart ?? field.value.length,
            });
        } else {
            field.value = previous.value;
            const cursor = Math.min(previous.cursor, field.value.length);
            field.setSelectionRange(cursor, cursor);
        }
    }, true);
})();
</script>
'''


# Previews

_cache: dict[str, str | None] = {}


def _sparkline_uri(x, y, color: str, width: int = 280, height: int = PREVIEW_HEIGHT) -> str:
    """Draw a small area chart as an SVG data URI."""
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
    """Get the project's custom preview or generate a sparkline."""
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

    except Exception as e:
        print(f'[home] no preview for {project.id!r}: {e}')

    _cache[project.id] = result
    return result


# Page

def home_page(on_project_submit: Callable[[str], None] | None = None) -> None:
    """Render the home page.

    Supply on_project_submit(details) to handle new project requests.
    Without it, submission is acknowledged but no project is created.
    """

    theme.setup()
    theme.header(home_link=False)

    ui.add_css(CSS)
    ui.add_head_html(TWO_LINE_SCRIPT)

    # NEW band: equal top and bottom padding.
    with ui.column().classes('new-band w-full items-center') \
            .style('padding: 32px 16px'):

        with ui.column().classes('w-full gap-3').style(f'max-width: {PAGE_WIDTH}px'):

            ui.label('PROJECTS').classes('project-band-title')

            ui.label('Something about projects that is very profound.'.upper()) \
                .classes('project-band-subheading')

            # The menu is directly attached to its trigger button.
            with ui.button('CREATE PROJECT', icon='add') \
                    .props('unelevated no-caps') \
                    .classes('action-btn create-project-btn self-start') \
                    .style(
                        f'background-color: {P["ink"]} !important; '
                        f'color: {theme.LOGO_COLOR} !important;'
                    ):

                with ui.menu() as menu:

                    with ui.column().classes('p-3 gap-2').style('width: 300px'):

                        textbox = ui.textarea(
                            placeholder='Enter project details...'
                        ).props(
                            'outlined rows=2'
                        ).classes(
                            'w-full create-project-textarea'
                        )

                        # Real submit handler.
                        def submit_project() -> None:
                            details = (textbox.value or '').strip()

                            if not details:
                                ui.notify(
                                    'Please enter project details.',
                                    type='warning',
                                )
                                return

                            if on_project_submit is not None:
                                on_project_submit(details)
                                ui.notify(
                                    'Project request submitted.',
                                    type='positive',
                                )
                            else:
                                print(f'[home] Project request submitted: {details}')
                                ui.notify(
                                    'Submitted (project creation is not connected yet).',
                                    type='info',
                                )

                            textbox.set_value('')
                            menu.close()

                        ui.button(
                            'Submit',
                            on_click=submit_project,
                        ).props(
                            'unelevated no-caps'
                        ).classes(
                            'action-btn w-full'
                        ).style(
                            f'background-color: {P["ink"]} !important; '
                            f'color: {theme.LOGO_COLOR} !important;'
                        )

    # Projects: heading and card grid.
    with ui.column().classes('w-full items-center').style('padding: 24px 16px 32px'):

        with ui.column().classes('w-full gap-4').style(f'max-width: {PAGE_WIDTH}px'):

            if not PROJECTS:
                ui.label('No projects yet. Add one to projects.py.')

            with ui.element('div').classes('w-full').style(
                f'display: grid; gap: 16px; '
                f'grid-template-columns: repeat(auto-fill, minmax({CARD_MIN_WIDTH}px, 1fr))'
            ):

                for project in PROJECTS:
                    src = _preview_for(project)

                    with ui.card().props('flat') \
                            .classes('theme-card project-card p-0 gap-0 cursor-pointer') \
                            .on('click', lambda p=project: ui.navigate.to(f'/project/{p.id}')):

                        if src:
                            ui.image(src).props(
                                'fit=cover no-spinner no-transition'
                            ).style(
                                f'width: 100%; height: {PREVIEW_HEIGHT}px'
                            )
                        else:
                            ui.element('div').style(
                                f'width: 100%; height: {PREVIEW_HEIGHT}px; '
                                f'background: {P["page"]}'
                            )

                        with ui.column().classes('gap-1 w-full').style('padding: 14px 16px 16px'):

                            ui.label(project.title.upper()).classes('project-card-title')
                            ui.label(project.subtitle).classes('project-card-text')
