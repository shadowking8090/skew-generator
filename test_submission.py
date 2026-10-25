import asyncio
import json
import runpy
from unittest.mock import Mock, patch

import pytest
from nicegui import ui

import home
import projects
import wrapper


@pytest.fixture
def submission():
    previous = list(projects.PROJECTS)
    registry = dict(projects.PROJECTS_BY_ID)
    controls = {}
    real_button, real_textarea = ui.button, ui.textarea

    def button(*args, **kwargs):
        element = real_button(*args, **kwargs)
        if args and args[0] == 'SUBMIT':
            controls.update(button=element, submit=kwargs['on_click'])
        return element

    def textarea(*args, **kwargs):
        controls['textbox'] = real_textarea(*args, **kwargs)
        return controls['textbox']

    with patch.object(ui, 'run'), patch.object(ui, 'page', side_effect=lambda *a, **k: lambda fn: fn):
        app = runpy.run_path('main.py')
    with patch.object(ui, 'button', button), patch.object(ui, 'textarea', textarea):
        home.home_page(on_project_submit=app['create_from_home'])
    handler = controls['submit']

    async def submit_in_client_context():
        with controls['textbox'].client:
            await handler()

    controls['submit'] = submit_in_client_context
    try:
        yield controls
    finally:
        projects.PROJECTS[:] = previous
        projects.PROJECTS_BY_ID.clear()
        projects.PROJECTS_BY_ID.update(registry)


def response():
    payload = dict(title='Fatigue and accuracy', subtitle='How tiredness affects recognition errors',
                   curves=[dict(name=f'Factor {i}', trials=20, rate=0.4, bw=0.06,
                                weight=0.1, weight_source='Assumed 10% share') for i in range(5)])
    return Mock(json=Mock(return_value={'reply': json.dumps(payload)}))


async def execute_io(fn, *args):
    return fn(*args)


def test_submit_calls_wrapper_once_saves_project_and_navigates(submission):
    submission['textbox'].value = 'Fatigue and accuracy'
    with patch.object(home.run, 'io_bound', execute_io), \
            patch.object(wrapper.requests, 'post', return_value=response()) as post, \
            patch.object(ui.navigate, 'to') as navigate:
        asyncio.run(submission['submit']())
    post.assert_called_once()
    project = projects.PROJECTS[-1]
    navigate.assert_called_once_with(f'/project/{project.id}')
    assert projects.PROJECTS_BY_ID[project.id] is project
    assert len(project.load()) == 7
    assert submission['textbox'].value == ''
    assert submission['button'].enabled


def test_failed_generation_preserves_prompt_and_allows_retry(submission):
    submission['textbox'].value = 'Fatigue and accuracy'
    before = len(projects.PROJECTS)
    with patch.object(home.run, 'io_bound', side_effect=ValueError('Bad response')), \
            patch.object(ui.navigate, 'to') as navigate, patch.object(ui, 'notify') as notify:
        asyncio.run(submission['submit']())
    navigate.assert_not_called()
    assert len(projects.PROJECTS) == before
    assert submission['textbox'].value == 'Fatigue and accuracy'
    assert submission['button'].enabled
    assert notify.call_args.kwargs['type'] == 'negative'


def test_repeated_submit_while_busy_does_not_make_second_request(submission):
    submission['textbox'].value = 'Fatigue and accuracy'

    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()

        async def delayed_io(fn, *args):
            started.set()
            await release.wait()
            return fn(*args)

        with patch.object(home.run, 'io_bound', delayed_io), \
                patch.object(wrapper.requests, 'post', return_value=response()) as post, \
                patch.object(ui.navigate, 'to'):
            first = asyncio.create_task(submission['submit']())
            await started.wait()
            assert not submission['button'].enabled
            await submission['submit']()
            release.set()
            await first
            post.assert_called_once()

    asyncio.run(scenario())
