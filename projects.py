"""Project registry. Add a Project to PROJECTS and it appears on the home screen
and gets its own page, built the same way main.py used to build the sample page."""

from dataclasses import dataclass, field
from typing import Callable
from copy import deepcopy
from dataclasses import dataclass, field
import re
from threading import Lock
from typing import Callable
from unicodedata import normalize


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
    preview: str | None = None                # optional image inside static/, e.g. 'previews/left-right.png'


# Loaders import lazily, so opening the home screen doesn't compute every project's curves.
def _load_left_right() -> list[Data]:
    from sampleData import sample_data
    return sample_data


def _left_right_layout() -> dict:
    return _error_layout('Left and right accuracy')


def _error_layout(topic: str) -> dict:
    """Keep the axis titles short; the project page explains them on hover."""
    from sampleData import LAYOUT
    layout = deepcopy(LAYOUT)
    layout['xaxis_title'] = 'Mean Squared Error'
    layout['yaxis_title'] = 'Relative Density'
    layout['xaxis'].update(automargin=True, title_standoff=10)
    layout['yaxis'].update(automargin=True, title_standoff=10)
    return layout


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
_REGISTRY_LOCK = Lock()


def _project_slug(title: str) -> str:
    text = normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
    base = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:40].rstrip('-') or 'project'
    slug = base
    suffix = 2
    while slug in PROJECTS_BY_ID:
        slug = f'{base}-{suffix}'
        suffix += 1
    return slug


def create_project(description: str) -> Project:
    """Generate five parameters and register a project only after validation."""
    from wrapper import generate_project
    from sampleData import sample_data

    description = description.strip()
    if not description:
        raise ValueError('Describe the new project first')
    title, subtitle, parameters = generate_project(description)
    defaults = deepcopy([d for d in sample_data
                         if d.name in {'Composite', 'Perfect Normal'}])
    data = defaults + parameters
    with _REGISTRY_LOCK:
        project = Project(
            id=_project_slug(title),
            title=title,
            subtitle=subtitle,
            load=lambda: deepcopy(data),
            layout=lambda: _error_layout(title),
        )
        PROJECTS.append(project)
        PROJECTS_BY_ID[project.id] = project
    return project

