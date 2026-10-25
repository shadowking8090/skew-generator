"""Home screen: one card per project in projects.PROJECTS, plus a NEW button
that opens a prompt bar for describing a new project."""

from nicegui import run, ui

import theme
from projects import PROJECTS, create_project


def home_page() -> None:
    theme.setup()
    theme.header()

    content = theme.fit_to_screen()
    with content:
        theme.heading('PROJECTS', 'CHOOSE A PROJECT TO EXPLORE.')

        # NEW button: toggles the prompt bar below it
        new_button = ui.button('NEW', icon='add', on_click=lambda: toggle_prompt())

        with ui.column().style(f'width: {theme.CONTENT_WIDTH}px') as prompt_area:
            with ui.row().classes('items-center no-wrap w-full'):
                prompt_box = ui.input(placeholder='Describe the new project') \
                    .props('outlined dense autofocus').classes('grow')
                send_button = ui.button('Send', on_click=lambda: send_prompt())
            reply_label = ui.label().classes('whitespace-pre-wrap')
        prompt_area.set_visibility(False)

        async def send_prompt() -> None:
            prompt = (prompt_box.value or '').strip()
            if not prompt or not send_button.enabled:
                return
            send_button.disable()
            reply_label.text = 'Creating project with five parameters...'
            try:
                project = await run.io_bound(create_project, prompt)
                ui.navigate.to(f'/project/{project.id}')
            except Exception as e:
                reply_label.text = f'Error: {e}'
            finally:
                send_button.enable()

        prompt_box.on('keydown.enter', send_prompt)

        def toggle_prompt() -> None:
            prompt_area.set_visibility(not prompt_area.visible)

        if not PROJECTS:
            ui.label('No projects yet. Click NEW to create one.')

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
