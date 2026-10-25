import json
from unittest.mock import patch

import pytest

import projects
import wrapper


def reply(count):
    return json.dumps({'title': 'Recognition under fatigue',
                       'subtitle': 'How fatigue affects recognition errors.',
                       'curves': [dict(name=f'Factor {i}', trials=20,
                                      rate=0.3 + i * 0.05, bw=0.06)
                                  for i in range(count)]})


def test_creation_registers_defaults_and_five_independent_parameters():
    with patch.object(wrapper, 'ask', return_value=reply(5)) as ask:
        project = projects.create_project('Fatigue and recognition')
    try:
        assert 'exactly 5' in ask.call_args.args[0]
        assert projects.PROJECTS_BY_ID[project.id] is project
        assert project in projects.PROJECTS
        assert project.title == 'Recognition under fatigue'
        assert project.subtitle == 'How fatigue affects recognition errors.'
        data = project.load()
        assert [d.name for d in data[:2]] == ['Composite', 'Perfect Normal']
        assert len(data) == 7
        data[2].name = 'Changed'
        assert project.load()[2].name == 'Factor 0'
        assert project.layout()['xaxis']['range'] == [0, 1]
    finally:
        projects.PROJECTS.remove(project)
        del projects.PROJECTS_BY_ID[project.id]


def test_wrong_parameter_count_does_not_register_project():
    before = list(projects.PROJECTS)
    registry = dict(projects.PROJECTS_BY_ID)
    with patch.object(wrapper, 'ask', return_value=reply(4)):
        with pytest.raises(ValueError, match='exactly 5'):
            projects.create_project('Fatigue')
    assert projects.PROJECTS == before
    assert projects.PROJECTS_BY_ID == registry
