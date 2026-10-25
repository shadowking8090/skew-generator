"""Project registry. Add a Project to PROJECTS and it appears on the home screen
and gets its own page, built the same way main.py used to build the sample page."""

from dataclasses import dataclass, field
from typing import Callable

from data import Data


@dataclass
class Project:
    id: str                                   # used in the URL: /project/<id>
    title: str                                # card title and page heading
    subtitle: str                             # card description and page subheading
    load: Callable[[], list[Data]]            # returns every Data object for the project
    layout: Callable[[], dict]                # returns the Plotly layout kwargs (axis titles, ranges)
    color: str = '#2f6fed'                    # accent dot on the home card
    composite: str = 'Composite'              # name of the curve that sums the checked rows
    always_shown: tuple[str, ...] = ('Composite', 'Perfect Normal')   # plotted, never listed
    not_hoverable: tuple[str, ...] = ('Perfect Normal',)


# Loaders import lazily, so opening the home screen doesn't compute every project's curves.
def _load_left_right() -> list[Data]:
    from sampleData import sample_data
    return sample_data


def _left_right_layout() -> dict:
    from sampleData import LAYOUT
    return LAYOUT


PROJECTS: list[Project] = [
    Project(
        id='left-right',
        title='Left and right accuracy',
        subtitle='The error distribution of people deciding between left and right.',
        load=_load_left_right,
        layout=_left_right_layout,
    ),
    # Template for the next project:
    #
    # Project(
    #     id='my-project',
    #     title='My project',
    #     subtitle='One line shown on the card and under the page heading.',
    #     load=lambda: my_module.sample_data,   # list[Data]; must include the `composite` curve
    #     layout=lambda: my_module.LAYOUT,
    #     color='#e8590c',
    # ),
]

PROJECTS_BY_ID = {p.id: p for p in PROJECTS}