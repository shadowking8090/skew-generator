import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from nicegui import ui

import projectTemplate
from projects import PROJECTS
import wrapper


@pytest.fixture
def parameter_controls():
    controls = {}
    project = replace(PROJECTS[0], extra_parameters=[], removed_parameters=set())
    button, textarea, aggrid, on = ui.button, ui.textarea, ui.aggrid, ui.on

    def capture_button(*args, **kwargs):
        element = button(*args, **kwargs)
        if args and args[0] == 'ADD':
            controls.update(button=element, submit=kwargs['on_click'])
        return element

    def capture_event(name, callback, *args, **kwargs):
        if name == 'factor-remove':
            controls['remove'] = callback
        return on(name, callback, *args, **kwargs)

    def capture_textarea(*args, **kwargs):
        controls['prompt'] = textarea(*args, **kwargs)
        return controls['prompt']

    def capture_grid(*args, **kwargs):
        controls['grid'] = aggrid(*args, **kwargs)
        return controls['grid']

    with patch.object(ui, 'button', capture_button), patch.object(ui, 'textarea', capture_textarea), \
            patch.object(ui, 'aggrid', capture_grid), patch.object(ui, 'on', capture_event):
        projectTemplate.build_project_page(project)
    controls['project'] = project
    return controls


def test_add_parameter_uses_one_call_and_updates_grid_and_project(parameter_controls):
    controls = parameter_controls
    controls['prompt'].value = 'Fatigue'
    payload = {'curves': [dict(name='Age bias', trials=20, rate=0.4, bw=0.06,
                              weight=0.2, weight_source='Assumed 20% share')]}
    response = Mock(json=Mock(return_value={'reply': json.dumps(payload)}))

    async def io(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    async def submit():
        with controls['prompt'].client:
            await controls['submit']()

    with patch.object(projectTemplate.run, 'io_bound', io), \
            patch.object(wrapper.requests, 'post', return_value=response) as post:
        asyncio.run(submit())
    post.assert_called_once()
    sent = post.call_args.kwargs['json']['prompt']
    assert 'exactly 1' in sent and 'Fatigue' in sent
    item = controls['project'].extra_parameters[0]
    assert item.name == 'Age bias (2)'
    assert controls['grid'].options['rowData'][-1]['name'] == item.name
    assert controls['prompt'].value == ''
    assert controls['button'].enabled
    with patch.object(ui, 'aggrid', wraps=ui.aggrid) as grid:
        projectTemplate.build_project_page(controls['project'])
    assert grid.call_args.args[0]['rowData'][-1]['name'] == item.name


def test_remove_selected_parameter_updates_project_and_grid(parameter_controls):
    controls = parameter_controls
    name = controls['grid'].options['rowData'][0]['name']

    async def remove():
        with controls['prompt'].client:
            controls['remove'](SimpleNamespace(args={'name': name}))

    with patch.object(controls['grid'], 'get_selected_rows', AsyncMock(return_value=[{'name': name}])), \
            patch.object(ui, 'run_javascript'):
        asyncio.run(remove())
    assert name in controls['project'].removed_parameters
    assert all(row['name'] != name for row in controls['grid'].options['rowData'])
    with patch.object(ui, 'aggrid', wraps=ui.aggrid) as grid:
        projectTemplate.build_project_page(controls['project'])
    assert all(row['name'] != name for row in grid.call_args.args[0]['rowData'])


def test_parameter_failure_keeps_prompt_and_does_not_add_rows(parameter_controls):
    controls = parameter_controls
    controls['prompt'].value = 'Fatigue'
    before = len(controls['grid'].options['rowData'])

    async def submit():
        with controls['prompt'].client:
            await controls['submit']()

    with patch.object(projectTemplate.run, 'io_bound', side_effect=ValueError('Bad response')):
        asyncio.run(submit())
    assert len(controls['grid'].options['rowData']) == before
    assert not controls['project'].extra_parameters
    assert controls['prompt'].value == 'Fatigue'
    assert controls['button'].enabled
