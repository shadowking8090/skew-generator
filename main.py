import os
from pathlib import Path

from nicegui import background_tasks, run, ui

from home import home_page
from projectTemplate import build_project_page
from projects import PROJECTS_BY_ID, create_project
from wrapper import project_error_message
from graph_entrance import install_graph_loading


async def _create_and_open(details: str, client) -> None:
    """Ask the AI for the project's factors, then open the new project page."""
    try:
        project = await run.io_bound(create_project, details)
    except Exception as e:
        with client:
            ui.notify(project_error_message(e), type='negative')
        return
    with client:
        ui.navigate.to(f'/project/{project.id}')


def create_from_home(details: str) -> None:
    """home.py's Create Project hook. Creation can take a while, so it runs in
    the background and the page opens when it's ready."""
    client = ui.context.client
    background_tasks.create(_create_and_open(details, client))


@ui.page('/')
def index() -> None:
    home_page(on_project_submit=create_from_home)


@ui.page('/project/{project_id}')
def project(project_id: str) -> None:
    selected = PROJECTS_BY_ID.get(project_id)
    if selected is None:
        ui.navigate.to('/')
        return
    build_project_page(selected)
    install_graph_loading()


ui.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8080)),
    reload=False,
    title='SKEW',
    favicon=Path(__file__).parent / 'static' / 'favicon.png'
)
