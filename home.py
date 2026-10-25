"""Home screen: one card per project in projects.PROJECTS."""

from nicegui import ui

import theme
from projects import PROJECTS


def home_page() -> None:
    theme.setup()
    theme.header()

    content = theme.fit_to_screen()
    with content:
        theme.heading('PROJECTS', 'CHOOSE A PROJECT TO EXPLORE.')

        if not PROJECTS:
            ui.label('No projects yet. Add one to projects.py.')

        for project in PROJECTS:
            with ui.card().classes('theme-card cursor-pointer') \
                    .style(f'width: {theme.CONTENT_WIDTH}px') \
                    .on('click', lambda p=project: ui.navigate.to(f'/project/{p.id}')):
                with ui.row().classes('items-center no-wrap'):
                    ui.element('span').style(
                        f'display:inline-block; width:14px; height:14px; border-radius:50%; '
                        f'background:{project.color}; box-shadow:0 0 0 1px rgba(15,27,45,0.12)')
                    ui.label(project.title.upper()).classes('text-lg font-bold')
                ui.label(project.subtitle)