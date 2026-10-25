"""Projects menu: a hamburger button pinned to the header's top left that slides out a
side drawer listing every project in projects.PROJECTS. (The SKEW logo's click-to-home
lives in theme.header().)

Call it once per page, right after theme.header() and outside the scaled content column."""

from nicegui import ui

import theme
from projects import PROJECTS


def _find_header():
    """The page's header, wherever theme.header() put it (made if there isn't one)."""
    layout = ui.context.client.layout
    for child in layout.default_slot.children:
        if isinstance(child, ui.header):
            return child
    return ui.header()


def home_button(current_id: str | None = None) -> None:
    """current_id highlights the open project in the drawer."""
    header = _find_header()

    # Overlay: slides over the page instead of pushing it, so the fitted layout never shifts.
    # It opens below the header.
    drawer = ui.left_drawer(value=False, fixed=True).props('overlay bordered width=260')
    with drawer:
        ui.label('PROJECTS').classes('theme-drawer-title font-bold q-pa-sm')
        with ui.list().props('separator').classes('w-full'):
            for project in PROJECTS:
                item = ui.item(on_click=lambda p=project: ui.navigate.to(f'/project/{p.id}'))
                if project.id == current_id:
                    item.props('active')
                with item:
                    with ui.item_section():
                        ui.item_label(project.title)

    # Hamburger pinned to the far left of the header
    with header:
        with ui.row().classes('absolute-left items-center no-wrap').style(
                'padding-left: 12px; z-index: 1'):
            ui.button(icon='menu', on_click=drawer.toggle).props('flat round dense') \
                .style(f'color: {theme.LOGO_COLOR}').tooltip('Projects')