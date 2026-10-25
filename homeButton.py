"""Projects menu: a hamburger button pinned to the header's top left that slides out a
side drawer listing every project in projects.PROJECTS. (The SKEW logo's click-to-home
lives in theme.header().)

Call it once per page, right after theme.header() and outside the scaled content column."""

import base64
from pathlib import Path

from nicegui import ui

import theme
from projects import PROJECTS


# Hamburger icon: put your PNG at static/hamburger.png (any size, kept in its own colors).
# If the file is missing, a built-in menu icon is shown instead.
ICON_FILE = Path(__file__).parent / 'static' / 'hamburger.png'
ICON_SIZE = 22   # px


def _icon_data_uri() -> str:
    return 'data:image/png;base64,' + base64.b64encode(ICON_FILE.read_bytes()).decode()


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
        ui.label('PROJECTS').classes('theme-drawer-title font-bold q-pa-sm w-full text-center') \
            .style(f"color: {theme.PALETTE['ink']}; font-size: 20px")
        with ui.list().props('separator').classes('w-full'):
            for project in PROJECTS:
                item = ui.item(on_click=lambda p=project: ui.navigate.to(f'/project/{p.id}'))
                if project.id == current_id:
                    item.props('active')
                with item:
                    with ui.item_section():
                        label = ui.item_label(project.title.upper()) \
                            .style(f"color: {theme.PALETTE['muted']}")
                        if project.id == current_id:
                            label.classes('font-bold')   # keeps the open project marked

    # Hamburger pinned to the far left of the header
    with header:
        with ui.row().classes('absolute-left items-center no-wrap').style(
                'padding-left: 12px; z-index: 1'):
            uri = _icon_data_uri()
            with ui.button(on_click=drawer.toggle).props('flat round dense'):
                if uri:
                    ui.image(uri).props('fit=contain no-spinner no-transition') \
                        .style(f'width:{ICON_SIZE}px; height:{ICON_SIZE}px')
                else:
                    ui.icon('menu', size=f'{ICON_SIZE}px').style(f'color: {theme.LOGO_COLOR}')