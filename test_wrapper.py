import json
from unittest.mock import Mock, patch

import numpy as np
import pytest
import requests

import wrapper
from data import Data
from sampleData import x


def payload(**changes):
    return json.dumps({'curves': [dict(name='Test (synthetic)', trials=20,
                                      rate=0.4, bw=0.06, **changes)]})


def test_generate_data_uses_description_and_returns_plot_data():
    response = Mock()
    response.json.return_value = {'reply': payload()}
    with patch.object(wrapper.requests, 'post', return_value=response) as post:
        items = wrapper.generate_data('Model fatigue')
    response.raise_for_status.assert_called_once()
    assert 'Model fatigue' in post.call_args.kwargs['json']['prompt']
    assert post.call_args.kwargs['json']['model'] == 'gemini-1.5-flash'
    assert post.call_args.kwargs['timeout'] == 60
    assert len(items) == 1 and isinstance(items[0], Data)
    assert items[0].name == 'Test'
    np.testing.assert_array_equal(items[0].trace.x, x)
    assert np.all(np.isfinite(items[0].trace.y))
    assert min(items[0].trace.y) >= 0
    assert max(items[0].trace.y) == pytest.approx(0.9)


def test_accepts_json_code_block():
    assert len(wrapper.parse_curves('```json\n' + payload() + '\n```')) == 1


@pytest.mark.parametrize('field,value', [
    ('trials', True), ('trials', 0), ('trials', 1001),
    ('rate', float('nan')), ('rate', 1.1), ('bw', 0),
    ('name', 'Composite'), ('name', ''),
])
def test_rejects_invalid_parameters(field, value):
    curve = json.loads(payload())
    curve['curves'][0][field] = value
    with pytest.raises(ValueError):
        wrapper.parse_curves(json.dumps(curve))


@pytest.mark.parametrize('reply', ['not json', '{}', '{"curves": []}',
                                   '__import__("os").system("echo unsafe")'])
def test_rejects_invalid_responses(reply):
    with pytest.raises(ValueError):
        wrapper.parse_curves(reply)


@pytest.mark.parametrize('prompt', ['', '   ', '12345', '?!?'])
def test_empty_or_nonverbal_prompt_never_calls_api(prompt):
    with patch.object(wrapper, 'ask') as ask:
        with pytest.raises(wrapper.InvalidProjectPrompt):
            wrapper.generate_project(prompt)
    ask.assert_not_called()


@pytest.mark.parametrize('reply', ['{}', '{"valid": "true"}', 'not json'])
def test_malformed_combined_response_does_not_trigger_another_call(reply):
    with patch.object(wrapper, 'ask', return_value=reply) as ask:
        with pytest.raises(ValueError):
            wrapper.generate_project('How fatigue affects accuracy')
    ask.assert_called_once()


def test_rejected_prompt_explains_what_to_change():
    with patch.object(wrapper, 'ask', return_value='{"valid": false, "reason": "greeting"}'):
        with pytest.raises(wrapper.InvalidProjectPrompt, match='instead of a greeting'):
            wrapper.generate_project('hello')


@pytest.mark.parametrize('error,expected', [
    (requests.Timeout('private details'), 'took too long'),
    (requests.ConnectionError('private details'), 'internet connection'),
    (ValueError('private details'), 'usable project'),
    (RuntimeError('private details'), 'could not create'),
])
def test_errors_have_helpful_messages_without_raw_details(error, expected):
    message = wrapper.project_error_message(error)
    assert expected in message
    assert 'private details' not in message


@pytest.mark.parametrize('status,expected', [(429, 'too many requests'),
                                          (503, 'temporarily unavailable'),
                                          (401, 'API access')])
def test_http_errors_explain_service_failure(status, expected):
    response = requests.Response()
    response.status_code = status
    error = requests.HTTPError('private details', response=response)
    assert expected in wrapper.project_error_message(error)


def test_unavailable_model_is_reported_as_configuration_problem():
    response = requests.Response()
    response.status_code = 503
    response._content = b'{"error":"models/gemini-1.5-pro is not found for API version v1beta"}'
    error = requests.HTTPError(response=response)
    assert 'Update the Gemini model in the Cloudflare Worker' in wrapper.project_error_message(error)


def test_disabled_api_explains_how_to_enable_it():
    response = requests.Response()
    response.status_code = 403
    response._content = b'{"error":"Gemini API has not been used in project 123 before or it is disabled."}'
    message = wrapper.project_error_message(requests.HTTPError(response=response))
    assert 'Enable the Generative Language API' in message
    assert 'wait a few minutes' in message
