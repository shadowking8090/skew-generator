import os
from pathlib import Path

from nicegui import ui

from home import home_page
from projectTemplate import build_project_page
from projects import PROJECTS_BY_ID, register_project
from data import Data
from graph_entrance import install_graph_loading

def create_from_home(details: str, title: str, subtitle: str, curves: list[Data]) -> None:
    """Save the homepage's generated data and open its registered project."""
    project = register_project(title, subtitle, curves)
    ui.navigate.to(f'/project/{project.id}')


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